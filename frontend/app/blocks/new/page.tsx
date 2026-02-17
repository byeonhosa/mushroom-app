"use client";

import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "../../../lib/api";
import type { Batch, Block, MixLot, PasteurizationRun, SpawnBatch, SpawnRecipe, SterilizationRun } from "../../../lib/types";

type BlockType = "SPAWN" | "SUBSTRATE";

export default function NewBlockPage() {
  const [blockType, setBlockType] = useState<BlockType>("SUBSTRATE");
  const [mixLots, setMixLots] = useState<MixLot[]>([]);
  const [pasteurizationRuns, setPasteurizationRuns] = useState<PasteurizationRun[]>([]);
  const [sterilizationRuns, setSterilizationRuns] = useState<SterilizationRun[]>([]);
  const [spawnRecipes, setSpawnRecipes] = useState<SpawnRecipe[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [spawnBatches, setSpawnBatches] = useState<SpawnBatch[]>([]);

  const [mixLotId, setMixLotId] = useState("");
  const [pasteurizationRunId, setPasteurizationRunId] = useState("");
  const [sterilizationRunId, setSterilizationRunId] = useState("");
  const [spawnRecipeId, setSpawnRecipeId] = useState("");
  const [substrateBatchId, setSubstrateBatchId] = useState("");
  const [spawnBatchId, setSpawnBatchId] = useState("");
  const [notes, setNotes] = useState("");
  const [status, setStatus] = useState("");
  const [createdBlock, setCreatedBlock] = useState<Block | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      apiGet<MixLot[]>("/mix-lots"),
      apiGet<PasteurizationRun[]>("/pasteurization-runs"),
      apiGet<SterilizationRun[]>("/sterilization-runs"),
      apiGet<SpawnRecipe[]>("/spawn-recipes"),
      apiGet<Batch[]>("/batches"),
      apiGet<SpawnBatch[]>("/spawn-batches?limit=200"),
    ])
      .then(([mix, paste, ster, recipes, batchRows, spawnRows]) => {
        setMixLots(mix);
        setPasteurizationRuns(paste);
        setSterilizationRuns(ster);
        setSpawnRecipes(recipes);
        setBatches(batchRows);
        setSpawnBatches(spawnRows);
      })
      .catch((e) => setError(e?.message || String(e)));
  }, []);

  const isSubstrate = useMemo(() => blockType === "SUBSTRATE", [blockType]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setCreatedBlock(null);
    setError(null);
    try {
      const payload: any = {
        block_type: blockType,
        notes: notes.trim() || null,
        status: status.trim() || null,
      };
      if (isSubstrate) {
        payload.mix_lot_id = mixLotId ? Number(mixLotId) : null;
        payload.pasteurization_run_id = pasteurizationRunId ? Number(pasteurizationRunId) : null;
        payload.substrate_batch_id = substrateBatchId ? Number(substrateBatchId) : null;
      } else {
        payload.sterilization_run_id = sterilizationRunId ? Number(sterilizationRunId) : null;
        payload.spawn_recipe_id = spawnRecipeId ? Number(spawnRecipeId) : null;
        payload.spawn_batch_id = spawnBatchId ? Number(spawnBatchId) : null;
      }
      const created = await apiPost<Block>("/blocks", payload);
      setCreatedBlock(created);
      setNotes("");
      setStatus("");
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  return (
    <div className="card">
      <h1>New Block</h1>
      {createdBlock && (
        <p style={{ background: "#e9f8ed", border: "1px solid #9fd3ab", padding: 10, borderRadius: 8 }}>
          Created block: <strong>{createdBlock.block_code}</strong> (ID {createdBlock.block_id})
        </p>
      )}
      {error && <p className="error">{error}</p>}
      <form className="form" onSubmit={onSubmit}>
        <label>
          Block Type
          <select value={blockType} onChange={(e) => setBlockType(e.target.value as BlockType)}>
            <option value="SUBSTRATE">SUBSTRATE</option>
            <option value="SPAWN">SPAWN</option>
          </select>
        </label>

        {isSubstrate ? (
          <>
            <label>
              Mix Lot
              <select value={mixLotId} onChange={(e) => setMixLotId(e.target.value)}>
                <option value="">(optional)</option>
                {mixLots.map((m) => <option key={m.mix_lot_id} value={m.mix_lot_id}>{m.lot_code}</option>)}
              </select>
            </label>
            <label>
              Pasteurization Run
              <select value={pasteurizationRunId} onChange={(e) => setPasteurizationRunId(e.target.value)}>
                <option value="">(optional)</option>
                {pasteurizationRuns.map((r) => <option key={r.pasteurization_run_id} value={r.pasteurization_run_id}>{r.run_code}</option>)}
              </select>
            </label>
            <label>
              Linked Substrate Batch
              <select value={substrateBatchId} onChange={(e) => setSubstrateBatchId(e.target.value)}>
                <option value="">(optional)</option>
                {batches.map((b) => <option key={b.substrate_batch_id} value={b.substrate_batch_id}>#{b.substrate_batch_id} {b.name}</option>)}
              </select>
            </label>
          </>
        ) : (
          <>
            <label>
              Sterilization Run
              <select value={sterilizationRunId} onChange={(e) => setSterilizationRunId(e.target.value)}>
                <option value="">(optional)</option>
                {sterilizationRuns.map((r) => <option key={r.sterilization_run_id} value={r.sterilization_run_id}>{r.run_code}</option>)}
              </select>
            </label>
            <label>
              Spawn Recipe
              <select value={spawnRecipeId} onChange={(e) => setSpawnRecipeId(e.target.value)}>
                <option value="">(optional)</option>
                {spawnRecipes.map((r) => <option key={r.spawn_recipe_id} value={r.spawn_recipe_id}>{r.recipe_code}</option>)}
              </select>
            </label>
            <label>
              Linked Spawn Batch
              <select value={spawnBatchId} onChange={(e) => setSpawnBatchId(e.target.value)}>
                <option value="">(optional)</option>
                {spawnBatches.map((b) => <option key={b.spawn_batch_id} value={b.spawn_batch_id}>#{b.spawn_batch_id} {b.strain_code}</option>)}
              </select>
            </label>
          </>
        )}

        <label>
          Status
          <input value={status} onChange={(e) => setStatus(e.target.value)} />
        </label>
        <label>
          Notes
          <input value={notes} onChange={(e) => setNotes(e.target.value)} />
        </label>
        <button className="btn" type="submit">Create Block</button>
      </form>
    </div>
  );
}
