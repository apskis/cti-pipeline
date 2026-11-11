"""Branded PDFs of the pipeline's .docx reports, made by Microsoft Word and cached.

Word lays the document out exactly as a reader would see it, banner, palette and footer
included, which no HTML rendering matches.

Word is slow the first time it exports in a session (close to a minute on a machine with
a network printer as its default, while it reads the printer's page metrics) and fast
after that. So one hidden Word is kept open on a worker thread, warmed up when the
console starts, and closed after a quiet spell. Each PDF is made once and kept in a cache
folder outside out/; the cache key carries the source's size and modified time, so a
rebuilt report gets a fresh PDF on its next view.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import queue
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# The first export of a Word session can take a minute; a long report adds to that.
TIMEOUT_S = 180
# Close Word after this long without a request, so it does not sit in memory all day.
IDLE_S = 15 * 60

WD_EXPORT_FORMAT_PDF = 17
WD_DO_NOT_SAVE_CHANGES = 0

Converter = Callable[[Path, Path], None]


class PdfError(Exception):
    """A PDF could not be made. `status` is the HTTP status the API should answer with."""

    def __init__(self, message: str, status: int) -> None:
        super().__init__(message)
        self.status = status


def word_available() -> bool:
    """True when Word is registered for automation and pywin32 can drive it."""
    if sys.platform != "win32":
        return False
    import winreg

    try:
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application\CLSID"))
        import win32com.client  # noqa: F401
    except (OSError, ImportError):
        return False
    return True


def stop_automation_word(since: datetime) -> None:
    """Close Word instances this console started, never one the user has open.

    Word started for automation carries /Automation on its command line; the user's own
    Word does not. Only instances created after `since` are touched.
    """
    stamp = since.strftime("%Y-%m-%dT%H:%M:%S")
    command = (
        "Get-CimInstance Win32_Process -Filter \"Name='WINWORD.EXE'\" | "
        "Where-Object { $_.CommandLine -match '/Automation' -and "
        f"$_.CreationDate -ge [datetime]'{stamp}' }} | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
    )
    with contextlib.suppress(OSError, subprocess.TimeoutExpired):
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )


@dataclass
class _Job:
    source: Path | None  # None means warm up: start Word and export a blank page
    target: Path
    done: Future[None] = field(default_factory=Future)


class WordWorker:
    """One hidden Word on one thread. COM objects must stay on the thread that made them."""

    def __init__(self, idle_s: float = IDLE_S, timeout_s: float = TIMEOUT_S) -> None:
        self.idle_s = idle_s
        self.timeout_s = timeout_s
        self._jobs: queue.Queue[_Job | None] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._started_at = datetime.now()
        self._guard = threading.Lock()
        self._job_handle: object | None = None  # Windows job that holds our Word

    def __call__(self, source: Path, target: Path) -> None:
        self._run(_Job(source, target))

    def warm_up(self) -> None:
        """Pay Word's slow first export now, in the background, before anyone waits."""
        target = Path(tempfile.gettempdir()) / f"cti-console-warmup-{os.getpid()}.pdf"
        self._submit(_Job(None, target))

    def close(self) -> None:
        if self._thread is not None:
            self._jobs.put(None)

    def _submit(self, job: _Job) -> None:
        with self._guard:
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._loop, name="word", daemon=True)
                self._thread.start()
        self._jobs.put(job)

    def _run(self, job: _Job) -> None:
        self._submit(job)
        try:
            job.done.result(timeout=self.timeout_s)
        except FutureTimeout as exc:
            # A hung Word blocks the thread; closing it makes the call fail and frees it.
            stop_automation_word(self._started_at)
            raise PdfError(f"Word took longer than {self.timeout_s:.0f} seconds", 504) from exc

    def _loop(self) -> None:
        import pythoncom
        import pywintypes
        import win32com.client

        pythoncom.CoInitialize()
        word = None
        try:
            while True:
                try:
                    job = self._jobs.get(timeout=self.idle_s)
                except queue.Empty:
                    word = self._quit(word)
                    continue
                if job is None:
                    return
                try:
                    if word is None:
                        self._started_at = datetime.now()
                        before = _automation_word_pids()
                        # DispatchEx always starts a new Word, never the user's open one.
                        word = win32com.client.DispatchEx("Word.Application")
                        word.Visible = False
                        word.DisplayAlerts = 0
                        self._tie_to_backend(_automation_word_pids() - before)
                    self._export(word, job)
                    job.done.set_result(None)
                except pywintypes.com_error as exc:
                    word = self._keep_if_alive(word)
                    job.done.set_exception(PdfError(_com_message(exc), 502))
                except Exception as exc:  # noqa: BLE001  the caller must always hear back
                    word = self._keep_if_alive(word)
                    job.done.set_exception(PdfError(f"Word could not convert: {exc}", 502))
        finally:
            self._quit(word)
            pythoncom.CoUninitialize()

    def _tie_to_backend(self, pids: set[int]) -> None:
        """Put the new Word in a job that Windows closes when the backend exits.

        Word runs as its own process, not the backend's child, so a backend killed
        outright (Ctrl+Break, taskkill /F) would otherwise leave a hidden Word behind.
        Best effort: if Windows refuses, the launcher's own cleanup still applies.
        """
        import win32api
        import win32con
        import win32job

        try:
            if self._job_handle is None:
                job = win32job.CreateJobObject(None, "")
                info = win32job.QueryInformationJobObject(
                    job, win32job.JobObjectExtendedLimitInformation
                )
                info["BasicLimitInformation"]["LimitFlags"] |= (
                    win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                )
                win32job.SetInformationJobObject(
                    job, win32job.JobObjectExtendedLimitInformation, info
                )
                self._job_handle = job
            for pid in pids:
                process = win32api.OpenProcess(
                    win32con.PROCESS_SET_QUOTA | win32con.PROCESS_TERMINATE, False, pid
                )
                try:
                    win32job.AssignProcessToJobObject(self._job_handle, process)
                finally:
                    win32api.CloseHandle(process)
        except Exception:  # noqa: BLE001  cleanup aid only; never block a conversion
            return

    @staticmethod
    def _export(word: object, job: _Job) -> None:
        documents = word.Documents  # type: ignore[attr-defined]
        if job.source is None:
            document = documents.Add()
        else:
            # Open(FileName, ConfirmConversions, ReadOnly, AddToRecentFiles)
            document = documents.Open(str(job.source), False, True, False)
        try:
            document.ExportAsFixedFormat(str(job.target), WD_EXPORT_FORMAT_PDF)
        finally:
            document.Close(WD_DO_NOT_SAVE_CHANGES)
        if job.source is None:
            job.target.unlink(missing_ok=True)

    @classmethod
    def _keep_if_alive(cls, word: object | None) -> object | None:
        """Keep Word after a bad document; restarting costs the slow first export again."""
        try:
            _ = word.Version  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001  any failure means Word is gone or hung
            return cls._quit(word)
        return word

    @staticmethod
    def _quit(word: object | None) -> None:
        if word is not None:
            with contextlib.suppress(Exception):
                word.Quit(WD_DO_NOT_SAVE_CHANGES)  # type: ignore[attr-defined]
        return None


