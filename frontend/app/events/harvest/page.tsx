"use client";

import { useState } from "react";
import { apiPost } from "../../../lib/api";

export default function HarvestPage() {
  const [bagId, setBagId] = useState("");
  const [flush, setFlush] = useState<1 | 2>(1);
  const [kg, setKg] = useState("0.250");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    const id = bagId.trim();
    if (!id) {
      setError("Enter bag ID.");
      return;
    }
    const weight = parseFloat(kg);
    if (!Number.isFinite(weight) || weight <= 0) {
      setError("Enter a valid weight (kg).");
      return;
    }
    try {
      await apiPost("/harvest-events", {
        bag_id: id,
        flush_number: flush,
        fresh_weight_kg: weight,
      });
      setSuccess(`Recorded flush ${flush}: ${weight} kg for ${id}`);
      setBagId("");
      setKg("0.250");
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  return (
    <div className="card">
      <h1>Harvest</h1>
      <p>Scan or enter bag ID and record harvest weight for flush 1 or 2.</p>
      <form onSubmit={submit} className="form">
        <label>
          Bag ID
          <input
            value={bagId}
            onChange={(e) => setBagId(e.target.value)}
            placeholder="e.g. PAST-20260301-001-MM-LM-0001"
            autoFocus
          />
        </label>
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
            onChange={(e) => setKg(e.target.value)}
          />
        </label>
        <button className="btn" type="submit">Record Harvest</button>
      </form>
      {success && <p className="success">{success}</p>}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
