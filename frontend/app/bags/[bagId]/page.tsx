import { apiGet } from "../../../lib/api";
import type { BagDetail } from "../../../lib/types";

export default async function BagPage({ params }: { params: { bagId: string } }) {
  const bagId = decodeURIComponent(params.bagId);
  const bag = await apiGet<BagDetail>(`/bags/${encodeURIComponent(bagId)}`);

  return (
    <div className="card">
      <h1>Bag {bag.bag_id}</h1>
      <p>Status: {bag.status}</p>

      <h2>Harvest Events</h2>
      {bag.harvest_events.length === 0 ? (
        <p>No harvests logged.</p>
      ) : (
        <table className="table">
          <thead>
            <tr><th>Date</th><th>Flush</th><th>kg</th></tr>
          </thead>
          <tbody>
            {bag.harvest_events.map(h => (
              <tr key={h.harvest_event_id}>
                <td>{new Date(h.harvested_at).toLocaleString()}</td>
                <td>{h.flush_number}</td>
                <td>{h.fresh_weight_kg.toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <p><a className="btn" href={`/bags/${encodeURIComponent(bag.bag_id)}/harvest`}>Log harvest</a></p>
    </div>
  );
}
