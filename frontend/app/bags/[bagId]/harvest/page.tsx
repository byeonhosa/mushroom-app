"use client";

import { useState } from "react";
import { apiPost } from "../../../../lib/api";

export default function LogHarvest({ params }: { params: { bagId: string } }) {
  const bagId = decodeURIComponent(params.bagId);
  const [flush, setFlush] = useState<1|2>(1);
  const [kg, setKg] = useState<number>(0.250);
  const [error, setError] = useState<string|null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await apiPost("/harvest-events", { bag_id: bagId, flush_number: flush, fresh_weight_kg: kg });
      window.location.href = `/bags/${encodeURIComponent(bagId)}`;
    } catch (e:any) {
      setError(e?.message || String(e));
    }
  }

  return (
    <div className="card">
      <h1>Log Harvest</h1>
      <p>Bag: {bagId}</p>
      <form onSubmit={submit} className="form">
        <label>
          Flush
          <select value={flush} onChange={e => setFlush(Number(e.target.value) as 1|2)}>
            <option value={1}>1</option>
            <option value={2}>2</option>
          </select>
        </label>
        <label>
          Fresh weight (kg)
          <input type="number" step="0.001" min="0" value={kg} onChange={e => setKg(Number(e.target.value))} />
        </label>
        <button className="btn" type="submit">Save</button>
        {error && <p className="error">{error}</p>}
      </form>
    </div>
  );
}
