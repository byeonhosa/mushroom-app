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
      <h1>Bag {decodedBagId}</h1>

      {error && <p className="error">{error}</p>}

      {!bag ? (
        <p>Loading…</p>
      ) : (
        <>
          <p>Status: {bag.status}</p>

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
            <a className="btn" href={`/bags/${encodeURIComponent(decodedBagId)}/harvest`}>
              Log harvest
            </a>
          </p>
        </>
      )}
    </div>
  );
}

