"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPatch, apiPost } from "../../lib/api";
import type { MushroomSpecies } from "../../lib/types";

export default function SpeciesPage() {
  const [rows, setRows] = useState<MushroomSpecies[]>([]);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [latinName, setLatinName] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function loadAll() {
    const items = await apiGet<MushroomSpecies[]>("/species?active_only=false");
    setRows(items);
  }

  useEffect(() => {
    loadAll().catch((e) => setError(e?.message || String(e)));
  }, []);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    try {
      await apiPost<MushroomSpecies>("/species", {
        code: code.trim(),
        name: name.trim(),
        latin_name: latinName.trim() || null,
        notes: notes.trim() || null,
        is_active: true,
      });
      setCode("");
      setName("");
      setLatinName("");
      setNotes("");
      await loadAll();
      setSuccess("Species created.");
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  async function toggleActive(row: MushroomSpecies) {
    setError(null);
    setSuccess(null);
    try {
      await apiPatch<MushroomSpecies>(`/species/${row.species_id}`, { is_active: !row.is_active });
      await loadAll();
      setSuccess("Species updated.");
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  return (
    <div className="card">
      <h1>Species</h1>
      <p>Admin-only page.</p>
      {success && <p style={{ background: "#e9f8ed", border: "1px solid #9fd3ab", padding: 10, borderRadius: 8 }}>{success}</p>}
      {error && <p className="error">{error}</p>}

      <form className="form" onSubmit={onCreate}>
        <label>
          Code
          <input value={code} onChange={(e) => setCode(e.target.value)} required />
        </label>
        <label>
          Name
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label>
          Latin Name
          <input value={latinName} onChange={(e) => setLatinName(e.target.value)} />
        </label>
        <label>
          Notes
          <input value={notes} onChange={(e) => setNotes(e.target.value)} />
        </label>
        <button className="btn" type="submit">Add Species</button>
      </form>

      <table className="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Code</th>
            <th>Name</th>
            <th>Latin</th>
            <th>Active</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.species_id}>
              <td>{r.species_id}</td>
              <td>{r.code}</td>
              <td>{r.name}</td>
              <td>{r.latin_name ?? ""}</td>
              <td>{r.is_active ? "yes" : "no"}</td>
              <td>
                <button className="btn" type="button" onClick={() => toggleActive(r)}>
                  {r.is_active ? "Deactivate" : "Activate"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
