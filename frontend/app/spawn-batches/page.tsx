"use client";

import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPatch, apiPost } from "../../lib/api";
import type { GrainType, SpawnBatch, SterilizationRun } from "../../lib/types";

type SpawnType = "PURCHASED_BLOCK" | "IN_HOUSE_GRAIN";

type SpawnBatchForm = {
  spawn_type: SpawnType;
  strain_code: string;
  vendor: string;
  lot_code: string;
  made_at: string;
  incubation_start_at: string;
  sterilization_run_id: string;
  grain_type_id: string;
  grain_kg: string;
  vermiculite_kg: string;
  water_kg: string;
  supplement_kg: string;
  notes: string;
};

const emptyForm: SpawnBatchForm = {
  spawn_type: "PURCHASED_BLOCK",
  strain_code: "",
  vendor: "",
  lot_code: "",
  made_at: "",
  incubation_start_at: "",
  sterilization_run_id: "",
  grain_type_id: "",
  grain_kg: "",
  vermiculite_kg: "",
  water_kg: "",
  supplement_kg: "",
  notes: "",
};

function clearInHouseFields(form: SpawnBatchForm): SpawnBatchForm {
  return {
    ...form,
    sterilization_run_id: "",
    grain_type_id: "",
    grain_kg: "",
    vermiculite_kg: "",
    water_kg: "",
    supplement_kg: "",
  };
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

function toPayload(form: SpawnBatchForm) {
  const isInHouse = form.spawn_type === "IN_HOUSE_GRAIN";
  return {
    spawn_type: form.spawn_type,
    strain_code: form.strain_code.trim(),
    vendor: form.vendor.trim() || null,
    lot_code: form.lot_code.trim() || null,
    made_at: form.made_at ? new Date(form.made_at).toISOString() : null,
    incubation_start_at: form.incubation_start_at ? new Date(form.incubation_start_at).toISOString() : null,
    ...(isInHouse
      ? {
          sterilization_run_id: toNullableInt(form.sterilization_run_id),
          grain_type_id: toNullableInt(form.grain_type_id),
          grain_kg: toNullableNumber(form.grain_kg),
          vermiculite_kg: toNullableNumber(form.vermiculite_kg),
          water_kg: toNullableNumber(form.water_kg),
          supplement_kg: toNullableNumber(form.supplement_kg),
        }
      : {}),
    notes: form.notes.trim() || null,
  };
}

function toDateTimeLocal(value?: string | null): string {
  if (!value) return "";
  const d = new Date(value);
  const tzOffsetMs = d.getTimezoneOffset() * 60000;
  return new Date(d.getTime() - tzOffsetMs).toISOString().slice(0, 16);
}

function computeMetrics(form: SpawnBatchForm) {
  const grain = toNullableNumber(form.grain_kg);
  const verm = toNullableNumber(form.vermiculite_kg);
  const water = toNullableNumber(form.water_kg);
  const supplement = toNullableNumber(form.supplement_kg) ?? 0;

  if (grain == null || verm == null || water == null) return null;
  const dryTotal = grain + verm + supplement;
  if (dryTotal <= 0) return null;
  const hydrationRatio = water / dryTotal;
  const expectedAddedWaterWbPct = (water / (water + dryTotal)) * 100.0;
  return { hydrationRatio, expectedAddedWaterWbPct };
}

export default function SpawnBatchesPage() {
  const [items, setItems] = useState<SpawnBatch[]>([]);
  const [sterilizationRuns, setSterilizationRuns] = useState<SterilizationRun[]>([]);
  const [grainTypes, setGrainTypes] = useState<GrainType[]>([]);
  const [filterSpawnType, setFilterSpawnType] = useState<"" | SpawnType>("");
  const [filterStrainContains, setFilterStrainContains] = useState("");
  const [filterSterilizationRunId, setFilterSterilizationRunId] = useState("");
  const [filterGrainTypeId, setFilterGrainTypeId] = useState("");
  const [sortBy, setSortBy] = useState<"spawn_batch_id" | "made_at" | "incubation_start_at" | "strain_code">("spawn_batch_id");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [createForm, setCreateForm] = useState<SpawnBatchForm>(emptyForm);
  const [editForms, setEditForms] = useState<Record<number, SpawnBatchForm>>({});
  const [error, setError] = useState<string | null>(null);

  const defaultGrainTypeId = useMemo(() => {
    const rye = grainTypes.find((g) => g.name.toLowerCase() === "rye");
    return rye?.grain_type_id ?? grainTypes[0]?.grain_type_id ?? null;
  }, [grainTypes]);

  async function refresh() {
    const params = new URLSearchParams();
    if (filterSpawnType) params.set("spawn_type", filterSpawnType);
    if (filterStrainContains.trim()) params.set("strain_contains", filterStrainContains.trim());
    if (filterSterilizationRunId) params.set("sterilization_run_id", filterSterilizationRunId);
    if (filterGrainTypeId) params.set("grain_type_id", filterGrainTypeId);
    params.set("sort_by", sortBy);
    params.set("sort_order", sortOrder);
    const spawnPath = `/spawn-batches?${params.toString()}`;

    const [spawnData, runData, grainData] = await Promise.all([
      apiGet<SpawnBatch[]>(spawnPath),
      apiGet<SterilizationRun[]>("/sterilization-runs"),
      apiGet<GrainType[]>("/grain-types"),
    ]);
    setItems(spawnData);
    setSterilizationRuns(runData);
    setGrainTypes(grainData);

    const nextForms: Record<number, SpawnBatchForm> = {};
    for (const row of spawnData) {
      nextForms[row.spawn_batch_id] = {
        spawn_type: row.spawn_type,
        strain_code: row.strain_code ?? "",
        vendor: row.vendor ?? "",
        lot_code: row.lot_code ?? "",
        made_at: toDateTimeLocal(row.made_at),
        incubation_start_at: toDateTimeLocal(row.incubation_start_at),
        sterilization_run_id: row.sterilization_run_id == null ? "" : String(row.sterilization_run_id),
        grain_type_id: row.grain_type_id == null ? "" : String(row.grain_type_id),
        grain_kg: row.grain_kg == null ? "" : String(row.grain_kg),
        vermiculite_kg: row.vermiculite_kg == null ? "" : String(row.vermiculite_kg),
        water_kg: row.water_kg == null ? "" : String(row.water_kg),
        supplement_kg: row.supplement_kg == null ? "" : String(row.supplement_kg),
        notes: row.notes ?? "",
      };
    }
    setEditForms(nextForms);
  }

  useEffect(() => {
    refresh().catch((e) => setError(String(e)));
  }, [filterSpawnType, filterStrainContains, filterSterilizationRunId, filterGrainTypeId, sortBy, sortOrder]);

  useEffect(() => {
    if (!defaultGrainTypeId) return;
    setCreateForm((prev) => {
      if (prev.spawn_type !== "IN_HOUSE_GRAIN") return prev;
      if (prev.grain_type_id) return prev;
      return { ...prev, grain_type_id: String(defaultGrainTypeId) };
    });
  }, [defaultGrainTypeId]);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await apiPost<SpawnBatch>("/spawn-batches", toPayload(createForm));
      setCreateForm(emptyForm);
      await refresh();
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  async function onSave(spawnBatchId: number) {
    setError(null);
    try {
      await apiPatch<SpawnBatch>(`/spawn-batches/${spawnBatchId}`, toPayload(editForms[spawnBatchId]));
      await refresh();
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  const createComputed = computeMetrics(createForm);

  return (
    <div className="card">
      <h1>Spawn Batches</h1>

      <h2>Filter + Sort</h2>
      <div className="form">
        <label>
          Spawn Type
          <select value={filterSpawnType} onChange={(e) => setFilterSpawnType(e.target.value as "" | SpawnType)}>
            <option value="">(all)</option>
            <option value="PURCHASED_BLOCK">PURCHASED_BLOCK</option>
            <option value="IN_HOUSE_GRAIN">IN_HOUSE_GRAIN</option>
          </select>
        </label>
        <label>
          Strain contains
          <input value={filterStrainContains} onChange={(e) => setFilterStrainContains(e.target.value)} />
        </label>
        <label>
          Sterilization Run
          <select value={filterSterilizationRunId} onChange={(e) => setFilterSterilizationRunId(e.target.value)}>
            <option value="">(all)</option>
            {sterilizationRuns.map((run) => (
              <option key={run.sterilization_run_id} value={run.sterilization_run_id}>
                {run.run_code}
              </option>
            ))}
          </select>
        </label>
        <label>
          Grain Type
          <select value={filterGrainTypeId} onChange={(e) => setFilterGrainTypeId(e.target.value)}>
            <option value="">(all)</option>
            {grainTypes.map((grainType) => (
              <option key={grainType.grain_type_id} value={grainType.grain_type_id}>
                {grainType.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Sort By
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value as "spawn_batch_id" | "made_at" | "incubation_start_at" | "strain_code")}>
            <option value="spawn_batch_id">ID</option>
            <option value="made_at">Made At</option>
            <option value="incubation_start_at">Incubation Start</option>
            <option value="strain_code">Strain Code</option>
          </select>
        </label>
        <label>
          Sort Order
          <select value={sortOrder} onChange={(e) => setSortOrder(e.target.value as "asc" | "desc")}>
            <option value="desc">desc</option>
            <option value="asc">asc</option>
          </select>
        </label>
      </div>

      <h2>Create Spawn Batch</h2>
      <form className="form" onSubmit={onCreate}>
        <label>
          Spawn Type
          <select
            value={createForm.spawn_type}
            onChange={(e) =>
              setCreateForm((p) => {
                const next = { ...p, spawn_type: e.target.value as SpawnType };
                if (next.spawn_type !== "IN_HOUSE_GRAIN") return clearInHouseFields(next);
                if (!next.grain_type_id && defaultGrainTypeId) next.grain_type_id = String(defaultGrainTypeId);
                return next;
              })
            }
          >
            <option value="PURCHASED_BLOCK">PURCHASED_BLOCK</option>
            <option value="IN_HOUSE_GRAIN">IN_HOUSE_GRAIN</option>
          </select>
        </label>
        <label>
          Strain Code
          <input
            required
            value={createForm.strain_code}
            onChange={(e) => setCreateForm((p) => ({ ...p, strain_code: e.target.value }))}
            placeholder="e.g., LM, PO"
          />
        </label>
        <label>
          Vendor
          <input value={createForm.vendor} onChange={(e) => setCreateForm((p) => ({ ...p, vendor: e.target.value }))} />
        </label>
        <label>
          Lot Code
          <input value={createForm.lot_code} onChange={(e) => setCreateForm((p) => ({ ...p, lot_code: e.target.value }))} />
        </label>
        <label>
          Made At
          <input type="datetime-local" value={createForm.made_at} onChange={(e) => setCreateForm((p) => ({ ...p, made_at: e.target.value }))} />
        </label>
        <label>
          Incubation Start At
          <input
            type="datetime-local"
            value={createForm.incubation_start_at}
            onChange={(e) => setCreateForm((p) => ({ ...p, incubation_start_at: e.target.value }))}
          />
        </label>

        {createForm.spawn_type === "IN_HOUSE_GRAIN" && (
          <>
            <label>
              Sterilization run (autoclave)
              <select
                value={createForm.sterilization_run_id}
                onChange={(e) => setCreateForm((p) => ({ ...p, sterilization_run_id: e.target.value }))}
              >
                <option value="">(optional)</option>
                {sterilizationRuns.map((run) => (
                  <option key={run.sterilization_run_id} value={run.sterilization_run_id}>
                    {run.run_code}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Grain type
              <select
                value={createForm.grain_type_id}
                onChange={(e) => setCreateForm((p) => ({ ...p, grain_type_id: e.target.value }))}
              >
                <option value="">Select grain type...</option>
                {grainTypes.map((grainType) => (
                  <option key={grainType.grain_type_id} value={grainType.grain_type_id}>
                    {grainType.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Grain (kg)
              <input
                type="number"
                min="0"
                step="0.001"
                value={createForm.grain_kg}
                onChange={(e) => setCreateForm((p) => ({ ...p, grain_kg: e.target.value }))}
              />
            </label>
            <label>
              Vermiculite (kg)
              <input
                type="number"
                min="0"
                step="0.001"
                value={createForm.vermiculite_kg}
                onChange={(e) => setCreateForm((p) => ({ ...p, vermiculite_kg: e.target.value }))}
              />
            </label>
            <label>
              Water added to dry grain/verm (no-soak/no-simmer)
              <input
                type="number"
                min="0"
                step="0.001"
                value={createForm.water_kg}
                onChange={(e) => setCreateForm((p) => ({ ...p, water_kg: e.target.value }))}
              />
            </label>
            <label>
              Supplement (kg, optional)
              <input
                type="number"
                min="0"
                step="0.001"
                value={createForm.supplement_kg}
                onChange={(e) => setCreateForm((p) => ({ ...p, supplement_kg: e.target.value }))}
              />
            </label>
            <p>
              Hydration Ratio: {createComputed ? createComputed.hydrationRatio.toFixed(4) : "n/a"} | Expected added-water wb%:{" "}
              {createComputed ? createComputed.expectedAddedWaterWbPct.toFixed(2) : "n/a"}
            </p>
          </>
        )}
        <label>
          Notes
          <input value={createForm.notes} onChange={(e) => setCreateForm((p) => ({ ...p, notes: e.target.value }))} />
        </label>
        <button className="btn" type="submit">Create Spawn Batch</button>
      </form>

      <h2>Existing Spawn Batches</h2>
      <table className="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Type</th>
            <th>Strain</th>
            <th>Vendor</th>
            <th>Lot</th>
            <th>Made At</th>
            <th>Sterilization Run</th>
            <th>Grain Type</th>
            <th>Grain kg</th>
            <th>Verm kg</th>
            <th>Water kg</th>
            <th>Supplement kg</th>
            <th>Hydration Ratio</th>
            <th>Expected added-water wb%</th>
            <th>Notes</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const form = editForms[item.spawn_batch_id];
            if (!form) return null;
            const computed = computeMetrics(form);
            const isInHouse = form.spawn_type === "IN_HOUSE_GRAIN";
            return (
              <tr key={item.spawn_batch_id}>
                <td>{item.spawn_batch_id}</td>
                <td>
                  <select
                    value={form.spawn_type}
                    onChange={(e) =>
                      setEditForms((p) => {
                        const next = { ...p[item.spawn_batch_id], spawn_type: e.target.value as SpawnType };
                        if (next.spawn_type !== "IN_HOUSE_GRAIN") return { ...p, [item.spawn_batch_id]: clearInHouseFields(next) };
                        if (!next.grain_type_id && defaultGrainTypeId) next.grain_type_id = String(defaultGrainTypeId);
                        return { ...p, [item.spawn_batch_id]: next };
                      })
                    }
                  >
                    <option value="PURCHASED_BLOCK">PURCHASED_BLOCK</option>
                    <option value="IN_HOUSE_GRAIN">IN_HOUSE_GRAIN</option>
                  </select>
                </td>
                <td>
                  <input
                    value={form.strain_code}
                    onChange={(e) =>
                      setEditForms((p) => ({ ...p, [item.spawn_batch_id]: { ...p[item.spawn_batch_id], strain_code: e.target.value } }))
                    }
                  />
                </td>
                <td>
                  <input
                    value={form.vendor}
                    onChange={(e) =>
                      setEditForms((p) => ({ ...p, [item.spawn_batch_id]: { ...p[item.spawn_batch_id], vendor: e.target.value } }))
                    }
                  />
                </td>
                <td>
                  <input
                    value={form.lot_code}
                    onChange={(e) =>
                      setEditForms((p) => ({ ...p, [item.spawn_batch_id]: { ...p[item.spawn_batch_id], lot_code: e.target.value } }))
                    }
                  />
                </td>
                <td>
                  <input
                    type="datetime-local"
                    value={form.made_at}
                    onChange={(e) =>
                      setEditForms((p) => ({ ...p, [item.spawn_batch_id]: { ...p[item.spawn_batch_id], made_at: e.target.value } }))
                    }
                  />
                </td>
                <td>
                  {isInHouse && (
                    <select
                      value={form.sterilization_run_id}
                      onChange={(e) =>
                        setEditForms((p) => ({
                          ...p,
                          [item.spawn_batch_id]: { ...p[item.spawn_batch_id], sterilization_run_id: e.target.value },
                        }))
                      }
                    >
                      <option value="">(optional)</option>
                      {sterilizationRuns.map((run) => (
                        <option key={run.sterilization_run_id} value={run.sterilization_run_id}>
                          {run.run_code}
                        </option>
                      ))}
                    </select>
                  )}
                </td>
                <td>
                  {isInHouse && (
                    <select
                      value={form.grain_type_id}
                      onChange={(e) =>
                        setEditForms((p) => ({
                          ...p,
                          [item.spawn_batch_id]: { ...p[item.spawn_batch_id], grain_type_id: e.target.value },
                        }))
                      }
                    >
                      <option value="">Select grain type...</option>
                      {grainTypes.map((grainType) => (
                        <option key={grainType.grain_type_id} value={grainType.grain_type_id}>
                          {grainType.name}
                        </option>
                      ))}
                    </select>
                  )}
                </td>
                <td>
                  {isInHouse && (
                    <input
                      type="number"
                      min="0"
                      step="0.001"
                      value={form.grain_kg}
                      onChange={(e) =>
                        setEditForms((p) => ({ ...p, [item.spawn_batch_id]: { ...p[item.spawn_batch_id], grain_kg: e.target.value } }))
                      }
                    />
                  )}
                </td>
                <td>
                  {isInHouse && (
                    <input
                      type="number"
                      min="0"
                      step="0.001"
                      value={form.vermiculite_kg}
                      onChange={(e) =>
                        setEditForms((p) => ({
                          ...p,
                          [item.spawn_batch_id]: { ...p[item.spawn_batch_id], vermiculite_kg: e.target.value },
                        }))
                      }
                    />
                  )}
                </td>
                <td>
                  {isInHouse && (
                    <input
                      type="number"
                      min="0"
                      step="0.001"
                      value={form.water_kg}
                      onChange={(e) =>
                        setEditForms((p) => ({ ...p, [item.spawn_batch_id]: { ...p[item.spawn_batch_id], water_kg: e.target.value } }))
                      }
                    />
                  )}
                </td>
                <td>
                  {isInHouse && (
                    <input
                      type="number"
                      min="0"
                      step="0.001"
                      value={form.supplement_kg}
                      onChange={(e) =>
                        setEditForms((p) => ({
                          ...p,
                          [item.spawn_batch_id]: { ...p[item.spawn_batch_id], supplement_kg: e.target.value },
                        }))
                      }
                    />
                  )}
                </td>
                <td>{isInHouse ? (computed ? computed.hydrationRatio.toFixed(4) : "n/a") : ""}</td>
                <td>{isInHouse ? (computed ? computed.expectedAddedWaterWbPct.toFixed(2) : "n/a") : ""}</td>
                <td>
                  <input
                    value={form.notes}
                    onChange={(e) =>
                      setEditForms((p) => ({ ...p, [item.spawn_batch_id]: { ...p[item.spawn_batch_id], notes: e.target.value } }))
                    }
                  />
                </td>
                <td>
                  <button className="btn" onClick={() => onSave(item.spawn_batch_id)}>Save</button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {error && <p className="error">{error}</p>}
    </div>
  );
}
