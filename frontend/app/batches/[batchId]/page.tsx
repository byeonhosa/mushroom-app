import { apiGet } from "../../../lib/api";
import type { SubstrateBag, BatchMetrics } from "../../../lib/types";

export default async function BatchDetail({ params }: { params: { batchId: string } }) {
  const id = params.batchId;
  const bags = await apiGet<SubstrateBag[]>(`/batches/${id}/bags`);
  const metrics = await apiGet<BatchMetrics>(`/batches/${id}/metrics`);

  return (
    <div className="card">
      <h1>Batch {id}</h1>
      <div className="kpis">
        <div><div className="kpiLabel">Total Harvest (kg)</div><div className="kpi">{metrics.total_harvest_kg.toFixed(3)}</div></div>
        <div><div className="kpiLabel">Dry Mass Total (kg)</div><div className="kpi">{metrics.dry_kg_total.toFixed(3)}</div></div>
        <div><div className="kpiLabel">BE%</div><div className="kpi">{metrics.be_percent.toFixed(1)}</div></div>
      </div>

      <h2>Bags</h2>
      <ul className="list">
        {bags.map(b => (
          <li key={b.bag_id}>
            <a href={`/bags/${encodeURIComponent(b.bag_id)}`}>{b.bag_id}</a> — {b.status}
          </li>
        ))}
      </ul>
    </div>
  );
}
