import clsx from "clsx";
import { RotateCcw, Save, Upload } from "lucide-react";
import { type ChangeEvent, type FormEvent, useState } from "react";

import { brandImageUrl, useBrand, useBrandPreview, useBrandWrites } from "../api/client";
import type { Brand, BrandImage, BrandInput, Palette } from "../api/types";
import { ConsolePreview, ContrastList, DocumentPreview } from "../components/BrandPreviews";
import LoadState from "../components/LoadState";
import {
  COLOUR_FIELDS,
  completeDraft,
  draftOf,
  IMAGE_FIELDS,
  isHex,
  MAX_TEXT,
  normaliseHex,
  sameDraft,
  TEXT_FIELDS,
  useSettled,
} from "../lib/branding";
import { SETTINGS_SECTIONS, type SettingsSection, settingsHref } from "../lib/route";

const fieldClass = "w-full rounded-md border border-line bg-surface px-2 py-1.5 text-sm";
const buttonClass =
  "inline-flex items-center gap-1.5 rounded-md border border-line px-3 py-1.5 text-sm hover:bg-raised disabled:opacity-50";
const primaryClass =
  "inline-flex items-center gap-1.5 rounded-md bg-accent px-3 py-1.5 text-sm text-on-accent hover:bg-accent-hover disabled:opacity-50";

const SECTION_LABELS: Record<SettingsSection, string> = { branding: "Branding" };

/** One colour: a picker and the hex beside it, kept in step. */
const ColourField = ({
  field,
  value,
  onChange,
}: {
  field: (typeof COLOUR_FIELDS)[number];
  value: string;
  onChange: (value: string) => void;
}) => {
  const id = `colour-${field.key}`;
  const valid = isHex(value);
  return (
    <div className="grid grid-cols-[2.5rem_6.5rem_1fr] items-center gap-2">
      <input
        type="color"
        aria-label={`${field.label} picker`}
        value={valid ? `#${normaliseHex(value).toLowerCase()}` : "#000000"}
        onChange={(e) => onChange(normaliseHex(e.target.value))}
        className="h-8 w-10 cursor-pointer rounded border border-line bg-surface p-0.5"
      />
      <input
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-invalid={!valid}
        aria-describedby={`${id}-use`}
        spellCheck={false}
        maxLength={7}
        className={clsx(fieldClass, "font-mono uppercase", !valid && "border-fail-ink")}
      />
      <label htmlFor={id} className="text-sm">
        <span className="font-medium">{field.label}</span>
        <span id={`${id}-use`} className="block text-xs text-muted">
          {valid ? field.use : "Six hex digits, such as 167D61"}
        </span>
      </label>
    </div>
  );
};

/** One image: what it is now, the rules, and a button to replace it straight away. */
const ImageField = ({ field, version }: { field: (typeof IMAGE_FIELDS)[number]; version: string }) => {
  const { upload } = useBrandWrites();
  const [problem, setProblem] = useState<string | null>(null);
  const busy = upload.isPending && upload.variables?.kind === field.kind;
  const choose = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setProblem(null);
    upload.mutate({ kind: field.kind, file }, { onError: (error) => setProblem(error.message) });
  };
  return (
    <div className="rounded-lg border border-line bg-surface p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium">{field.label}</p>
          <p className="text-xs text-muted">{field.use}</p>
        </div>
        <label className={clsx(buttonClass, "cursor-pointer", busy && "opacity-50")}>
          <Upload aria-hidden size={14} />
          {busy ? "Uploading" : "Replace"}
          <input
            type="file"
            accept="image/png"
            className="sr-only"
            disabled={busy}
            onChange={choose}
            aria-label={`Replace the ${field.label.toLowerCase()}`}
          />
        </label>
      </div>
      {/* Logo and banner print on white paper; the symbol sits on the console's tile. */}
      <div
        className={clsx(
          "mt-2 flex h-16 items-center justify-center rounded border border-line p-2",
          field.kind === "symbol" ? "bg-symbol-tile" : "bg-white",
        )}
      >
        <img src={brandImageUrl(field.kind as BrandImage, version)} alt={`Current ${field.label.toLowerCase()}`} className="max-h-full max-w-full" />
      </div>
      <p className="mt-1 text-xs text-faint">PNG, up to 2 MB, {field.shape}.</p>
      {problem && (
        <p role="alert" className="mt-1 text-xs text-fail-ink">
          Not replaced. {problem}
        </p>
      )}
    </div>
  );
};

