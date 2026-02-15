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
  notes: string;
};

const emptyForm: SpawnBatchForm = {
  spawn_type: "PURCHASED_BLOCK",
  strain_code: "",
  vendor: "",
  lot_code: "",
  made_at: "",
  incubation_start_at: "",
  notes: "",
};

function toPayload(form: SpawnBatchForm) {
  return {
    spawn_type: form.spawn_type,
    strain_code: form.strain_code.trim(),
    vendor: form.vendor.trim() || null,
    lot_code: form.lot_code.trim() || null,
    made_at: form.made_at ? new Date(form.made_at).toISOString() : null,
    incubation_start_at: form.incubation_start_at ? new Date(form.incubation_start_at).toISOString() : null,
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
