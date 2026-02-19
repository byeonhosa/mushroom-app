export default function BatchesDeprecatedPage() {
  return (
    <div className="card">
      <h1>Batches Deprecated</h1>
      <p>Deprecated: use Blocks + Pasteurization Runs.</p>
      <p>
        <a className="btn" href="/blocks">Go to Blocks</a>
      </p>
      <p>
        <a className="btn" href="/pasteurization-runs">Go to Pasteurization Runs</a>
      </p>
    </div>
  );
}
