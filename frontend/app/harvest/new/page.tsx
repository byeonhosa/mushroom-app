"use client";

import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "../../../lib/api";
import type { Batch, Harvest } from "../../../lib/types";

type FlushNumber = 1 | 2;

function toNullableText(raw: string): string | null {
  return raw.trim() ? raw.trim() : null;
}

export default function NewHarvestPage() {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [substrateBatchId, setSubstrateBatchId] = useState<string>("");
  const [flushNumber, setFlushNumber] = useState<FlushNumber>(1);
  const [harvestedKg, setHarvestedKg] = useState<string>("");
  const [notes, setNotes] = useState<string>("");
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    apiGet<Batch[]>("/batches")
      .then((data) => {
        setBatches(data);
        if (data.length > 0) {
          setSubstrateBatchId(String(data[0].substrate_batch_id));
        }
      })
      .catch((e) => setError(e?.message || String(e)));
  }, []);

  const canSubmit = useMemo(() => {
    const kg = Number(harvestedKg);
    return !!substrateBatchId && Number.isFinite(kg) && kg > 0 && !submitting;
  }, [substrateBatchId, harvestedKg, submitting]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSuccess(null);
    setError(null);

    const kg = Number(harvestedKg);
    if (!Number.isFinite(kg) || kg <= 0) {
      setError("Weight must be a positive number.");
      return;
    }

    setSubmitting(true);
    try {
      await apiPost<Harvest>("/harvests", {
        substrate_batch_id: Number(substrateBatchId),
        flush_number: flushNumber,
        harvested_kg: kg,
        harvested_at: new Date().toISOString(),
        notes: toNullableText(notes),
      });
      setSuccess("Harvest saved.");
      setHarvestedKg("");
      setNotes("");
      setFlushNumber(1);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="card" style={{ maxWidth: 560 }}>
      <h1>New Harvest</h1>

      {success && (
        <p style={{ background: "#e9f8ed", border: "1px solid #9fd3ab", padding: 10, borderRadius: 8 }}>
          {success}
        </p>
      )}
      {error && <p className="error">{error}</p>}

      <form className="form" onSubmit={onSubmit}>
        <label>
          Batch
          <select
            value={substrateBatchId}
            onChange={(e) => setSubstrateBatchId(e.target.value)}
            required
            style={{ minHeight: 44 }}
          >
            <option value="">Select batch...</option>
            {batches.map((batch) => (
              <option key={batch.substrate_batch_id} value={batch.substrate_batch_id}>
                #{batch.substrate_batch_id} - {batch.name}
              </option>
            ))}
          </select>
        </label>

        <label>
          Flush
          <select
            value={flushNumber}
            onChange={(e) => setFlushNumber(Number(e.target.value) as FlushNumber)}
            style={{ minHeight: 44 }}
          >
            <option value={1}>1</option>
            <option value={2}>2</option>
          </select>
        </label>

        <label>
          Weight (kg)
          <input
            type="number"
            min="0"
            step="0.001"
            inputMode="decimal"
            value={harvestedKg}
            onChange={(e) => setHarvestedKg(e.target.value)}
            placeholder="e.g., 2.450"
            required
            style={{ minHeight: 44, fontSize: 18 }}
          />
        </label>

        <label>
          Notes (optional)
          <input
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="optional"
            style={{ minHeight: 44 }}
          />
        </label>

        <button className="btn" type="submit" disabled={!canSubmit} style={{ minHeight: 48, fontSize: 18 }}>
          {submitting ? "Saving..." : "Save Harvest"}
        </button>
      </form>
    </div>
  );
}
