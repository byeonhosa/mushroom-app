"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiGet } from "../../../lib/api";
import type { SterilizationRunDetail } from "../../../lib/types";

function formatPercent(value: number | null | undefined) {
  if (value == null) {
    return "-";
  }
  return `${(value * 100).toFixed(1)}%`;
}

export default function SterilizationRunDetailPage() {
  const params = useParams();
  const runIdRaw = params?.runId;
  const runId = typeof runIdRaw === "string" ? runIdRaw : Array.isArray(runIdRaw) ? runIdRaw[0] : undefined;
  const [run, setRun] = useState<SterilizationRunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) {
      return;
    }
    (async () => {
      try {
        setError(null);
        setRun(await apiGet<SterilizationRunDetail>(`/sterilization-runs/${encodeURIComponent(runId)}/detail`));
      } catch (e: any) {
        setError(e?.message || String(e));
      }
    })();
  }, [runId]);

  if (!runId) {
    return (
      <div className="card">
        <h1>Sterilization Run</h1>
        <p className="error">Missing run ID.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="card">
        <h1>Sterilization Run Detail</h1>
        {error && <p className="error">{error}</p>}
        {!run ? (
          <p>Loading...</p>
        ) : (
          <>
            <p>Run Code: {run.run_code}</p>
            <p>Run ID: {run.sterilization_run_id}</p>
            <p>Unloaded At: {new Date(run.unloaded_at).toLocaleString()}</p>
            <p>Bag Count: {run.bag_count}</p>
            <p>Consumed Spawn Bags: {run.summary.consumed_bags}</p>
            <p>Downstream Substrate Bags: {run.downstream_summary.total_bags}</p>
            <p>Downstream Contamination: {run.downstream_summary.contaminated_bags}</p>
            <p>Downstream Harvest: {run.downstream_summary.total_harvest_kg.toFixed(3)} kg</p>
            <p>Downstream BE: {formatPercent(run.downstream_summary.overall_bio_efficiency)}</p>
          </>
        )}
      </div>

      {run && (
        <>
          <div className="card">
            <h2>Spawn Bags In This Run</h2>
            <table className="table">
              <thead>
                <tr>
                  <th>Bag</th>
                  <th>Status</th>
                  <th>Labeled</th>
                  <th>Ready</th>
                  <th>Consumed</th>
                </tr>
              </thead>
              <tbody>
                {run.bags.map((bag) => (
                  <tr key={bag.bag_id}>
                    <td>
                      <a href={`/bags/${encodeURIComponent(bag.bag_ref)}`}>{bag.bag_ref}</a>
                    </td>
                    <td>{bag.status}</td>
                    <td>{bag.labeled_at ? new Date(bag.labeled_at).toLocaleDateString() : "-"}</td>
                    <td>{bag.ready_at ? new Date(bag.ready_at).toLocaleDateString() : "-"}</td>
                    <td>{bag.consumed_at ? new Date(bag.consumed_at).toLocaleDateString() : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {run.bags.length === 0 && <p>No spawn bags recorded for this run.</p>}
          </div>

          <div className="card">
            <h2>Downstream Substrate Outcomes</h2>
            {run.downstream_substrate_bags.length === 0 ? (
              <p>No downstream substrate bags found yet.</p>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Bag</th>
                    <th>Pasteurization Run</th>
                    <th>Status</th>
                    <th>Harvest</th>
                    <th>Dry Weight</th>
                    <th>BE</th>
                  </tr>
                </thead>
                <tbody>
                  {run.downstream_substrate_bags.map((bag) => (
                    <tr key={bag.bag_id}>
                      <td>
                        <a href={`/bags/${encodeURIComponent(bag.bag_ref)}`}>{bag.bag_ref}</a>
                      </td>
                      <td>
                        {bag.pasteurization_run_id ? (
                          <a href={`/pasteurization-runs/${bag.pasteurization_run_id}`}>
                            {bag.pasteurization_run_code ?? bag.pasteurization_run_id}
                          </a>
                        ) : (
                          "-"
                        )}
                      </td>
                      <td>{bag.contaminated ? "CONTAMINATED" : bag.status}</td>
                      <td>{bag.total_harvest_kg.toFixed(3)} kg</td>
                      <td>
                        {bag.dry_weight_kg != null ? `${bag.dry_weight_kg.toFixed(3)} kg (${bag.dry_weight_source ?? "-"})` : "-"}
                      </td>
                      <td>{formatPercent(bag.bio_efficiency)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}