def _automation_word_pids() -> set[int]:
    """Process IDs of Word instances started for automation (none the user opened)."""
    import win32com.client

    try:
        wmi = win32com.client.GetObject("winmgmts:")
        rows = wmi.ExecQuery(
            "SELECT ProcessId, CommandLine FROM Win32_Process WHERE Name='WINWORD.EXE'"
        )
        return {int(r.ProcessId) for r in rows if "/Automation" in (r.CommandLine or "")}
    except Exception:  # noqa: BLE001  without the list, Word simply is not tied to a job
        return set()


def _com_message(exc: Exception) -> str:
    """Word's own words from a COM error, which sit in the excepinfo tuple."""
    args = getattr(exc, "args", ())
    info = args[2] if len(args) > 2 and isinstance(args[2], tuple) else ()
    text = info[2] if len(info) > 2 and info[2] else (args[1] if len(args) > 1 else exc)
    return f"Word could not convert the report: {str(text).strip()}"


class PdfCache:
    """One PDF per report version. Conversions run one at a time; Word dislikes company."""

    def __init__(self, folder: Path, converter: Converter | None = None) -> None:
        self.folder = folder
        self.converter = converter or WordWorker()
        self._lock = threading.Lock()

    def path_for(self, ident: str, source: Path) -> Path:
        stat = source.stat()
        key = f"{source.resolve()}|{stat.st_size}|{stat.st_mtime_ns}"
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        return self.folder / f"{ident}-{digest}.pdf"

    def get(self, ident: str, source: Path) -> Path:
        """The cached PDF for this version of `source`, made now if missing."""
        target = self.path_for(ident, source)
        if target.is_file():
            return target
        with self._lock:
            if target.is_file():  # made while this request waited
                return target
            self.folder.mkdir(parents=True, exist_ok=True)
            partial = target.with_suffix(".part.pdf")
            partial.unlink(missing_ok=True)
            try:
                self.converter(source, partial)
                os.replace(partial, target)
            finally:
                partial.unlink(missing_ok=True)
            self._drop_old(ident, keep=target)
        return target

    def _drop_old(self, ident: str, keep: Path) -> None:
        """Remove PDFs of earlier versions of the same report."""
        for old in self.folder.glob(f"{ident}-*.pdf"):
            # WK-2026-* also matches WK-2026-46-<digest>, so compare the ID part exactly.
            if old != keep and old.stem.rsplit("-", 1)[0] == ident:
                old.unlink(missing_ok=True)
