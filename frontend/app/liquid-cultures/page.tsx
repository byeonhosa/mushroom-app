"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../../lib/api";
import type { LiquidCulture, MushroomSpecies } from "../../lib/types";

export default function LiquidCulturesPage() {
  const [cultures, setCultures] = useState<LiquidCulture[]>([]);
  const [species, setSpecies] = useState<MushroomSpecies[]>([]);
  const [cultureCode, setCultureCode] = useState("");
  const [speciesId, setSpeciesId] = useState<number | "">("");
  const [source, setSource] = useState("");
  const [preparedAt, setPreparedAt] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function loadAll() {
    const [cultureRows, speciesRows] = await Promise.all([
      apiGet<LiquidCulture[]>("/liquid-cultures?active_only=false"),
      apiGet<MushroomSpecies[]>("/species?active_only=false"),
    ]);
    setCultures(cultureRows);
    setSpecies(speciesRows);
    if (speciesRows.length > 0) {
      setSpeciesId((current) => current || speciesRows[0].species_id);
    }
  }

  useEffect(() => {
    loadAll().catch((e) => setError(e?.message || String(e)));
  }, []);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    if (speciesId === "") {
      setError("Select a species.");
      return;
    }

    try {
      await apiPost<LiquidCulture>("/liquid-cultures", {
        culture_code: cultureCode.trim(),
        species_id: speciesId,
        source: source.trim() || null,
        prepared_at: preparedAt ? new Date(preparedAt).toISOString() : null,
        notes: notes.trim() || null,
        is_active: true,
      });
      setCultureCode("");
      setSource("");
      setPreparedAt("");
      setNotes("");
      await loadAll();
      setSuccess("Liquid culture created.");
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  const speciesById = new Map(species.map((row) => [row.species_id, `${row.name} (${row.code})`]));

  return (
    <div className="card">
      <h1>Liquid Cultures</h1>
      <p>Lightweight source registry for spawn-bag inoculation.</p>

      {success && <p style={{ background: "#e9f8ed", border: "1px solid #9fd3ab", padding: 10, borderRadius: 8 }}>{success}</p>}
      {error && <p className="error">{error}</p>}

      <form className="form" onSubmit={onCreate}>
        <label>
          Culture Code
          <input value={cultureCode} onChange={(e) => setCultureCode(e.target.value)} required />
        </label>
        <label>
          Species
          <select value={speciesId} onChange={(e) => setSpeciesId(Number(e.target.value) || "")} required>
            <option value="">— Select —</option>
            {species.map((row) => (
              <option key={row.species_id} value={row.species_id}>
                {row.name} ({row.code})
              </option>
            ))}
          </select>
        </label>
        <label>
          Source
          <input value={source} onChange={(e) => setSource(e.target.value)} placeholder="Vendor, lab, or internal source" />
        </label>
        <label>
          Prepared / Received
          <input type="datetime-local" value={preparedAt} onChange={(e) => setPreparedAt(e.target.value)} />
        </label>
        <label>
          Notes
          <input value={notes} onChange={(e) => setNotes(e.target.value)} />
        </label>
        <button className="btn" type="submit">Add Liquid Culture</button>
      </form>

      <table className="table">
        <thead>
          <tr>
            <th>Code</th>
            <th>Species</th>
            <th>Source</th>
            <th>Prepared</th>
            <th>Active</th>
          </tr>
        </thead>
        <tbody>
          {cultures.map((culture) => (
            <tr key={culture.liquid_culture_id}>
              <td>{culture.culture_code}</td>
              <td>{speciesById.get(culture.species_id) ?? culture.species_id}</td>
              <td>{culture.source ?? "-"}</td>
              <td>{culture.prepared_at ? new Date(culture.prepared_at).toLocaleString() : "-"}</td>
              <td>{culture.is_active ? "yes" : "no"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
