export default function NewBatchDeprecatedPage() {
  return (
    <div className="card">
      <h1>New Batch Deprecated</h1>
      <p>Deprecated: use Blocks + Pasteurization Runs.</p>
      <p>
        <a className="btn" href="/blocks/new">Create Block</a>
      </p>
      <p>
        <a className="btn" href="/pasteurization-runs">Go to Pasteurization Runs</a>
      </p>
    </div>
  );
}
