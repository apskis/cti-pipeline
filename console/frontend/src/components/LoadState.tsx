interface LoadStateProps {
  error: Error | null;
  onRetry: () => void;
}

/** Shown while the first answer is on its way, or when the backend cannot be reached. */
const LoadState = ({ error, onRetry }: LoadStateProps) => {
  if (!error) {
    return (
      <p className="py-12 text-center text-muted" role="status">
        Reading the pipeline output. The first load reads every document and takes a few seconds.
      </p>
    );
  }
  return (
    <div className="mx-auto max-w-lg rounded-xl border border-line bg-surface p-6" role="alert">
      <p className="font-medium">The console backend did not answer.</p>
      <p className="mt-2 text-sm text-muted">
        Start it with <code>python -m cti_console</code> in <code>console/backend</code>, then retry.
      </p>
      <p className="mt-2 text-xs text-faint">{error.message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-4 rounded-md border border-line px-3 py-1.5 text-sm hover:bg-raised"
      >
        Retry
      </button>
    </div>
  );
};

export default LoadState;
