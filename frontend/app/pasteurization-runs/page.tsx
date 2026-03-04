"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../../lib/api";
import type { PasteurizationRun, MixLot, SubstrateRecipeVersion } from "../../lib/types";

function toIsoOrNull(value: string): string | null {
  if (!value) return null;
  return new Date(value).toISOString();
}

export default function PasteurizationRunsPage() {
  const [runs, setRuns] = useState<PasteurizationRun[]>([]);
  const [mixLots, setMixLots] = useState<MixLot[]>([]);
  const [recipes, setRecipes] = useState<SubstrateRecipeVersion[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [createRunCode, setCreateRunCode] = useState("");
  const [createMixLotId, setCreateMixLotId] = useState<number | "">("");
  const [createRecipeId, setCreateRecipeId] = useState<number | "">("");
  const [createBagCount, setCreateBagCount] = useState(1);
  const [createSteamStart, setCreateSteamStart] = useState("");
  const [createSteamEnd, setCreateSteamEnd] = useState("");
  const [createUnloadedAt, setCreateUnloadedAt] = useState("");
  const [createNotes, setCreateNotes] = useState("");

  async function loadRuns() {
    const [r, m, rec] = await Promise.all([
      apiGet<PasteurizationRun[]>("/pasteurization-runs"),
      apiGet<MixLot[]>("/mix-lots"),
      apiGet<SubstrateRecipeVersion[]>("/substrate-recipe-versions"),
    ]);
    setRuns(r);
    setMixLots(m);
    setRecipes(rec);
    if (m.length > 0 && !createMixLotId) setCreateMixLotId(m[0].mix_lot_id);
    if (rec.length > 0 && !createRecipeId) setCreateRecipeId(rec[0].substrate_recipe_version_id);
  }

  useEffect(() => {
    loadRuns().catch(e => setError(String(e)));
  }, []);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (createMixLotId === "" || createRecipeId === "") {
      setError("Select mix lot and substrate recipe.");
      return;
    }
    try {
      await apiPost<PasteurizationRun>("/pasteurization-runs", {
        run_code: createRunCode,
        mix_lot_id: createMixLotId,
        substrate_recipe_version_id: createRecipeId,
        steam_start_at: toIsoOrNull(createSteamStart),
        steam_end_at: toIsoOrNull(createSteamEnd),
        unloaded_at: new Date(createUnloadedAt).toISOString(),
        bag_count: createBagCount,
        notes: createNotes || null
      });
      setCreateRunCode("");
      setCreateMixLotId(mixLots[0]?.mix_lot_id ?? "");
      setCreateRecipeId(recipes[0]?.substrate_recipe_version_id ?? "");
      setCreateBagCount(1);
      setCreateSteamStart("");
      setCreateSteamEnd("");
      setCreateUnloadedAt("");
      setCreateNotes("");
      await loadRuns();
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  return (
    <div>
      <div className="card">
        <h1>Pasteurization Runs (Steam)</h1>
        <form onSubmit={onCreate} className="form">
          <label>
            Run Code
            <input value={createRunCode} onChange={e => setCreateRunCode(e.target.value)} placeholder="e.g., PS-2026-02-15-A" required />
          </label>
          <label>
            Mix Lot
            <select value={createMixLotId} onChange={e => setCreateMixLotId(Number(e.target.value) || "")} required>
              <option value="">Select</option>
              {mixLots.map(m => (
                <option key={m.mix_lot_id} value={m.mix_lot_id}>{m.lot_code}</option>
              ))}
            </select>
          </label>
          <label>
            Substrate Recipe
            <select value={createRecipeId} onChange={e => setCreateRecipeId(Number(e.target.value) || "")} required>
              <option value="">Select</option>
              {recipes.map(r => (
                <option key={r.substrate_recipe_version_id} value={r.substrate_recipe_version_id}>{r.name} ({r.recipe_code})</option>
              ))}
            </select>
          </label>
          <label>
            Bag Count
            <input type="number" min={1} value={createBagCount} onChange={e => setCreateBagCount(Number(e.target.value) || 1)} required />
          </label>
          <label>
            Steam Start (optional)
            <input type="datetime-local" value={createSteamStart} onChange={e => setCreateSteamStart(e.target.value)} />
          </label>
          <label>
            Steam End (optional)
            <input type="datetime-local" value={createSteamEnd} onChange={e => setCreateSteamEnd(e.target.value)} />
          </label>
          <label>
            Unloaded At
            <input type="datetime-local" value={createUnloadedAt} onChange={e => setCreateUnloadedAt(e.target.value)} required />
          </label>
          <label>
            Notes
            <input value={createNotes} onChange={e => setCreateNotes(e.target.value)} />
          </label>
          <button className="btn" type="submit">Create Run</button>
        </form>
      </div>

      <div className="card">
        <h2>All Runs</h2>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Run Code</th>
              <th>Unloaded At</th>
            </tr>
          </thead>
          <tbody>
            {runs.map(run => (
              <tr key={run.pasteurization_run_id}>
                <td>{run.pasteurization_run_id}</td>
                <td>{run.run_code}</td>
                <td>{new Date(run.unloaded_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {error && <p className="error">{error}</p>}
    </div>
  );
}
