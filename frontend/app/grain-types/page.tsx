"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPatch, apiPost } from "../../lib/api";
import type { GrainType } from "../../lib/types";

type GrainTypeForm = {
  name: string;
  notes: string;
};

const emptyForm: GrainTypeForm = { name: "", notes: "" };

export default function GrainTypesPage() {
  const [items, setItems] = useState<GrainType[]>([]);
  const [createForm, setCreateForm] = useState<GrainTypeForm>(emptyForm);
  const [editForms, setEditForms] = useState<Record<number, GrainTypeForm>>({});
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    const data = await apiGet<GrainType[]>("/grain-types");
    setItems(data);
    const nextForms: Record<number, GrainTypeForm> = {};
    for (const row of data) {
      nextForms[row.grain_type_id] = {
        name: row.name ?? "",
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
      await apiPost<GrainType>("/grain-types", {
        name: createForm.name.trim(),
        notes: createForm.notes.trim() || null,
      });
      setCreateForm(emptyForm);
      await refresh();
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  async function onSave(grainTypeId: number) {
    setError(null);
    try {
      await apiPatch<GrainType>(`/grain-types/${grainTypeId}`, {
        name: editForms[grainTypeId].name.trim(),
        notes: editForms[grainTypeId].notes.trim() || null,
      });
      await refresh();
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  return (
    <div className="card">
      <h1>Grain Types</h1>

      <h2>Create Grain Type</h2>
      <form className="form" onSubmit={onCreate}>
        <label>
          Name
          <input
            required
            value={createForm.name}
            onChange={(e) => setCreateForm((p) => ({ ...p, name: e.target.value }))}
            placeholder="e.g., Rye, Millet, Sorghum"
          />
        </label>
        <label>
          Notes
          <input
            value={createForm.notes}
            onChange={(e) => setCreateForm((p) => ({ ...p, notes: e.target.value }))}
          />
        </label>
        <button className="btn" type="submit">Create Grain Type</button>
      </form>

      <h2>Existing Grain Types</h2>
      <table className="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Notes</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const form = editForms[item.grain_type_id];
            if (!form) return null;
            return (
              <tr key={item.grain_type_id}>
                <td>{item.grain_type_id}</td>
                <td>
                  <input
                    value={form.name}
                    onChange={(e) =>
                      setEditForms((p) => ({
                        ...p,
                        [item.grain_type_id]: { ...p[item.grain_type_id], name: e.target.value },
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
                        [item.grain_type_id]: { ...p[item.grain_type_id], notes: e.target.value },
                      }))
                    }
                  />
                </td>
                <td>
                  <button className="btn" onClick={() => onSave(item.grain_type_id)}>Save</button>
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
