"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiGet, apiPost } from "../../../lib/api";
import type { SterilizationRun, LiquidCulture, Bag } from "../../../lib/types";

export default function SpawnInoculationPage() {
  const router = useRouter();
  const [runs, setRuns] = useState<SterilizationRun[]>([]);
  const [liquidCultures, setLiquidCultures] = useState<LiquidCulture[]>([]);
  const [readySpawnBags, setReadySpawnBags] = useState<Bag[]>([]);
  const [runId, setRunId] = useState<number | "">("");
  const [sourceType, setSourceType] = useState<"LIQUID_CULTURE" | "SPAWN_BAG">("LIQUID_CULTURE");
  const [liquidCultureId, setLiquidCultureId] = useState<number | "">("");
  const [donorSpawnBagId, setDonorSpawnBagId] = useState<string>("");
  const [count, setCount] = useState(1);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const [runRows, cultureRows, donorRows] = await Promise.all([
        apiGet<SterilizationRun[]>("/sterilization-runs"),
        apiGet<LiquidCulture[]>("/liquid-cultures"),
        apiGet<Bag[]>("/bags?bag_type=SPAWN&status=READY"),
      ]);
      setRuns(runRows);
      setLiquidCultures(cultureRows);
      setReadySpawnBags(donorRows);
      if (runRows.length > 0) {
        setRunId((current) => current || runRows[0].sterilization_run_id);
      }
      if (cultureRows.length > 0) {
        setLiquidCultureId((current) => current || cultureRows[0].liquid_culture_id);
      }
      if (donorRows.length > 0) {
        setDonorSpawnBagId((current) => current || donorRows[0].bag_ref);
      }
      if (cultureRows.length === 0 && donorRows.length > 0) {
        setSourceType("SPAWN_BAG");
      }
    })().catch((e) => setError(String(e)));
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (runId === "") {
      setError("Select a sterilization run.");
      return;
    }
    if (sourceType === "LIQUID_CULTURE" && liquidCultureId === "") {
      setError("Select a liquid culture.");
      return;
    }
    if (sourceType === "SPAWN_BAG" && !donorSpawnBagId) {
      setError("Select a donor spawn bag.");
      return;
    }

    try {
      const bags = await apiPost<Bag[]>("/spawn-inoculations/batch", {
        sterilization_run_id: runId,
        bag_count: count,
        source_type: sourceType,
        liquid_culture_id: sourceType === "LIQUID_CULTURE" ? liquidCultureId : undefined,
        donor_spawn_bag_id: sourceType === "SPAWN_BAG" ? donorSpawnBagId : undefined,
      });
      router.push(
        `/bags/create/spawn/labels?ids=${bags.map((bag) => encodeURIComponent(bag.bag_ref)).join(",")}`,
      );
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  return (
    <div className="card">
      <h1>Spawn Inoculation</h1>
      <p>
        Select the sterilization run and the actual inoculation source. Spawn bag codes are assigned after inoculation,
        when labels can safely be printed and attached.
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
          Source Type
          <select
            value={sourceType}
            onChange={(e) => setSourceType(e.target.value as "LIQUID_CULTURE" | "SPAWN_BAG")}
          >
            <option value="LIQUID_CULTURE">Liquid Culture</option>
            <option value="SPAWN_BAG">Donor Spawn Bag</option>
          </select>
        </label>
        {sourceType === "LIQUID_CULTURE" ? (
          <label>
            Liquid Culture
            <select value={liquidCultureId} onChange={(e) => setLiquidCultureId(Number(e.target.value) || "")} required>
              <option value="">— Select —</option>
              {liquidCultures.map((culture) => (
                <option key={culture.liquid_culture_id} value={culture.liquid_culture_id}>
                  {culture.culture_code}
                  {culture.source ? ` - ${culture.source}` : ""}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <label>
            Donor Spawn Bag
            <select value={donorSpawnBagId} onChange={(e) => setDonorSpawnBagId(e.target.value)} required>
              <option value="">— Select —</option>
              {readySpawnBags.map((bag) => (
                <option key={bag.bag_id} value={bag.bag_ref}>
                  {bag.bag_ref}
                </option>
              ))}
            </select>
          </label>
        )}
        <label>
          Bag count
          <input type="number" min={1} max={999} value={count} onChange={(e) => setCount(Number(e.target.value) || 1)} />
        </label>
        {sourceType === "LIQUID_CULTURE" && liquidCultures.length === 0 && (
          <p className="error">No active liquid cultures are available yet. Add one on the Liquid Cultures page first.</p>
        )}
        {sourceType === "SPAWN_BAG" && readySpawnBags.length === 0 && (
          <p className="error">No ready donor spawn bags are available yet.</p>
        )}
        <button className="btn" type="submit">Assign Codes &amp; Print Labels</button>
      </form>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
