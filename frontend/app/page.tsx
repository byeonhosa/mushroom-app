export default function Home() {
  return (
    <div className="card">
      <h1>Welcome</h1>
      <p>
        Bag-focused production: create run-level bag records, assign printable bag codes at inoculation, record
        lifecycle events, and trace bags back to thermal batches.
      </p>
      <p>
        <a className="btn" href="/bags">View Bags</a>
        <a className="btn" href="/bags/create/spawn" style={{ marginLeft: 8 }}>Create Spawn Records</a>
        <a className="btn" href="/events/spawn-inoculation" style={{ marginLeft: 8 }}>Spawn Inoculation</a>
        <a className="btn" href="/bags/create/substrate" style={{ marginLeft: 8 }}>Create Substrate Records</a>
        <a className="btn" href="/reports" style={{ marginLeft: 8 }}>Reports</a>
      </p>
    </div>
  );
}
