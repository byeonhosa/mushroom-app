"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiPost } from "../../../../lib/api";

export default function LogHarvest() {
  const params = useParams();
  const router = useRouter();

  const bagIdRaw = params?.bagId;

  const bagId =
    typeof bagIdRaw === "string"
      ? bagIdRaw
      : Array.isArray(bagIdRaw)
      ? bagIdRaw[0]
      : undefined;

  const decodedBagId = bagId ? decodeURIComponent(bagId) : undefined;

  const [flush, setFlush] = useState<1 | 2>(1);
  const [kg, setKg] = useState<number>(0.250);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!decodedBagId) {
      setError("Missing bagId in route params.");
      return;
    }

    try {
      await apiPost("/harvest-events", {
        bag_id: decodedBagId,
        flush_number: flush,
        fresh_weight_kg: kg,
      });
      router.push(`/bags/${encodeURIComponent(decodedBagId)}`);
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  if (!decodedBagId) {
    return (
      <div className="card">
        <h1>Log Harvest</h1>
        <p className="error">Missing bagId in route params.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h1>Log Harvest</h1>
      <p>Bag: {decodedBagId}</p>

      <form onSubmit={submit} className="form">
        <label>
          Flush
          <select value={flush} onChange={(e) => setFlush(Number(e.target.value) as 1 | 2)}>
            <option value={1}>1</option>
            <option value={2}>2</option>
          </select>
        </label>

        <label>
          Fresh weight (kg)
          <input
            type="number"
            step="0.001"
            min="0"
            value={kg}
            onChange={(e) => setKg(Number(e.target.value))}
          />
        </label>

        <button className="btn" type="submit">
          Save
        </button>

        {error && <p className="error">{error}</p>}
      </form>
    </div>
  );
}