/** Names and colours are a draft until saved; images save as soon as they are picked. */
const BrandingForm = ({ brand }: { brand: Brand }) => {
  const saved = draftOf(brand);
  const [draft, setDraft] = useState<BrandInput>(saved);
  const [message, setMessage] = useState<string | null>(null);
  const settled = useSettled(draft);
  const complete = completeDraft(settled);
  const preview = useBrandPreview(complete);
  const { save } = useBrandWrites();

  const dirty = !sameDraft(draft, saved);
  const current = sameDraft(draft, settled) && preview.data !== undefined && !preview.isFetching;
  const canSave = dirty && completeDraft(draft) !== null && current && preview.data?.ok === true;

  const setText = (key: (typeof TEXT_FIELDS)[number]["key"], value: string) => {
    setMessage(null);
    setDraft((d) => ({ ...d, [key]: value }));
  };
  const setColour = (key: keyof Palette, value: string) => {
    setMessage(null);
    setDraft((d) => ({ ...d, palette: { ...d.palette, [key]: value } }));
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    const ready = completeDraft(draft);
    if (!ready) return;
    save.mutate(ready, {
      onSuccess: (next) => {
        setDraft(draftOf(next));
        setMessage("Saved. The console shows it now; the next report built uses it. Reports already made keep their old look.");
      },
    });
  };

  const light = preview.data?.light ?? brand.light;
  const dark = preview.data?.dark ?? brand.dark;
  return (
    <form onSubmit={submit} className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,22rem)]">
      <div className="space-y-6">
        <fieldset className="space-y-3">
          <legend className="mb-2 font-medium">Names</legend>
          {TEXT_FIELDS.map((field) => (
            <label key={field.key} className="block text-sm">
              <span className="font-medium">{field.label}</span>
              <span className="block text-xs text-muted">{field.hint}</span>
              <input
                value={draft[field.key]}
                onChange={(e) => setText(field.key, e.target.value)}
                maxLength={MAX_TEXT}
                required
                aria-invalid={draft[field.key].trim() === ""}
                className={clsx(fieldClass, "mt-1")}
              />
            </label>
          ))}
        </fieldset>

        <fieldset className="space-y-2">
          <legend className="mb-1 font-medium">Colours</legend>
          <p className="text-xs text-muted">
            Reports use these as given. The console works out its light and dark themes from them.
          </p>
          {COLOUR_FIELDS.map((field) => (
            <ColourField
              key={field.key}
              field={field}
              value={draft.palette[field.key]}
              onChange={(value) => setColour(field.key, value)}
            />
          ))}
        </fieldset>

        <div className="sticky bottom-0 flex flex-wrap items-center gap-2 border-t border-line bg-page py-3">
          <button type="submit" className={primaryClass} disabled={!canSave || save.isPending}>
            <Save aria-hidden size={14} />
            {save.isPending ? "Saving" : "Save names and colours"}
          </button>
          <button
            type="button"
            className={buttonClass}
            disabled={!dirty || save.isPending}
            onClick={() => {
              setDraft(saved);
              setMessage(null);
            }}
          >
            <RotateCcw aria-hidden size={14} />
            Undo changes
          </button>
          <p className="text-xs text-muted" role="status">
            {save.isError
              ? `Not saved. ${save.error.message}`
              : (message ??
                (!dirty
                  ? "No changes."
                  : completeDraft(draft) === null
                    ? "Fill in every name and give every colour six hex digits."
                    : !current
                      ? "Checking the colours."
                      : preview.data?.ok
                        ? "Ready to save."
                        : "Fix the colours marked under Readability to save."))}
          </p>
        </div>

        <section aria-labelledby="images-title" className="space-y-2">
          <h3 id="images-title" className="font-medium">
            Images
          </h3>
          <p className="text-xs text-muted">An image is saved as soon as you pick it. The one it replaces is kept as a .bak file beside it.</p>
          <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
            {IMAGE_FIELDS.map((field) => (
              <ImageField key={field.kind} field={field} version={brand.version} />
            ))}
          </div>
        </section>
      </div>

      <aside aria-label="Preview" className="space-y-4 lg:sticky lg:top-4 lg:self-start">
        <h3 className="font-medium">Preview</h3>
        <ConsolePreview theme="Light" tokens={light} draft={draft} version={brand.version} />
        <ConsolePreview theme="Dark" tokens={dark} draft={draft} version={brand.version} />
        <DocumentPreview draft={draft} version={brand.version} />
        {preview.data && <ContrastList checks={preview.data.checks} />}
        {preview.isError && (
          <p role="alert" className="text-xs text-fail-ink">
            Could not check the colours: {preview.error.message}
          </p>
        )}
      </aside>
    </form>
  );
};

const BrandingTab = () => {
  const brand = useBrand();
  if (!brand.data) return <LoadState error={brand.error} onRetry={() => void brand.refetch()} />;
  return (
    <>
      <p className="mb-4 text-sm text-muted">
        How {brand.data.name}'s reports and this console look. Saved to{" "}
        <code>config/companies/{brand.data.slug}/</code>, the file the report builders read.
      </p>
      {/* Keyed by company, so a different company starts a fresh draft. */}
      <BrandingForm key={brand.data.slug} brand={brand.data} />
    </>
  );
};

const SettingsPage = ({ section }: { section: SettingsSection }) => (
  <section aria-labelledby="settings-title">
    <h2 id="settings-title" className="mb-3 text-lg font-medium">
      Settings
    </h2>
    <nav aria-label="Settings" className="mb-4 flex gap-1">
      {SETTINGS_SECTIONS.map((s) => (
        <a
          key={s}
          href={settingsHref(s)}
          aria-current={s === section ? "page" : undefined}
          className={clsx(
            "rounded-md px-3 py-1.5 text-sm",
            s === section ? "bg-accent-soft font-medium text-accent-soft-ink" : "text-muted hover:bg-raised",
          )}
        >
          {SECTION_LABELS[s]}
        </a>
      ))}
    </nav>
    {section === "branding" && <BrandingTab />}
  </section>
);

export default SettingsPage;
