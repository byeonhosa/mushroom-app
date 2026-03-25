"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../../../../lib/api";
import type { PasteurizationRun, Bag } from "../../../../lib/types";

export default function CreateSubstrateBagsPage() {
  const [runs, setRuns] = useState<PasteurizationRun[]>([]);
  const [runId, setRunId] = useState<number | "">("");
  const [count, setCount] = useState(1);
  const [actualDryKg, setActualDryKg] = useState("");
  const [createdBags, setCreatedBags] = useState<Bag[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const runRows = await apiGet<PasteurizationRun[]>("/pasteurization-runs");
      setRuns(runRows);
      if (runRows.length > 0) {
        setRunId((current) => current || runRows[0].pasteurization_run_id);
      }
    })().catch((e) => setError(String(e)));
  }, []);

  const selectedRun = runs.find((run) => run.pasteurization_run_id === runId);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setCreatedBags([]);
    if (runId === "") {
      setError("Select a pasteurization run.");
      return;
    }
    try {
      const parsedActualDryKg = actualDryKg.trim() ? Number(actualDryKg) : undefined;
      if (parsedActualDryKg !== undefined && (!Number.isFinite(parsedActualDryKg) || parsedActualDryKg <= 0)) {
        setError("Actual dry kg per bag must be a positive number when provided.");
        return;
      }
      const bags = await apiPost<Bag[]>("/bags/substrate", {
        pasteurization_run_id: runId,
        bag_count: count,
        actual_dry_kg: parsedActualDryKg,
      });
      setCreatedBags(bags);
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  return (
    <div className="card">
      <h1>Create Substrate Bag Records</h1>
      <p className="workflow-note">
        <strong>When to use:</strong> After filling and pasteurizing substrate bags. This records unlabeled internal
        bag records for the pasteurization run. Printable bag codes are assigned later, after inoculation, when labels
        can safely be attached.
      </p>
      <form onSubmit={submit} className="form">
        <label>
          Pasteurization Run
          <select value={runId} onChange={(e) => setRunId(Number(e.target.value) || "")} required>
            <option value="">— Select —</option>
            {runs.map((run) => (
              <option key={run.pasteurization_run_id} value={run.pasteurization_run_id}>
                {run.run_code}
              </option>
            ))}
          </select>
        </label>
        <label>
          Bag count
          <input type="number" min={1} max={999} value={count} onChange={(e) => setCount(Number(e.target.value) || 1)} />
        </label>
        <label>
          Actual dry kg per bag (optional)
          <input
            type="number"
            step="0.001"
            min="0"
            value={actualDryKg}
            onChange={(e) => setActualDryKg(e.target.value)}
            placeholder="Uses fill profile target if left blank"
          />
        </label>
        <button className="btn" type="submit">Create Unlabeled Records</button>
      </form>
      {createdBags.length > 0 && (
        <div className="success" style={{ marginTop: 16 }}>
          <p>
            Recorded {createdBags.length} unlabeled substrate bag record{createdBags.length === 1 ? "" : "s"}
            {selectedRun ? ` for ${selectedRun.run_code}` : ""}.
          </p>
          <p>
            Dry-weight source:{" "}
            {createdBags[0]?.dry_weight_source === "ACTUAL"
              ? `actual ${createdBags[0].dry_weight_kg?.toFixed(3)} kg per bag`
              : `target ${createdBags[0]?.dry_weight_kg?.toFixed(3) ?? "-"} kg per bag`}
          </p>
          <p>Next step: inoculate the run from a ready spawn bag to assign printable bag codes and labels.</p>
          <p>
            <a className="btn" href="/events/inoculation">Go to Substrate Inoculation</a>
            <a className="btn" href="/bags" style={{ marginLeft: 8 }}>View Bags</a>
          </p>
        </div>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
