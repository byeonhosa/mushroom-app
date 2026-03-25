"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiGet, apiPost } from "../../../lib/api";
import type { PasteurizationRun, Bag } from "../../../lib/types";

export default function InoculationPage() {
  const router = useRouter();
  const [runs, setRuns] = useState<PasteurizationRun[]>([]);
  const [runId, setRunId] = useState<number | "">("");
  const [bagCount, setBagCount] = useState(1);
  const [spawnBagRef, setSpawnBagRef] = useState("");
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

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const spawnRef = spawnBagRef.trim();
    if (runId === "" || !spawnRef) {
      setError("Select a pasteurization run and enter one ready spawn bag code.");
      return;
    }

    try {
      const bags = await apiPost<Bag[]>("/inoculations/batch", {
        pasteurization_run_id: runId,
        bag_count: bagCount,
        spawn_bag_id: spawnRef,
      });
      router.push(
        `/bags/create/substrate/labels?ids=${bags.map((bag) => encodeURIComponent(bag.bag_ref)).join(",")}`,
      );
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  return (
    <div className="card">
      <h1>Substrate Inoculation</h1>
      <p>
        Select the pasteurization run, enter how many unlabeled substrate bag records you are inoculating now, and
        scan the ready spawn bag that supplied the grain. Printable bag codes are assigned as part of this batch.
      </p>
      <form onSubmit={submit} className="form">
        <label>
          Ready spawn bag code
          <input
            value={spawnBagRef}
            onChange={(e) => setSpawnBagRef(e.target.value)}
            placeholder="e.g. STER-20260324-SR1-LM-0001"
            autoFocus
          />
        </label>
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
          <input type="number" min={1} max={999} value={bagCount} onChange={(e) => setBagCount(Number(e.target.value) || 1)} />
        </label>
        <button className="btn" type="submit">Assign Codes &amp; Print Labels</button>
      </form>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
