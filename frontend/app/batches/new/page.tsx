"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../../../lib/api";
import type { FillProfile, PasteurizationRun, SpawnBatch } from "../../../lib/types";

export default function NewBatch() {
  const [fillProfiles, setFillProfiles] = useState<FillProfile[]>([]);
  const [pasteurizationRuns, setPasteurizationRuns] = useState<PasteurizationRun[]>([]);
  const [spawnBatches, setSpawnBatches] = useState<SpawnBatch[]>([]);
  const [name, setName] = useState("");
  const [fillProfileId, setFillProfileId] = useState<number | null>(null);
  const [pasteurizationRunId, setPasteurizationRunId] = useState<number | null>(null);
  const [spawnBatchId, setSpawnBatchId] = useState<number | null>(null);
  const [spawnBlocksUsed, setSpawnBlocksUsed] = useState<number | null>(null);
  const [bagCount, setBagCount] = useState(10);
  const [recipeId, setRecipeId] = useState(1);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<FillProfile[]>("/fill-profiles")
      .then(fps => {
        setFillProfiles(fps);
        if (fps.length && fillProfileId === null) setFillProfileId(fps[0].fill_profile_id);
      })
      .catch(e => setError(String(e)));
  }, []);

  useEffect(() => {
    apiGet<PasteurizationRun[]>("/pasteurization-runs")
      .then(setPasteurizationRuns)
      .catch(e => setError(String(e)));
  }, []);

  useEffect(() => {
    apiGet<SpawnBatch[]>("/spawn-batches")
      .then(setSpawnBatches)
      .catch(e => setError(String(e)));
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!fillProfileId) {
      setError("Fill Profile is not selected yet. Please pick one.");
      return;
    }

    try {
      const created = await apiPost<any>("/batches", {
        name,
        substrate_recipe_version_id: recipeId,
        fill_profile_id: fillProfileId,
        bag_count: bagCount,
        pasteurization_run_id: pasteurizationRunId
      });

      const id = created?.substrate_batch_id;
      if (!id || typeof id !== "number") {
        // Show the response so we can see what came back
        setError(`Unexpected response from API: ${JSON.stringify(created)}`);
        return;
      }

      if (spawnBatchId) {
        await apiPost("/batch-inoculations", {
          substrate_batch_id: id,
          spawn_batch_id: spawnBatchId,
          spawn_blocks_used: spawnBlocksUsed
        });
      }

      window.location.href = `/batches/${id}`;
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  return (
    <div className="card">
      <h1>Create Substrate Batch</h1>
      <form onSubmit={onSubmit} className="form">
        <label>
          Batch Name
          <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g., LM-2026-02-13-A" required />
        </label>

        <label>
          Fill Profile
          <select value={fillProfileId ?? ""} onChange={e => setFillProfileId(Number(e.target.value))}>
            {fillProfiles.map(fp => (
              <option key={fp.fill_profile_id} value={fp.fill_profile_id}>
                {fp.name} ({fp.target_dry_kg_per_bag}kg dry + {fp.target_water_kg_per_bag}kg water)
              </option>
            ))}
          </select>
        </label>

        <label>
          Pasteurization Run (optional)
          <select
            value={pasteurizationRunId ?? ""}
            onChange={e => setPasteurizationRunId(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">None</option>
            {pasteurizationRuns.map(run => (
              <option key={run.pasteurization_run_id} value={run.pasteurization_run_id}>
                {run.run_code}
              </option>
            ))}
          </select>
        </label>

        <label>
          Spawn Batch (optional)
          <select
            value={spawnBatchId ?? ""}
            onChange={e => setSpawnBatchId(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">None</option>
            {spawnBatches.map(sb => (
              <option key={sb.spawn_batch_id} value={sb.spawn_batch_id}>
                #{sb.spawn_batch_id} {sb.strain_code} ({sb.spawn_type})
              </option>
            ))}
          </select>
        </label>

        <label>
          Spawn Blocks Used (optional)
          <input
            type="number"
            min={1}
            value={spawnBlocksUsed ?? ""}
            onChange={e => setSpawnBlocksUsed(e.target.value ? Number(e.target.value) : null)}
            disabled={!spawnBatchId}
          />
        </label>

        <label>
          Bag Count
          <input type="number" min={1} value={bagCount} onChange={e => setBagCount(Number(e.target.value))} />
        </label>

        <label>
          Substrate Recipe Version ID
          <input type="number" min={1} value={recipeId} onChange={e => setRecipeId(Number(e.target.value))} />
        </label>

        <button className="btn" type="submit">Create Batch</button>
        {error && <p className="error">{error}</p>}
      </form>
    </div>
  );
}
