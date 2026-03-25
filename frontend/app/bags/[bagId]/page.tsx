"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiGet } from "../../../lib/api";
import type { BagDetail } from "../../../lib/types";

export default function BagPage() {
  const params = useParams();
  const bagIdRaw = params?.bagId;

  const bagId =
    typeof bagIdRaw === "string"
      ? bagIdRaw
      : Array.isArray(bagIdRaw)
      ? bagIdRaw[0]
      : undefined;

  const decodedBagId = bagId ? decodeURIComponent(bagId) : undefined;

  const [bag, setBag] = useState<BagDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!decodedBagId) return;

    (async () => {
      try {
        setError(null);
        const res = await apiGet<BagDetail>(`/bags/${encodeURIComponent(decodedBagId)}`);
        setBag(res);
      } catch (e: any) {
        setError(e?.message || String(e));
      }
    })();
  }, [decodedBagId]);

  if (!decodedBagId) {
    return (
      <div className="card">
        <h1>Bag</h1>
        <p className="error">Missing bagId in route params.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h1>Bag {bag?.bag_ref ?? decodedBagId}</h1>

      {error && <p className="error">{error}</p>}

      {!bag ? (
        <p>Loading…</p>
      ) : (
        <>
          <p>Printable Code: {bag.bag_code ?? "-"}</p>
          <p>Internal Record ID: {bag.bag_id}</p>
          <p>Status: {bag.status}</p>
          <p>Type: {bag.bag_type}</p>
          <p>
            Sterilization Run:{" "}
            {bag.sterilization_run_id ? (
              <a href={`/sterilization-runs/${bag.sterilization_run_id}`}>{bag.sterilization_run_id}</a>
            ) : (
              "-"
            )}
          </p>
          <p>
            Pasteurization Run:{" "}
            {bag.pasteurization_run_id ? (
              <a href={`/pasteurization-runs/${bag.pasteurization_run_id}`}>{bag.pasteurization_run_id}</a>
            ) : (
              "-"
            )}
          </p>
          <p>Dry Weight Source: {bag.dry_weight_source ?? "-"}</p>
          <p>Target Dry Weight: {bag.target_dry_kg != null ? `${bag.target_dry_kg.toFixed(3)} kg` : "-"}</p>
          <p>Actual Dry Weight: {bag.actual_dry_kg != null ? `${bag.actual_dry_kg.toFixed(3)} kg` : "-"}</p>
          <p>Biological Efficiency: {bag.bio_efficiency != null ? `${(bag.bio_efficiency * 100).toFixed(1)}%` : "-"}</p>
          <p>Labeled: {bag.labeled_at ? new Date(bag.labeled_at).toLocaleString() : "-"}</p>
          <p>Inoculated: {bag.inoculated_at ? new Date(bag.inoculated_at).toLocaleString() : "-"}</p>
          <p>Incubation Start: {bag.incubation_start_at ? new Date(bag.incubation_start_at).toLocaleString() : "-"}</p>
          <p>Ready: {bag.ready_at ? new Date(bag.ready_at).toLocaleString() : "-"}</p>
          <p>Fruiting Start: {bag.fruiting_start_at ? new Date(bag.fruiting_start_at).toLocaleString() : "-"}</p>
          <p>
            Inoculation Source:{" "}
            {bag.inoculation_source_type === "LIQUID_CULTURE" ? (
              bag.source_liquid_culture_id ? (
                <a href="/liquid-cultures">{bag.source_liquid_culture_code ?? `LC-${bag.source_liquid_culture_id}`}</a>
              ) : (
                bag.source_liquid_culture_code ?? "Liquid culture"
              )
            ) : bag.inoculation_source_type === "SPAWN_BAG" ? (
              bag.source_spawn_bag_ref ? (
                <a href={`/bags/${encodeURIComponent(bag.source_spawn_bag_ref)}`}>{bag.source_spawn_bag_ref}</a>
              ) : (
                bag.source_spawn_bag_id ?? "-"
              )
            ) : (
              "-"
            )}
          </p>
          <p>Disposal: {bag.disposed_at ? `${bag.disposal_reason ?? "Disposed"} at ${new Date(bag.disposed_at).toLocaleString()}` : "-"}</p>
          <p>
            Total Harvest:{" "}
            {bag.harvest_events.reduce((sum, event) => sum + event.fresh_weight_kg, 0).toFixed(3)} kg
          </p>

          {bag.child_bags.length > 0 && (
            <>
              <h2>Downstream Bags</h2>
              {bag.child_summary && (
                <>
                  <p>Total downstream bags: {bag.child_summary.total_bags}</p>
                  <p>Contaminated downstream bags: {bag.child_summary.contaminated_bags}</p>
                  <p>Total downstream harvest: {bag.child_summary.total_harvest_kg.toFixed(3)} kg</p>
                  <p>
                    Downstream BE:{" "}
                    {bag.child_summary.overall_bio_efficiency != null
                      ? `${(bag.child_summary.overall_bio_efficiency * 100).toFixed(1)}%`
                      : "-"}
                  </p>
                </>
              )}
              <table className="table">
                <thead>
                  <tr>
                    <th>Depth</th>
                    <th>Bag</th>
                    <th>Type</th>
                    <th>Source</th>
                    <th>Run</th>
                    <th>Status</th>
                    <th>Harvest</th>
                    <th>BE</th>
                  </tr>
                </thead>
                <tbody>
                  {bag.child_bags.map((child) => (
                    <tr key={child.bag_id}>
                      <td>{child.generation}</td>
                      <td>
                        <a href={`/bags/${encodeURIComponent(child.bag_ref)}`}>{child.bag_ref}</a>
                      </td>
                      <td>
                        {child.bag_type}
                      </td>
                      <td>
                        {child.inoculation_source_type === "LIQUID_CULTURE" ? (
                          child.source_liquid_culture_id ? (
                            <a href="/liquid-cultures">{child.source_liquid_culture_code ?? `LC-${child.source_liquid_culture_id}`}</a>
                          ) : (
                            child.source_liquid_culture_code ?? "Liquid culture"
                          )
                        ) : child.parent_spawn_bag_ref ? (
                          <a href={`/bags/${encodeURIComponent(child.parent_spawn_bag_ref)}`}>{child.parent_spawn_bag_ref}</a>
                        ) : (
                          "-"
                        )}
                      </td>
                      <td>
                        {child.bag_type === "SPAWN" ? (
                          child.sterilization_run_id ? (
                            <a href={`/sterilization-runs/${child.sterilization_run_id}`}>{child.sterilization_run_code ?? child.sterilization_run_id}</a>
                          ) : (
                            "-"
                          )
                        ) : child.pasteurization_run_id ? (
                          <a href={`/pasteurization-runs/${child.pasteurization_run_id}`}>{child.pasteurization_run_code ?? child.pasteurization_run_id}</a>
                        ) : (
                          "-"
                        )}
                      </td>
                      <td>{child.contaminated ? "CONTAMINATED" : child.status}</td>
                      <td>{child.bag_type === "SUBSTRATE" ? `${child.total_harvest_kg.toFixed(3)} kg` : "-"}</td>
                      <td>{child.bio_efficiency != null ? `${(child.bio_efficiency * 100).toFixed(1)}%` : "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          <h2>Harvest Events</h2>
          {bag.harvest_events.length === 0 ? (
            <p>No harvests logged.</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Flush</th>
                  <th>kg</th>
                </tr>
              </thead>
              <tbody>
                {bag.harvest_events.map((h) => (
                  <tr key={h.harvest_event_id}>
                    <td>{new Date(h.harvested_at).toLocaleString()}</td>
                    <td>{h.flush_number}</td>
                    <td>{h.fresh_weight_kg.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <p>
            <a className="btn" href={`/bags/${encodeURIComponent(bag.bag_ref)}/harvest`}>
              Log harvest
            </a>
          </p>
        </>
      )}
    </div>
  );
}

