import { apiGet } from "../../lib/api";
import type { SubstrateBatch } from "../../lib/types";

export default async function Batches() {
  const batches = await apiGet<SubstrateBatch[]>("/batches");

  return (
    <div className="card">
      <h1>Batches</h1>
      <table className="table">
        <thead>
          <tr><th>ID</th><th>Name</th><th>Bags</th></tr>
        </thead>
        <tbody>
          {batches.map(b => (
            <tr key={b.substrate_batch_id}>
              <td>{b.substrate_batch_id}</td>
              <td><a href={`/batches/${b.substrate_batch_id}`}>{b.name}</a></td>
              <td>{b.bag_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p><a className="btn" href="/batches/new">Create new batch</a></p>
    </div>
  );
}
