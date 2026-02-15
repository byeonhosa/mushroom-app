"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPatch, apiPost } from "../../lib/api";
import type { SpawnBatch } from "../../lib/types";

type SpawnType = "PURCHASED_BLOCK" | "IN_HOUSE_GRAIN";

type SpawnBatchForm = {
  spawn_type: SpawnType;
  strain_code: string;
  vendor: string;
  lot_code: string;
  made_at: string;
  incubation_start_at: string;
  grain_dry_kg: string;
  grain_water_kg: string;
  supplement_kg: string;
  lc_vendor: string;
  lc_code: string;
  sterilization_run_code: string;
  incubation_zone_id: string;
  notes: string;
};

const emptyForm: SpawnBatchForm = {
  spawn_type: "PURCHASED_BLOCK",
  strain_code: "",
  vendor: "",
  lot_code: "",
  made_at: "",
  incubation_start_at: "",
  grain_dry_kg: "",
  grain_water_kg: "",
  supplement_kg: "",
  lc_vendor: "",
  lc_code: "",
  sterilization_run_code: "",
  incubation_zone_id: "",
  notes: "",
};

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
    grain_dry_kg: isInHouse ? toNullableNumber(form.grain_dry_kg) : null,
    grain_water_kg: isInHouse ? toNullableNumber(form.grain_water_kg) : null,
    supplement_kg: isInHouse ? toNullableNumber(form.supplement_kg) : null,
    lc_vendor: isInHouse ? (form.lc_vendor.trim() || null) : null,
    lc_code: isInHouse ? (form.lc_code.trim() || null) : null,
    sterilization_run_code: isInHouse ? (form.sterilization_run_code.trim() || null) : null,
    incubation_zone_id: isInHouse ? toNullableInt(form.incubation_zone_id) : null,
    notes: form.notes.trim() || null,
  };
}

function toDateTimeLocal(value?: string | null): string {
  if (!value) return "";
  const d = new Date(value);
  const tzOffsetMs = d.getTimezoneOffset() * 60000;
  return new Date(d.getTime() - tzOffsetMs).toISOString().slice(0, 16);
}

