"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiGet } from "../../../lib/api";
import type { PasteurizationRunDetail } from "../../../lib/types";

function formatPercent(value: number | null | undefined) {
  if (value == null) {
    return "-";
  }
  return `${(value * 100).toFixed(1)}%`;
}

export default function PasteurizationRunDetailPage() {
  const params = useParams();
  const runIdRaw = params?.runId;
  const runId = typeof runIdRaw === "string" ? runIdRaw : Array.isArray(runIdRaw) ? runIdRaw[0] : undefined;
  const [run, setRun] = useState<PasteurizationRunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) {
      return;
    }
    (async () => {
      try {
        setError(null);
        setRun(await apiGet<PasteurizationRunDetail>(`/pasteurization-runs/${encodeURIComponent(runId)}/detail`));
      } catch (e: any) {
        setError(e?.message || String(e));
      }
    })();
  }, [runId]);

  if (!runId) {
    return (
      <div className="card">
        <h1>Pasteurization Run</h1>
        <p className="error">Missing run ID.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="card">
        <h1>Pasteurization Run Detail</h1>
        {error && <p className="error">{error}</p>}
        {!run ? (
          <p>Loading...</p>
        ) : (
          <>
            <p>Run Code: {run.run_code}</p>
            <p>Run ID: {run.pasteurization_run_id}</p>
            <p>Unloaded At: {new Date(run.unloaded_at).toLocaleString()}</p>
            <p>Bag Count: {run.bag_count}</p>
            <p>Contaminated Bags: {run.summary.contaminated_bags}</p>
            <p>Total Harvest: {run.summary.total_harvest_kg.toFixed(3)} kg</p>
            <p>Total Dry Weight: {run.summary.total_dry_weight_kg.toFixed(3)} kg</p>
            <p>Run BE: {formatPercent(run.summary.overall_bio_efficiency)}</p>
          </>
        )}
      </div>

      {run && (
        <div className="card">
          <h2>Substrate Bags In This Run</h2>
          {run.bags.length === 0 ? (
            <p>No substrate bags recorded for this run.</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Bag</th>
                  <th>Parent Spawn</th>
                  <th>Source Sterilization</th>
                  <th>Status</th>
                  <th>Harvest</th>
                  <th>Dry Weight</th>
                  <th>BE</th>
                </tr>
              </thead>
              <tbody>
                {run.bags.map((bag) => (
                  <tr key={bag.bag_id}>
                    <td>
                      <a href={`/bags/${encodeURIComponent(bag.bag_ref)}`}>{bag.bag_ref}</a>
                    </td>
                    <td>
                      {bag.parent_spawn_bag_ref ? (
                        <a href={`/bags/${encodeURIComponent(bag.parent_spawn_bag_ref)}`}>{bag.parent_spawn_bag_ref}</a>
                      ) : (
                        "-"
                      )}
                    </td>
                    <td>
                      {bag.source_sterilization_run_id ? (
                        <a href={`/sterilization-runs/${bag.source_sterilization_run_id}`}>
                          {bag.source_sterilization_run_code ?? bag.source_sterilization_run_id}
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
      )}
    </div>
  );
}
