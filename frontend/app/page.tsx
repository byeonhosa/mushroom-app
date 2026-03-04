export default function Home() {
  return (
    <div className="card">
      <h1>Welcome</h1>
      <p>
        Bag-focused production: record spawn and substrate bags, track inoculations,
        record harvest flushes, and trace bags to thermal batches.
      </p>
      <p>
        <a className="btn" href="/bags">View Bags</a>
        <a className="btn" href="/bags/create/spawn" style={{ marginLeft: 8 }}>Create Spawn Bags</a>
        <a className="btn" href="/bags/create/substrate" style={{ marginLeft: 8 }}>Record Substrate Bags</a>
      </p>
    </div>
  );
}