export default function SpawnBatchesPage() {
  const [items, setItems] = useState<SpawnBatch[]>([]);
  const [createForm, setCreateForm] = useState<SpawnBatchForm>(emptyForm);
  const [editForms, setEditForms] = useState<Record<number, SpawnBatchForm>>({});
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    const data = await apiGet<SpawnBatch[]>("/spawn-batches");
    setItems(data);
    const nextForms: Record<number, SpawnBatchForm> = {};
    for (const row of data) {
      nextForms[row.spawn_batch_id] = {
        spawn_type: row.spawn_type,
        strain_code: row.strain_code ?? "",
        vendor: row.vendor ?? "",
        lot_code: row.lot_code ?? "",
        made_at: toDateTimeLocal(row.made_at),
        incubation_start_at: toDateTimeLocal(row.incubation_start_at),
        grain_dry_kg: row.grain_dry_kg == null ? "" : String(row.grain_dry_kg),
        grain_water_kg: row.grain_water_kg == null ? "" : String(row.grain_water_kg),
        supplement_kg: row.supplement_kg == null ? "" : String(row.supplement_kg),
        lc_vendor: row.lc_vendor ?? "",
        lc_code: row.lc_code ?? "",
        sterilization_run_code: row.sterilization_run_code ?? "",
        incubation_zone_id: row.incubation_zone_id == null ? "" : String(row.incubation_zone_id),
        notes: row.notes ?? "",
      };
    }
    setEditForms(nextForms);
  }

  useEffect(() => {
    refresh().catch((e) => setError(String(e)));
  }, []);

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
    const payload = toPayload(editForms[spawnBatchId]);
    try {
      await apiPatch<SpawnBatch>(`/spawn-batches/${spawnBatchId}`, payload);
      await refresh();
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  return (
    <div className="card">
      <h1>Spawn Batches</h1>

      <h2>Create Spawn Batch</h2>
      <form className="form" onSubmit={onCreate}>
        <label>
          Spawn Type
          <select
            value={createForm.spawn_type}
            onChange={(e) => setCreateForm((p) => ({ ...p, spawn_type: e.target.value as SpawnType }))}
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
          <input
            type="datetime-local"
            value={createForm.made_at}
            onChange={(e) => setCreateForm((p) => ({ ...p, made_at: e.target.value }))}
          />
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
              Grain Dry (kg)
              <input
                type="number"
                min="0"
                step="0.001"
                value={createForm.grain_dry_kg}
                onChange={(e) => setCreateForm((p) => ({ ...p, grain_dry_kg: e.target.value }))}
              />
            </label>
            <label>
              Grain Water (kg)
              <input
                type="number"
                min="0"
                step="0.001"
                value={createForm.grain_water_kg}
                onChange={(e) => setCreateForm((p) => ({ ...p, grain_water_kg: e.target.value }))}
              />
            </label>
            <label>
              Supplement (kg)
              <input
                type="number"
                min="0"
                step="0.001"
                value={createForm.supplement_kg}
                onChange={(e) => setCreateForm((p) => ({ ...p, supplement_kg: e.target.value }))}
              />
            </label>
            <label>
              LC Vendor
              <input
                value={createForm.lc_vendor}
                onChange={(e) => setCreateForm((p) => ({ ...p, lc_vendor: e.target.value }))}
              />
            </label>
            <label>
              LC Code
              <input
                value={createForm.lc_code}
                onChange={(e) => setCreateForm((p) => ({ ...p, lc_code: e.target.value }))}
              />
            </label>
            <label>
              Sterilization Run Code
              <input
                value={createForm.sterilization_run_code}
                onChange={(e) => setCreateForm((p) => ({ ...p, sterilization_run_code: e.target.value }))}
              />
            </label>
            <label>
              Incubation Zone ID
              <input
                type="number"
                min="1"
                step="1"
                value={createForm.incubation_zone_id}
                onChange={(e) => setCreateForm((p) => ({ ...p, incubation_zone_id: e.target.value }))}
              />
            </label>
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
            <th>Incubation Start</th>
            <th>Grain Dry kg</th>
            <th>Grain Water kg</th>
            <th>Supplement kg</th>
            <th>LC Vendor</th>
            <th>LC Code</th>
            <th>Sterilization Run</th>
            <th>Incubation Zone ID</th>
            <th>Notes</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const form = editForms[item.spawn_batch_id];
            if (!form) return null;
            return (
              <tr key={item.spawn_batch_id}>
                <td>{item.spawn_batch_id}</td>
                <td>
                  <select
                    value={form.spawn_type}
                    onChange={(e) =>
                      setEditForms((p) => ({
                        ...p,
                        [item.spawn_batch_id]: { ...p[item.spawn_batch_id], spawn_type: e.target.value as SpawnType },
                      }))
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
                      setEditForms((p) => ({
                        ...p,
                        [item.spawn_batch_id]: { ...p[item.spawn_batch_id], strain_code: e.target.value },
                      }))
                    }
                  />
                </td>
                <td>
                  <input
                    value={form.vendor}
                    onChange={(e) =>
                      setEditForms((p) => ({
                        ...p,
                        [item.spawn_batch_id]: { ...p[item.spawn_batch_id], vendor: e.target.value },
                      }))
                    }
                  />
                </td>
                <td>
                  <input
                    value={form.lot_code}
                    onChange={(e) =>
                      setEditForms((p) => ({
                        ...p,
                        [item.spawn_batch_id]: { ...p[item.spawn_batch_id], lot_code: e.target.value },
                      }))
                    }
                  />
                </td>
                <td>
                  <input
                    type="datetime-local"
                    value={form.made_at}
                    onChange={(e) =>
                      setEditForms((p) => ({
                        ...p,
                        [item.spawn_batch_id]: { ...p[item.spawn_batch_id], made_at: e.target.value },
                      }))
                    }
                  />
                </td>
                <td>
                  <input
                    type="datetime-local"
                    value={form.incubation_start_at}
                    onChange={(e) =>
                      setEditForms((p) => ({
                        ...p,
                        [item.spawn_batch_id]: { ...p[item.spawn_batch_id], incubation_start_at: e.target.value },
                      }))
                    }
                  />
                </td>
                <td>
                  {form.spawn_type === "IN_HOUSE_GRAIN" && (
                    <input
                      type="number"
                      min="0"
                      step="0.001"
                      value={form.grain_dry_kg}
                      onChange={(e) =>
                        setEditForms((p) => ({
                          ...p,
                          [item.spawn_batch_id]: { ...p[item.spawn_batch_id], grain_dry_kg: e.target.value },
                        }))
                      }
                    />
                  )}
                </td>
                <td>
                  {form.spawn_type === "IN_HOUSE_GRAIN" && (
                    <input
                      type="number"
                      min="0"
                      step="0.001"
                      value={form.grain_water_kg}
                      onChange={(e) =>
                        setEditForms((p) => ({
                          ...p,
                          [item.spawn_batch_id]: { ...p[item.spawn_batch_id], grain_water_kg: e.target.value },
                        }))
                      }
                    />
                  )}
                </td>
                <td>
                  {form.spawn_type === "IN_HOUSE_GRAIN" && (
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
                <td>
                  {form.spawn_type === "IN_HOUSE_GRAIN" && (
                    <input
                      value={form.lc_vendor}
                      onChange={(e) =>
                        setEditForms((p) => ({
                          ...p,
                          [item.spawn_batch_id]: { ...p[item.spawn_batch_id], lc_vendor: e.target.value },
                        }))
                      }
                    />
                  )}
                </td>
                <td>
                  {form.spawn_type === "IN_HOUSE_GRAIN" && (
                    <input
                      value={form.lc_code}
                      onChange={(e) =>
                        setEditForms((p) => ({
                          ...p,
                          [item.spawn_batch_id]: { ...p[item.spawn_batch_id], lc_code: e.target.value },
                        }))
                      }
                    />
                  )}
                </td>
                <td>
                  {form.spawn_type === "IN_HOUSE_GRAIN" && (
                    <input
                      value={form.sterilization_run_code}
                      onChange={(e) =>
                        setEditForms((p) => ({
                          ...p,
                          [item.spawn_batch_id]: { ...p[item.spawn_batch_id], sterilization_run_code: e.target.value },
                        }))
                      }
                    />
                  )}
                </td>
                <td>
                  {form.spawn_type === "IN_HOUSE_GRAIN" && (
                    <input
                      type="number"
                      min="1"
                      step="1"
                      value={form.incubation_zone_id}
                      onChange={(e) =>
                        setEditForms((p) => ({
                          ...p,
                          [item.spawn_batch_id]: { ...p[item.spawn_batch_id], incubation_zone_id: e.target.value },
                        }))
                      }
                    />
                  )}
                </td>
                <td>
                  <input
                    value={form.notes}
                    onChange={(e) =>
                      setEditForms((p) => ({
                        ...p,
                        [item.spawn_batch_id]: { ...p[item.spawn_batch_id], notes: e.target.value },
                      }))
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
