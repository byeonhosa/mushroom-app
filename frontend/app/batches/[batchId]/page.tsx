"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiGet } from "../../../lib/api";
import type { SubstrateBag, BatchMetrics, BatchInoculation } from "../../../lib/types";

export default function BatchDetail() {
  const params = useParams();
  const batchIdRaw = params?.batchId; // string | string[] | undefined

  const batchId =
    typeof batchIdRaw === "string"
      ? batchIdRaw
      : Array.isArray(batchIdRaw)
      ? batchIdRaw[0]
      : undefined;

  const [bags, setBags] = useState<SubstrateBag[]>([]);
  const [metrics, setMetrics] = useState<BatchMetrics | null>(null);
  const [inoculation, setInoculation] = useState<BatchInoculation | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!batchId) return;

    (async () => {
      try {
        setError(null);
        const [bagsRes, metricsRes] = await Promise.all([
          apiGet<SubstrateBag[]>(`/batches/${batchId}/bags`),
          apiGet<BatchMetrics>(`/batches/${batchId}/metrics`),
        ]);
        setBags(bagsRes);
        setMetrics(metricsRes);
        try {
          const inoc = await apiGet<BatchInoculation>(`/batches/${batchId}/inoculation`);
          setInoculation(inoc);
        } catch {
          setInoculation(null);
        }
      } catch (e: any) {
        setError(e?.message || String(e));
      }
    })();
  }, [batchId]);

  if (!batchId) {
    return (
      <div className="card">
        <h1>Batch</h1>
        <p className="error">Missing batchId in route params.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h1>Batch {batchId}</h1>

      {error && <p className="error">{error}</p>}

      {!metrics ? (
        <p>Loading…</p>
      ) : (
        <div className="kpis">
          <div>
            <div className="kpiLabel">Total Harvest (kg)</div>
            <div className="kpi">{metrics.total_harvest_kg.toFixed(3)}</div>
          </div>
          <div>
            <div className="kpiLabel">Dry Mass Total (kg)</div>
            <div className="kpi">{metrics.dry_kg_total.toFixed(3)}</div>
          </div>
          <div>
            <div className="kpiLabel">BE%</div>
            <div className="kpi">{metrics.be_percent.toFixed(1)}</div>
          </div>
        </div>
      )}

      <h2>Inoculation</h2>
      {!inoculation ? (
        <p>No inoculation record.</p>
      ) : (
        <p>
          Spawn Batch #{inoculation.spawn_batch_id} ({inoculation.spawn_batch.strain_code} / {inoculation.spawn_batch.spawn_type})
          {" "}at {new Date(inoculation.inoculated_at).toLocaleString()}
          {inoculation.spawn_blocks_used ? ` using ${inoculation.spawn_blocks_used} block(s)` : ""}
        </p>
      )}

      <h2>Bags</h2>
      <ul className="list">
        {bags.map((b) => (
          <li key={b.bag_id}>
            <a href={`/bags/${encodeURIComponent(b.bag_id)}`}>{b.bag_id}</a> —{" "}
            {b.status}
          </li>
        ))}
      </ul>
    </div>
  );
}
