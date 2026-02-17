"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../../../lib/api";
import type { Block, HarvestEvent } from "../../../lib/types";

export default function NewHarvestPage() {
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [blockId, setBlockId] = useState("");
  const [flushNumber, setFlushNumber] = useState<1 | 2>(1);
  const [freshWeightKg, setFreshWeightKg] = useState("");
  const [notes, setNotes] = useState("");
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<Block[]>("/blocks?block_type=SUBSTRATE&limit=500")
      .then((data) => {
        setBlocks(data);
        if (data.length > 0) setBlockId(String(data[0].block_id));
      })
      .catch((e) => setError(e?.message || String(e)));
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    try {
      await apiPost<HarvestEvent>("/harvest-events", {
        block_id: Number(blockId),
        flush_number: flushNumber,
        fresh_weight_kg: Number(freshWeightKg),
        harvested_at: new Date().toISOString(),
        notes: notes.trim() || null,
      });
      setFreshWeightKg("");
      setNotes("");
      setFlushNumber(1);
      setSuccess("Harvest recorded.");
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  return (
    <div className="card" style={{ maxWidth: 560 }}>
      <h1>New Harvest</h1>
      {success && <p style={{ background: "#e9f8ed", border: "1px solid #9fd3ab", padding: 10, borderRadius: 8 }}>{success}</p>}
      {error && <p className="error">{error}</p>}

      <form className="form" onSubmit={onSubmit}>
        <label>
          Substrate Block
          <select value={blockId} onChange={(e) => setBlockId(e.target.value)} required>
            <option value="">Select block...</option>
            {blocks.map((b) => (
              <option key={b.block_id} value={b.block_id}>
                {b.block_code}
              </option>
            ))}
          </select>
        </label>
        <label>
          Flush
          <select value={flushNumber} onChange={(e) => setFlushNumber(Number(e.target.value) as 1 | 2)}>
            <option value={1}>1</option>
            <option value={2}>2</option>
          </select>
        </label>
        <label>
          Fresh Weight (kg)
          <input
            type="number"
            min="0.001"
            step="0.001"
            inputMode="decimal"
            value={freshWeightKg}
            onChange={(e) => setFreshWeightKg(e.target.value)}
            required
          />
        </label>
        <label>
          Notes
          <input value={notes} onChange={(e) => setNotes(e.target.value)} />
        </label>
        <button className="btn" type="submit">Save Harvest</button>
      </form>
    </div>
  );
}
