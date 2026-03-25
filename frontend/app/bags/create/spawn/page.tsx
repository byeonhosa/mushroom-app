"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../../../../lib/api";
import type { SterilizationRun, Bag } from "../../../../lib/types";

export default function CreateSpawnBagsPage() {
  const [runs, setRuns] = useState<SterilizationRun[]>([]);
  const [runId, setRunId] = useState<number | "">("");
  const [count, setCount] = useState(1);
  const [createdBags, setCreatedBags] = useState<Bag[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const runRows = await apiGet<SterilizationRun[]>("/sterilization-runs");
      setRuns(runRows);
      if (runRows.length > 0) {
        setRunId((current) => current || runRows[0].sterilization_run_id);
      }
    })().catch((e) => setError(String(e)));
  }, []);

  const selectedRun = runs.find((run) => run.sterilization_run_id === runId);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setCreatedBags([]);
    if (runId === "") {
      setError("Select a sterilization run.");
      return;
    }
    try {
      const bags = await apiPost<Bag[]>("/bags/spawn", {
        sterilization_run_id: runId,
        bag_count: count,
      });
      setCreatedBags(bags);
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  return (
    <div className="card">
      <h1>Create Spawn Bag Records</h1>
      <p className="workflow-note">
        <strong>When to use:</strong> After filling and sterilizing spawn bags. This step creates internal run-linked
        bag records before labels exist. Species and printable bag codes are assigned later during spawn inoculation.
      </p>
      <form onSubmit={submit} className="form">
        <label>
          Sterilization Run
          <select value={runId} onChange={(e) => setRunId(Number(e.target.value) || "")} required>
            <option value="">— Select —</option>
            {runs.map((run) => (
              <option key={run.sterilization_run_id} value={run.sterilization_run_id}>
                {run.run_code}
              </option>
            ))}
          </select>
        </label>
        <label>
          Bag count
          <input type="number" min={1} max={999} value={count} onChange={(e) => setCount(Number(e.target.value) || 1)} />
        </label>
        <button className="btn" type="submit">Create Unlabeled Records</button>
      </form>
      {createdBags.length > 0 && (
        <div className="success" style={{ marginTop: 16 }}>
          <p>
            Recorded {createdBags.length} unlabeled spawn bag record{createdBags.length === 1 ? "" : "s"}
            {selectedRun ? ` for ${selectedRun.run_code}` : ""}.
          </p>
          <p>Next step: inoculate the run to assign species, printable bag codes, and labels.</p>
          <p>
            <a className="btn" href="/events/spawn-inoculation">Go to Spawn Inoculation</a>
            <a className="btn" href="/bags" style={{ marginLeft: 8 }}>View Bags</a>
          </p>
        </div>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
