"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiGet, apiPost } from "../../../lib/api";
import { SubstrateSourceFields, useUsableSpawnLots, type SubstrateSource } from "../../../lib/spawn-lots";
import type { PasteurizationRun, Bag } from "../../../lib/types";

export default function InoculationPage() {
  const router = useRouter();
  const [runs, setRuns] = useState<PasteurizationRun[]>([]);
  const [runId, setRunId] = useState<number | "">("");
  const [bagCount, setBagCount] = useState(1);
  const [source, setSource] = useState<SubstrateSource>("PURCHASED_SPAWN");
  const [lotId, setLotId] = useState<number | "">("");
  const [spawnBagRef, setSpawnBagRef] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const { lots, loaded: lotsLoaded } = useUsableSpawnLots();
  // With no purchased lot open, the only possible source is one of our own spawn bags.
  useEffect(() => {
    if (lotsLoaded && lots.length === 0) setSource("SPAWN_BAG");
  }, [lotsLoaded, lots]);

  useEffect(() => {
    (async () => {
      const runRows = await apiGet<PasteurizationRun[]>("/pasteurization-runs");
      setRuns(runRows);
      if (runRows.length > 0) {
        setRunId((current) => current || runRows[0].pasteurization_run_id);
      }
    })().catch((failure) => setError(failure instanceof ApiError ? failure.message : String(failure)));
  }, []);

  // With one open lot there is nothing to choose.
  useEffect(() => {
    if (lots.length === 1) setLotId((current) => current || lots[0].purchased_spawn_lot_id);
  }, [lots]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    setError(null);

    if (runId === "") {
      setError("Select a pasteurization run.");
      return;
    }
    if (source === "PURCHASED_SPAWN" && lotId === "") {
      setError("Select the purchased spawn lot that supplied the grain.");
      return;
    }
    if (source === "SPAWN_BAG" && !spawnBagRef.trim()) {
      setError("Enter the ready spawn bag that supplied the grain.");
      return;
    }

    setBusy(true);
    try {
      const bags = await apiPost<Bag[]>("/inoculations/batch", {
        pasteurization_run_id: runId,
        bag_count: bagCount,
        ...(source === "PURCHASED_SPAWN"
          ? { purchased_spawn_lot_id: lotId }
          : { spawn_bag_id: spawnBagRef.trim() }),
      });
      router.push(
        `/bags/create/substrate/labels?ids=${bags.map((bag) => encodeURIComponent(bag.bag_ref)).join(",")}`,
      );
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : String(failure));
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h1>Substrate Inoculation</h1>
      <p>
        Choose where the grain came from, the pasteurization run, and how many of its unlabeled bags you are
        inoculating now. Bag codes are assigned as part of this step and the labels open for printing.
      </p>
      <form onSubmit={submit} className="form stackedForm">
        <SubstrateSourceFields
          source={source}
          onSourceChange={setSource}
          lots={lots}
          lotId={lotId}
          onLotChange={setLotId}
          spawnBagRef={spawnBagRef}
          onSpawnBagChange={setSpawnBagRef}
        />
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
        <button className="btn" type="submit" disabled={busy}>Assign Codes &amp; Print Labels</button>
      </form>
      {error && <p className="error" role="alert">{error}</p>}
    </div>
  );
}
