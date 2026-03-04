"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiGet, apiPost } from "../../../../lib/api";
import type { SterilizationRun, MushroomSpecies, Bag } from "../../../../lib/types";

export default function CreateSpawnBagsPage() {
  const router = useRouter();
  const [runs, setRuns] = useState<SterilizationRun[]>([]);
  const [species, setSpecies] = useState<MushroomSpecies[]>([]);
  const [runId, setRunId] = useState<number | "">("");
  const [speciesId, setSpeciesId] = useState<number | "">("");
  const [count, setCount] = useState(1);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const [r, s] = await Promise.all([
        apiGet<SterilizationRun[]>("/sterilization-runs"),
        apiGet<MushroomSpecies[]>("/species"),
      ]);
      setRuns(r);
      setSpecies(s);
      if (r.length > 0 && !runId) setRunId(r[0].sterilization_run_id);
      if (s.length > 0 && !speciesId) setSpeciesId(s[0].species_id);
    })().catch((e) => setError(String(e)));
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (runId === "" || speciesId === "") {
      setError("Select sterilization run and species.");
      return;
    }
    try {
      const bags = await apiPost<Bag[]>("/bags/spawn", {
        sterilization_run_id: runId,
        species_id: speciesId,
        bag_count: count,
      });
      router.push(`/bags/create/spawn/labels?ids=${bags.map((b) => encodeURIComponent(b.bag_id)).join(",")}`);
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  return (
    <div className="card">
      <h1>Create Spawn Bags</h1>
      <form onSubmit={submit} className="form">
        <label>
          Sterilization Run
          <select value={runId} onChange={(e) => setRunId(Number(e.target.value) || "")} required>
            <option value="">— Select —</option>
            {runs.map((r) => (
              <option key={r.sterilization_run_id} value={r.sterilization_run_id}>
                {r.run_code}
              </option>
            ))}
          </select>
        </label>
        <label>
          Species
          <select value={speciesId} onChange={(e) => setSpeciesId(Number(e.target.value) || "")} required>
            <option value="">— Select —</option>
            {species.map((s) => (
              <option key={s.species_id} value={s.species_id}>
                {s.name} ({s.code})
              </option>
            ))}
          </select>
        </label>
        <label>
          Bag count
          <input type="number" min={1} max={999} value={count} onChange={(e) => setCount(Number(e.target.value) || 1)} />
        </label>
        <button className="btn" type="submit">Create &amp; Print Labels</button>
      </form>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
