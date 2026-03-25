"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../../lib/api";
import type { SterilizationRun, SpawnRecipe, GrainType } from "../../lib/types";

function toIsoOrNull(value: string): string | null {
  if (!value) return null;
  return new Date(value).toISOString();
}

function toNullableNumber(raw: string): number | null {
  if (!raw.trim()) return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

function toNullableInt(raw: string): number | null {
  if (!raw.trim()) return null;
  const n = Number(raw);
  if (!Number.isFinite(n)) return null;
  return Math.trunc(n);
}

export default function SterilizationRunsPage() {
  const [runs, setRuns] = useState<SterilizationRun[]>([]);
  const [spawnRecipes, setSpawnRecipes] = useState<SpawnRecipe[]>([]);
  const [grainTypes, setGrainTypes] = useState<GrainType[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [filterRunCodeContains, setFilterRunCodeContains] = useState("");
  const [sortBy, setSortBy] = useState<"sterilization_run_id" | "run_code" | "unloaded_at">("sterilization_run_id");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  const [createRunCode, setCreateRunCode] = useState("");
  const [createSpawnRecipeId, setCreateSpawnRecipeId] = useState<number | "">("");
  const [createGrainTypeId, setCreateGrainTypeId] = useState<number | "">("");
  const [createBagCount, setCreateBagCount] = useState(1);
  const [createCycleStart, setCreateCycleStart] = useState("");
  const [createCycleEnd, setCreateCycleEnd] = useState("");
  const [createUnloadedAt, setCreateUnloadedAt] = useState("");
  const [createTempC, setCreateTempC] = useState("");
  const [createPsi, setCreatePsi] = useState("");
  const [createHoldMinutes, setCreateHoldMinutes] = useState("");
  const [createNotes, setCreateNotes] = useState("");

  async function loadRuns() {
    const params = new URLSearchParams();
    if (filterRunCodeContains.trim()) params.set("run_code_contains", filterRunCodeContains.trim());
    params.set("sort_by", sortBy);
    params.set("sort_order", sortOrder);
    const [r, spr, gt] = await Promise.all([
      apiGet<SterilizationRun[]>(`/sterilization-runs?${params.toString()}`),
      apiGet<SpawnRecipe[]>("/spawn-recipes"),
      apiGet<GrainType[]>("/grain-types"),
    ]);
    setRuns(r);
    setSpawnRecipes(spr);
    setGrainTypes(gt);
    if (spr.length > 0 && !createSpawnRecipeId) setCreateSpawnRecipeId(spr[0].spawn_recipe_id);
    if (gt.length > 0 && !createGrainTypeId) setCreateGrainTypeId(gt[0].grain_type_id);
  }

  useEffect(() => {
    loadRuns().catch((e) => setError(String(e)));
  }, [filterRunCodeContains, sortBy, sortOrder]);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (createSpawnRecipeId === "" || createGrainTypeId === "") {
      setError("Select spawn recipe and grain type.");
      return;
    }
    try {
      await apiPost<SterilizationRun>("/sterilization-runs", {
        run_code: createRunCode.trim(),
        spawn_recipe_id: createSpawnRecipeId,
        grain_type_id: createGrainTypeId,
        bag_count: createBagCount,
        cycle_start_at: toIsoOrNull(createCycleStart),
        cycle_end_at: toIsoOrNull(createCycleEnd),
        unloaded_at: new Date(createUnloadedAt).toISOString(),
        temp_c: toNullableNumber(createTempC),
        psi: toNullableNumber(createPsi),
        hold_minutes: toNullableInt(createHoldMinutes),
        notes: createNotes.trim() || null,
      });
      setCreateRunCode("");
      setCreateSpawnRecipeId(spawnRecipes[0]?.spawn_recipe_id ?? "");
      setCreateGrainTypeId(grainTypes[0]?.grain_type_id ?? "");
      setCreateBagCount(1);
      setCreateCycleStart("");
      setCreateCycleEnd("");
      setCreateUnloadedAt("");
      setCreateTempC("");
      setCreatePsi("");
      setCreateHoldMinutes("");
      setCreateNotes("");
      await loadRuns();
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  return (
    <div>
      <div className="card">
        <h1>Sterilization Runs (Autoclave)</h1>
        <h2>Filter + Sort</h2>
        <div className="form">
          <label>
            Run code contains
            <input value={filterRunCodeContains} onChange={(e) => setFilterRunCodeContains(e.target.value)} />
          </label>
          <label>
            Sort by
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value as "sterilization_run_id" | "run_code" | "unloaded_at")}>
              <option value="sterilization_run_id">ID</option>
              <option value="run_code">Run Code</option>
              <option value="unloaded_at">Unloaded At</option>
            </select>
          </label>
          <label>
            Sort order
            <select value={sortOrder} onChange={(e) => setSortOrder(e.target.value as "asc" | "desc")}>
              <option value="desc">desc</option>
              <option value="asc">asc</option>
            </select>
          </label>
        </div>

        <form onSubmit={onCreate} className="form">
          <label>
            Run Code
            <input
              value={createRunCode}
              onChange={(e) => setCreateRunCode(e.target.value)}
              placeholder="e.g., AUTO-2026-02-15-A"
              required
            />
          </label>
          <label>
            Spawn Recipe
            <select value={createSpawnRecipeId} onChange={(e) => setCreateSpawnRecipeId(Number(e.target.value) || "")} required>
              <option value="">Select</option>
              {spawnRecipes.map((r) => (
                <option key={r.spawn_recipe_id} value={r.spawn_recipe_id}>{r.recipe_code}</option>
              ))}
            </select>
          </label>
          <label>
            Grain Type
            <select value={createGrainTypeId} onChange={(e) => setCreateGrainTypeId(Number(e.target.value) || "")} required>
              <option value="">Select</option>
              {grainTypes.map((g) => (
                <option key={g.grain_type_id} value={g.grain_type_id}>{g.name}</option>
              ))}
            </select>
          </label>
          <label>
            Bag Count
            <input type="number" min={1} value={createBagCount} onChange={(e) => setCreateBagCount(Number(e.target.value) || 1)} required />
          </label>
          <label>
            Cycle Start (optional)
            <input type="datetime-local" value={createCycleStart} onChange={(e) => setCreateCycleStart(e.target.value)} />
          </label>
          <label>
            Cycle End (optional)
            <input type="datetime-local" value={createCycleEnd} onChange={(e) => setCreateCycleEnd(e.target.value)} />
          </label>
          <label>
            Unloaded At
            <input type="datetime-local" value={createUnloadedAt} onChange={(e) => setCreateUnloadedAt(e.target.value)} required />
          </label>
          <label>
            Temp C (optional)
            <input type="number" step="0.01" value={createTempC} onChange={(e) => setCreateTempC(e.target.value)} />
          </label>
          <label>
            PSI (optional)
            <input type="number" step="0.01" value={createPsi} onChange={(e) => setCreatePsi(e.target.value)} />
          </label>
          <label>
            Hold Minutes (optional)
            <input type="number" step="1" min="0" value={createHoldMinutes} onChange={(e) => setCreateHoldMinutes(e.target.value)} />
          </label>
          <label>
            Notes
            <input value={createNotes} onChange={(e) => setCreateNotes(e.target.value)} />
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
            {runs.map((run) => (
              <tr key={run.sterilization_run_id}>
                <td>{run.sterilization_run_id}</td>
                <td>
                  <a href={`/sterilization-runs/${run.sterilization_run_id}`}>{run.run_code}</a>
                </td>
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
