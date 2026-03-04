"use client";

import { useState } from "react";
import { apiPost } from "../../../lib/api";
import type { Bag } from "../../../lib/types";

export default function FruitingStartPage() {
  const [bagId, setBagId] = useState("");
  const [result, setResult] = useState<Bag | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    const id = bagId.trim();
    if (!id) {
      setError("Enter bag ID.");
      return;
    }
    try {
      const bag = await apiPost<Bag>(`/bags/${encodeURIComponent(id)}/fruiting-start`, {});
      setResult(bag);
      setBagId("");
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  return (
    <div className="card">
      <h1>Fruiting Start</h1>
      <p>Scan or enter bag ID when moving bag to grow tent.</p>
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
        <button className="btn" type="submit">Record Fruiting Start</button>
      </form>
      {result && <p className="success">Recorded: {result.bag_id} — Status: {result.status}</p>}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
