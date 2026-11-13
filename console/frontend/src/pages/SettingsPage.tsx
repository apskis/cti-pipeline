import clsx from "clsx";
import { Copy, Plus, RotateCcw, Save, Upload } from "lucide-react";
import { type ChangeEvent, type FormEvent, useRef, useState } from "react";

import {
  brandImageUrl,
  useBrand,
  useBrandPreview,
  useBrandWrites,
  useCompanies,
  useCompanyWrites,
} from "../api/client";
import type { Brand, BrandImage, BrandInput, Company, Palette } from "../api/types";
import { ConsolePreview, ContrastList, DocumentPreview } from "../components/BrandPreviews";
import LoadState from "../components/LoadState";
import {
  COLOUR_FIELDS,
  completeDraft,
  draftOf,
  IMAGE_FIELDS,
  isHex,
  isSlug,
  MAX_TEXT,
  normaliseHex,
  sameDraft,
  slugOf,
  TEXT_FIELDS,
  useSettled,
} from "../lib/branding";
import { SETTINGS_SECTIONS, type SettingsSection, settingsHref } from "../lib/route";

const fieldClass = "w-full rounded-md border border-line bg-surface px-2 py-1.5 text-sm";
const buttonClass =
  "inline-flex items-center gap-1.5 rounded-md border border-line px-3 py-1.5 text-sm hover:bg-raised disabled:opacity-50";
const primaryClass =
  "inline-flex items-center gap-1.5 rounded-md bg-accent px-3 py-1.5 text-sm text-on-accent hover:bg-accent-hover disabled:opacity-50";

const SECTION_LABELS: Record<SettingsSection, string> = { branding: "Branding", companies: "Companies" };

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
        <code>data/companies/{brand.data.slug}/</code>, the folder the report builders read.
      </p>
      {/* Keyed by company, so a different company starts a fresh draft. */}
      <BrandingForm key={brand.data.slug} brand={brand.data} />
    </>
  );
};

/** One company in the list: what it is, and buttons to show it or copy it. */
const CompanyRow = ({
  company,
  active,
  busy,
  onShow,
  onCopy,
}: {
  company: Company;
  active: boolean;
  busy: boolean;
  onShow: () => void;
  onCopy: () => void;
}) => (
  <li className="flex flex-wrap items-center gap-3 rounded-lg border border-line bg-surface px-3 py-2">
    <div className="min-w-0 flex-1">
      <p className="text-sm font-medium">
        {company.name}
        {active && (
          <span className="ml-2 rounded bg-accent-soft px-1.5 py-0.5 text-xs font-medium text-accent-soft-ink">
            Shown now
          </span>
        )}
      </p>
      <p className="text-xs text-muted">
        Short name <code>{company.slug}</code>.{" "}
        {company.pipeline ? "The pipeline writes its reports." : "No pipeline runs for it yet."}
      </p>
    </div>
    {!active && (
      <button type="button" className={buttonClass} disabled={busy} onClick={onShow}>
        Show this company
      </button>
    )}
    <button type="button" className={buttonClass} onClick={onCopy} aria-label={`Copy ${company.name}`}>
      <Copy aria-hidden size={14} />
      Copy
    </button>
  </li>
);

const slugProblem = (slug: string, taken: boolean): string => {
  if (taken) return "Another company already uses this short name.";
  if (slug !== "" && !isSlug(slug)) return "Start with a letter or digit; use only a to z, 0 to 9 and hyphens.";
  return "";
};

/** Every company, and a form to add one, blank or copied from another's branding. */
const CompaniesTab = () => {
  const companies = useCompanies();
  const { pick, create } = useCompanyWrites();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  // The short name follows the name until it is typed into; after that it is left alone.
  const [slugTouched, setSlugTouched] = useState(false);
  const [source, setSource] = useState("");
  const nameInput = useRef<HTMLInputElement>(null);

  if (!companies.data) return <LoadState error={companies.error} onRetry={() => void companies.refetch()} />;
  const { active, companies: list } = companies.data;
  const taken = list.some((c) => c.slug === slug);
  const ready = name.trim() !== "" && isSlug(slug) && !taken;
  const busy = create.isPending || pick.isPending;
  const problem = slugProblem(slug, taken);

  const changeName = (value: string, follow = !slugTouched) => {
    setName(value);
    if (follow) setSlug(slugOf(value));
  };
  const copyOf = (company: Company) => {
    setSource(company.slug);
    setSlugTouched(false);
    changeName(`${company.name} copy`, true);
    nameInput.current?.focus();
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!ready) return;
    create.mutate(
      { name: name.trim(), slug, source: source || null },
      {
        // A new company is shown at once, on its Branding tab, where it is set up next.
        onSuccess: () =>
          pick.mutate(slug, {
            onSuccess: () => {
              window.location.hash = settingsHref("branding");
            },
          }),
      },
    );
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,22rem)]">
      <section aria-labelledby="company-list-title" className="space-y-2">
        <h3 id="company-list-title" className="font-medium">
          Companies
        </h3>
        <p className="text-xs text-muted">
          Each company has its own branding, stakeholders, reports and logs. The console shows one at a time; pick it
          here or in the header.
        </p>
        <ul className="space-y-2">
          {list.map((company) => (
            <CompanyRow
              key={company.slug}
              company={company}
              active={company.slug === active}
              busy={busy}
              onShow={() => pick.mutate(company.slug)}
              onCopy={() => copyOf(company)}
            />
          ))}
        </ul>
        {pick.isError && (
          <p role="alert" className="text-xs text-fail-ink">
            Not switched. {pick.error.message}
          </p>
        )}
      </section>

      <form
        onSubmit={submit}
        aria-labelledby="add-company-title"
        className="space-y-3 self-start rounded-lg border border-line bg-surface p-4"
      >
        <h3 id="add-company-title" className="font-medium">
          Add a company
        </h3>
        <label className="block text-sm">
          <span className="font-medium">Company name</span>
          <input
            ref={nameInput}
            value={name}
            onChange={(e) => changeName(e.target.value)}
            maxLength={MAX_TEXT}
            required
            className={clsx(fieldClass, "mt-1")}
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium">Short name</span>
          <span className="block text-xs text-muted">Names its folder. Lower case letters, digits and hyphens.</span>
          <input
            value={slug}
            onChange={(e) => {
              setSlugTouched(true);
              setSlug(e.target.value.toLowerCase());
            }}
            maxLength={40}
            required
            spellCheck={false}
            aria-invalid={problem !== ""}
            aria-describedby="slug-problem"
            className={clsx(fieldClass, "mt-1 font-mono")}
          />
          <span id="slug-problem" className="block text-xs text-fail-ink">
            {problem}
          </span>
        </label>
        <label className="block text-sm">
          <span className="font-medium">Start from</span>
          <select value={source} onChange={(e) => setSource(e.target.value)} className={clsx(fieldClass, "mt-1")}>
            <option value="">A blank brand, to fill in</option>
            {list.map((c) => (
              <option key={c.slug} value={c.slug}>
                {`A copy of ${c.name}'s branding`}
              </option>
            ))}
          </select>
          <span className="block text-xs text-muted">Only branding is copied, never stakeholders, reports or logs.</span>
        </label>
        <button type="submit" className={primaryClass} disabled={!ready || busy}>
          <Plus aria-hidden size={14} />
          {create.isPending ? "Adding" : "Add and show it"}
        </button>
        {create.isError && (
          <p role="alert" className="text-xs text-fail-ink">
            Not added. {create.error.message}
          </p>
        )}
      </form>
    </div>
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
    {section === "companies" && <CompaniesTab />}
  </section>
);

export default SettingsPage;
