import { useRef, useState, type DragEvent, type FormEvent, type RefObject } from "react";
import { useNavigate } from "react-router-dom";
import {
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  FileSpreadsheet,
  TriangleAlert,
  Upload,
} from "lucide-react";
import { Button, Card, ErrorState, LoadingState, PageHeader } from "@/components";
import { confirmPortfolioUpload, uploadPortfolio } from "@/api/portfolios";
import { ApiError, toErrorMessage } from "@/models/errors";
import type {
  Holding,
  IssueSeverity,
  Portfolio,
  PortfolioPreview,
  PreviewHolding,
  PreviewStatus,
  SymbolValidationStatus,
  ValidationIssue,
} from "@/models";

const FLOW_STEPS = ["upload", "validate", "preview", "confirm", "complete"] as const;
type FlowStep = (typeof FLOW_STEPS)[number];

const STEP_LABELS: Record<FlowStep, string> = {
  upload: "Upload",
  validate: "Validate",
  preview: "Preview",
  confirm: "Confirm",
  complete: "Import complete",
};

const ACCEPT = ".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

export function UploadPortfolioPage() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);

  const [step, setStep] = useState<FlowStep>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [preview, setPreview] = useState<PortfolioPreview | null>(null);
  const [imported, setImported] = useState<Portfolio | null>(null);
  const [name, setName] = useState("");
  const [uploadError, setUploadError] = useState<unknown>(null);
  const [confirmError, setConfirmError] = useState<unknown>(null);
  const [clientMessage, setClientMessage] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);

  function resetToUpload() {
    setStep("upload");
    setFile(null);
    setPreview(null);
    setImported(null);
    setName("");
    setUploadError(null);
    setConfirmError(null);
    setClientMessage(null);
    setConfirming(false);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  async function validateFile(selected: File) {
    setFile(selected);
    setClientMessage(null);
    setUploadError(null);
    setConfirmError(null);
    setImported(null);
    setPreview(null);
    setStep("validate");
    try {
      const result = await uploadPortfolio(selected);
      setPreview(result);
      setStep("preview");
    } catch (error) {
      setUploadError(error);
      setStep("upload");
    }
  }

  function chooseFile(selected: File | undefined) {
    if (!selected) {
      return;
    }
    if (!isSupportedPortfolioFile(selected)) {
      setFile(null);
      setClientMessage("Choose a CSV or XLSX file. Other formats are not supported.");
      setUploadError(null);
      return;
    }
    if (selected.size === 0) {
      setFile(null);
      setClientMessage("The selected file is empty.");
      setUploadError(null);
      return;
    }
    void validateFile(selected);
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragOver(false);
    chooseFile(event.dataTransfer.files[0]);
  }

  async function onConfirm(event: FormEvent) {
    event.preventDefault();
    if (!preview?.can_confirm) {
      return;
    }
    setConfirming(true);
    setConfirmError(null);
    try {
      const portfolio = await confirmPortfolioUpload(preview.upload_id, {
        name: name.trim() || null,
      });
      setImported(portfolio);
      setStep("complete");
    } catch (error) {
      setConfirmError(error);
    } finally {
      setConfirming(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Upload Portfolio"
        description="Upload a CSV or XLSX file, review validation issues, then confirm import."
      />

      <FlowStepper current={step} />

      {step === "validate" ? (
        <LoadingState label="Validating the uploaded file..." />
      ) : null}

      {step === "upload" ? (
        <UploadStep
          inputRef={inputRef}
          dragOver={dragOver}
          file={file}
          clientMessage={clientMessage}
          uploadError={uploadError}
          onBrowse={() => inputRef.current?.click()}
          onFileChange={(selected) => chooseFile(selected)}
          onDragOverChange={setDragOver}
          onDrop={onDrop}
        />
      ) : null}

      {step === "preview" && preview ? (
        <PreviewStep
          preview={preview}
          onChooseAnother={resetToUpload}
          onContinue={() => setStep("confirm")}
        />
      ) : null}

      {step === "confirm" && preview ? (
        <ConfirmStep
          preview={preview}
          name={name}
          confirming={confirming}
          error={confirmError}
          onNameChange={setName}
          onBack={() => {
            setConfirmError(null);
            setStep("preview");
          }}
          onSubmit={onConfirm}
        />
      ) : null}

      {step === "complete" && imported ? (
        <CompleteStep
          portfolio={imported}
          warningCount={preview?.warning_count ?? 0}
          onUploadAnother={resetToUpload}
          onOpenAnalyzer={() =>
            navigate(`/portfolio?portfolioId=${encodeURIComponent(imported.id)}`)
          }
        />
      ) : null}
    </>
  );
}

function FlowStepper({ current }: { current: FlowStep }) {
  const currentIndex = FLOW_STEPS.indexOf(current);

  return (
    <ol className="mb-6 flex flex-wrap items-center gap-y-2" aria-label="Import progress">
      {FLOW_STEPS.map((item, index) => {
        const done = index < currentIndex;
        const active = index === currentIndex;
        return (
          <li key={item} className="flex items-center">
            {index > 0 ? (
              <ChevronRight className="mx-1 h-4 w-4 text-slate-300" aria-hidden />
            ) : null}
            <span
              className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs font-medium ${
                active
                  ? "bg-brand-700 text-white"
                  : done
                    ? "bg-brand-50 text-brand-800"
                    : "bg-slate-100 text-slate-500"
              }`}
              aria-current={active ? "step" : undefined}
            >
              <span className="tabular-nums">{index + 1}</span>
              {STEP_LABELS[item]}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

function UploadStep({
  inputRef,
  dragOver,
  file,
  clientMessage,
  uploadError,
  onBrowse,
  onFileChange,
  onDragOverChange,
  onDrop,
}: {
  inputRef: RefObject<HTMLInputElement | null>;
  dragOver: boolean;
  file: File | null;
  clientMessage: string | null;
  uploadError: unknown;
  onBrowse: () => void;
  onFileChange: (file: File | undefined) => void;
  onDragOverChange: (value: boolean) => void;
  onDrop: (event: DragEvent<HTMLDivElement>) => void;
}) {
  return (
    <div className="space-y-4">
      <Card>
        <div
          className={`flex min-h-[28vh] flex-col items-center justify-center rounded-md border border-dashed px-6 py-10 text-center ${
            dragOver ? "border-brand-600 bg-brand-50" : "border-slate-300 bg-slate-50"
          }`}
          onDragOver={(event) => {
            event.preventDefault();
            onDragOverChange(true);
          }}
          onDragLeave={() => onDragOverChange(false)}
          onDrop={onDrop}
        >
          <Upload className="h-8 w-8 text-brand-700" />
          <p className="mt-3 text-sm font-medium text-slate-800">
            Drop a CSV or XLSX file here
          </p>
          <p className="mt-1 max-w-md text-sm text-slate-500">
            Required columns: symbol (or ticker) and quantity (or shares). Optional:
            average_cost, currency, name, weight.
          </p>
          <input
            ref={inputRef}
            id="portfolio-file"
            type="file"
            className="sr-only"
            accept={ACCEPT}
            aria-label="Portfolio CSV or XLSX file"
            onChange={(event) => {
              const selected = event.target.files?.[0];
              event.target.value = "";
              onFileChange(selected);
            }}
          />
          <Button className="mt-4" onClick={onBrowse}>
            <FileSpreadsheet className="h-4 w-4" />
            Choose file
          </Button>
          {file ? (
            <p className="mt-3 text-xs text-slate-500">{file.name}</p>
          ) : null}
        </div>
      </Card>

      {clientMessage ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900" role="alert">
          {clientMessage}
        </div>
      ) : null}

      {uploadError ? (
        <ErrorState
          error={uploadError}
          title="The file could not be uploaded"
          onRetry={onBrowse}
        />
      ) : null}

      {uploadError instanceof ApiError && uploadError.issues?.length ? (
        <IssueList
          title="Upload errors"
          issues={uploadError.issues.map(asValidationIssue)}
          severity="error"
        />
      ) : null}
    </div>
  );
}

function PreviewStep({
  preview,
  onChooseAnother,
  onContinue,
}: {
  preview: PortfolioPreview;
  onChooseAnother: () => void;
  onContinue: () => void;
}) {
  const errors = preview.issues.filter((issue) => issue.severity === "error");
  const warnings = preview.issues.filter((issue) => issue.severity === "warning");
  const validRows = preview.holdings.filter((holding) => holding.valid).length;

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <PreviewStatusBadge status={preview.status} />
              <span className="text-sm font-medium text-slate-800">{preview.filename}</span>
              {preview.format ? (
                <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs uppercase text-slate-600">
                  {preview.format}
                </span>
              ) : null}
            </div>
            <p className="mt-2 text-sm text-slate-500">
              {validRows} importable of {preview.holding_count} rows · {preview.error_count}{" "}
              {preview.error_count === 1 ? "error" : "errors"} · {preview.warning_count}{" "}
              {preview.warning_count === 1 ? "warning" : "warnings"}
            </p>
            <p className="mt-1 text-xs text-slate-400">
              Preview expires {formatDate(preview.expires_at)}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" onClick={onChooseAnother}>
              Choose another file
            </Button>
            <Button onClick={onContinue} disabled={!preview.can_confirm}>
              Continue to confirm
            </Button>
          </div>
        </div>
        {!preview.can_confirm ? (
          <p className="mt-3 text-sm text-red-700">
            Resolve every validation error in the file before this portfolio can be imported.
          </p>
        ) : preview.warning_count > 0 ? (
          <p className="mt-3 text-sm text-amber-800">
            Warnings will not block import. Review them before confirming.
          </p>
        ) : (
          <p className="mt-3 text-sm text-slate-600">
            Validation passed. Continue to confirm import. No market data is attached at this
            step.
          </p>
        )}
      </Card>

      {errors.length ? <IssueList title="Errors" issues={errors} severity="error" /> : null}
      {warnings.length ? (
        <IssueList title="Warnings" issues={warnings} severity="warning" />
      ) : null}

      <Card title="Holdings preview">
        {preview.holdings.length === 0 ? (
          <p className="text-sm text-slate-500">No holdings were parsed from this file.</p>
        ) : (
          <HoldingsTable holdings={preview.holdings} />
        )}
      </Card>
    </div>
  );
}

function ConfirmStep({
  preview,
  name,
  confirming,
  error,
  onNameChange,
  onBack,
  onSubmit,
}: {
  preview: PortfolioPreview;
  name: string;
  confirming: boolean;
  error: unknown;
  onNameChange: (value: string) => void;
  onBack: () => void;
  onSubmit: (event: FormEvent) => void;
}) {
  const importable = preview.holdings.filter((holding) => holding.valid);

  return (
    <div className="space-y-4">
      {error ? (
        <ErrorState error={error} title="Import could not be confirmed" />
      ) : null}

      {error instanceof ApiError && error.issues?.length ? (
        <IssueList
          title="Import errors"
          issues={error.issues.map(asValidationIssue)}
          severity="error"
        />
      ) : null}

      <Card title="Confirm import">
        <form className="space-y-4" onSubmit={onSubmit}>
          <p className="text-sm text-slate-600">
            {importable.length} {importable.length === 1 ? "holding" : "holdings"} from{" "}
            <span className="font-medium text-slate-800">{preview.filename}</span> will be
            stored. Import does not fetch market prices or run analysis.
          </p>

          {preview.warning_count > 0 ? (
            <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
              <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                This file has {preview.warning_count}{" "}
                {preview.warning_count === 1 ? "warning" : "warnings"}. You can still import it.
              </span>
            </div>
          ) : null}

          <label className="block text-sm">
            <span className="font-medium text-slate-700">Portfolio name (optional)</span>
            <input
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-600"
              value={name}
              onChange={(event) => onNameChange(event.target.value)}
              placeholder="Core holdings"
              maxLength={120}
            />
          </label>

          <ul className="flex flex-wrap gap-2">
            {importable.map((holding) => (
              <li
                key={`${holding.row}-${holding.symbol}`}
                className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700"
              >
                {holding.symbol ?? "—"}
              </li>
            ))}
          </ul>

          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="secondary" onClick={onBack} disabled={confirming}>
              Back to preview
            </Button>
            <Button type="submit" disabled={!preview.can_confirm || confirming}>
              {confirming ? "Importing..." : "Confirm import"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

function CompleteStep({
  portfolio,
  warningCount,
  onUploadAnother,
  onOpenAnalyzer,
}: {
  portfolio: Portfolio;
  warningCount: number;
  onUploadAnother: () => void;
  onOpenAnalyzer: () => void;
}) {
  return (
    <div className="space-y-4">
      <Card>
        <div className="flex items-start gap-3">
          <CheckCircle2 className="mt-0.5 h-6 w-6 shrink-0 text-brand-700" />
          <div className="min-w-0 flex-1">
            <h3 className="text-sm font-semibold text-slate-900">Import complete</h3>
            <p className="mt-1 text-sm text-slate-600">
              {portfolio.name ?? "Untitled portfolio"} is available for analysis. This screen
              does not run portfolio or market analysis.
            </p>
            <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-slate-500">Holdings</dt>
                <dd className="font-medium text-slate-800">{portfolio.holding_count}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Source</dt>
                <dd className="font-medium text-slate-800">
                  {portfolio.source_filename}{" "}
                  <span className="uppercase text-slate-500">{portfolio.source_format}</span>
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">Imported</dt>
                <dd className="font-medium text-slate-800">{formatDate(portfolio.imported_at)}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Base currency</dt>
                <dd className="font-medium text-slate-800">{portfolio.base_currency ?? "—"}</dd>
              </div>
            </dl>
            {warningCount > 0 ? (
              <p className="mt-3 text-sm text-amber-800">
                Imported with {warningCount} {warningCount === 1 ? "warning" : "warnings"}.
              </p>
            ) : null}
            <ul className="mt-4 flex flex-wrap gap-2">
              {portfolio.holdings.map((holding: Holding) => (
                <li
                  key={holding.symbol}
                  className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700"
                >
                  {holding.symbol}
                </li>
              ))}
            </ul>
            <div className="mt-5 flex flex-wrap gap-2">
              <Button onClick={onOpenAnalyzer}>Open Portfolio Analyzer</Button>
              <Button variant="secondary" onClick={onUploadAnother}>
                Upload another file
              </Button>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}

function IssueList({
  title,
  issues,
  severity,
}: {
  title: string;
  issues: ValidationIssue[];
  severity: IssueSeverity;
}) {
  const isError = severity === "error";
  return (
    <Card title={title}>
      <ul className="space-y-2" role="list">
        {issues.map((issue, index) => (
          <li
            key={`${issue.code}-${issue.row}-${issue.column}-${index}`}
            className={`flex items-start gap-2 rounded-md px-3 py-2 text-sm ${
              isError ? "bg-red-50 text-red-800" : "bg-amber-50 text-amber-900"
            }`}
          >
            {isError ? (
              <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />
            ) : (
              <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />
            )}
            <span>
              <span className="font-medium">{issue.message}</span>
              <span className="mt-0.5 block text-xs opacity-80">
                {issue.code}
                {issue.row != null ? ` · row ${issue.row}` : ""}
                {issue.column ? ` · ${issue.column}` : ""}
                {issue.value ? ` · ${issue.value}` : ""}
              </span>
            </span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function HoldingsTable({ holdings }: { holdings: PreviewHolding[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-2 py-2 font-medium">Row</th>
            <th className="px-2 py-2 font-medium">Symbol</th>
            <th className="px-2 py-2 font-medium">Quantity</th>
            <th className="px-2 py-2 font-medium">Avg cost</th>
            <th className="px-2 py-2 font-medium">Currency</th>
            <th className="px-2 py-2 font-medium">Name</th>
            <th className="px-2 py-2 font-medium">Weight</th>
            <th className="px-2 py-2 font-medium">Cost value</th>
            <th className="px-2 py-2 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((holding) => (
            <tr
              key={holding.row}
              className={`border-b border-slate-100 ${holding.valid ? "" : "bg-red-50"}`}
            >
              <td className="px-2 py-2 tabular-nums text-slate-500">{holding.row}</td>
              <td className="px-2 py-2 font-medium text-slate-800">
                {holding.symbol ?? "—"}
                <div className="mt-0.5">
                  <SymbolStatusBadge status={holding.symbol_validation.status} />
                </div>
              </td>
              <td className="px-2 py-2 tabular-nums">{formatNumber(holding.quantity)}</td>
              <td className="px-2 py-2 tabular-nums">{formatNumber(holding.average_cost)}</td>
              <td className="px-2 py-2">{holding.currency ?? "—"}</td>
              <td className="px-2 py-2">{holding.name ?? "—"}</td>
              <td className="px-2 py-2 tabular-nums">{formatWeight(holding.weight)}</td>
              <td className="px-2 py-2 tabular-nums">{formatNumber(holding.cost_value)}</td>
              <td className="px-2 py-2">
                {holding.valid ? (
                  <span className="text-brand-700">Valid</span>
                ) : (
                  <span className="text-red-700">Invalid</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PreviewStatusBadge({ status }: { status: PreviewStatus }) {
  const styles: Record<PreviewStatus, string> = {
    valid: "bg-emerald-50 text-emerald-800",
    valid_with_warnings: "bg-amber-50 text-amber-900",
    invalid: "bg-red-50 text-red-800",
  };
  const labels: Record<PreviewStatus, string> = {
    valid: "Valid",
    valid_with_warnings: "Valid with warnings",
    invalid: "Invalid",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${styles[status]}`}>
      {labels[status]}
    </span>
  );
}

function SymbolStatusBadge({ status }: { status: SymbolValidationStatus }) {
  const styles: Record<SymbolValidationStatus, string> = {
    valid: "text-emerald-700",
    invalid: "text-red-700",
    missing: "text-slate-500",
  };
  return <span className={`text-xs ${styles[status]}`}>{status}</span>;
}

function isSupportedPortfolioFile(file: File): boolean {
  const extension = fileExtension(file.name);
  return extension === ".csv" || extension === ".xlsx";
}

function fileExtension(name: string): string {
  const index = name.lastIndexOf(".");
  return index >= 0 ? name.slice(index).toLowerCase() : "";
}

function formatNumber(value: number | null | undefined): string {
  if (value == null) {
    return "—";
  }
  return value.toLocaleString(undefined, { maximumFractionDigits: 4 });
}

function formatWeight(value: number | null | undefined): string {
  if (value == null) {
    return "—";
  }
  return `${(value * 100).toLocaleString(undefined, { maximumFractionDigits: 2 })}%`;
}

function formatDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

function asValidationIssue(issue: Record<string, unknown>): ValidationIssue {
  return {
    severity: issue.severity === "warning" ? "warning" : "error",
    code: typeof issue.code === "string" ? issue.code : "unknown",
    message:
      typeof issue.message === "string" ? issue.message : toErrorMessage(issue.message),
    row: typeof issue.row === "number" ? issue.row : null,
    column: typeof issue.column === "string" ? issue.column : null,
    value: typeof issue.value === "string" ? issue.value : issue.value == null ? null : String(issue.value),
  };
}
