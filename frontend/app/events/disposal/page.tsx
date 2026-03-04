"use client";

import { useState } from "react";
import { apiPost } from "../../../lib/api";
import type { Bag } from "../../../lib/types";

export default function DisposalPage() {
  const [bagId, setBagId] = useState("");
  const [reason, setReason] = useState<"CONTAMINATION" | "FINAL_HARVEST">("FINAL_HARVEST");
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
      const bag = await apiPost<Bag>(`/bags/${encodeURIComponent(id)}/disposal`, {
        disposal_reason: reason,
      });
      setResult(bag);
      setBagId("");
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  return (
    <div className="card">
      <h1>Disposal</h1>
      <p>Scan or enter bag ID when removing bag from production.</p>
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
          Reason
          <select value={reason} onChange={(e) => setReason(e.target.value as "CONTAMINATION" | "FINAL_HARVEST")}>
            <option value="FINAL_HARVEST">Final harvest</option>
            <option value="CONTAMINATION">Contamination</option>
          </select>
        </label>
        <button className="btn" type="submit">Record Disposal</button>
      </form>
      {result && <p className="success">Recorded: {result.bag_id} — {result.disposal_reason}</p>}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
