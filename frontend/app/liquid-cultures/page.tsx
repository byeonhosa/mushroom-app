"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPatch, apiPost } from "../../lib/api";
import type { LiquidCulture, MushroomSpecies } from "../../lib/types";

export default function LiquidCulturesPage() {
  const [cultures, setCultures] = useState<LiquidCulture[]>([]);
  const [species, setSpecies] = useState<MushroomSpecies[]>([]);
  const [cultureCode, setCultureCode] = useState("");
  const [speciesId, setSpeciesId] = useState<number | "">("");
  const [parentId, setParentId] = useState<number | "">("");
  const [source, setSource] = useState("");
  const [preparedAt, setPreparedAt] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function loadAll() {
    const [cultureRows, speciesRows] = await Promise.all([
      apiGet<LiquidCulture[]>("/liquid-cultures?active_only=false"),
      apiGet<MushroomSpecies[]>("/species?active_only=false"),
    ]);
    setCultures(cultureRows);
    setSpecies(speciesRows);
  }

  useEffect(() => {
    loadAll().catch((e) => setError(e?.message || String(e)));
  }, []);

  // A culture can only be made from a culture of the same species.
  const possibleParents = cultures.filter((culture) => speciesId !== "" && culture.species_id === speciesId);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    if (speciesId === "") {
      setError("Select a species.");
      return;
    }
    setBusy(true);
    try {
      const created = await apiPost<LiquidCulture>("/liquid-cultures", {
        culture_code: cultureCode.trim(),
        species_id: speciesId,
        parent_liquid_culture_id: parentId === "" ? null : parentId,
        source: source.trim() || null,
        prepared_at: preparedAt ? new Date(preparedAt).toISOString() : null,
        notes: notes.trim() || null,
        is_active: true,
      });
      setCultureCode("");
      setParentId("");
      setSource("");
      setPreparedAt("");
      setNotes("");
      await loadAll();
      setSuccess(`Added ${created.culture_code}.`);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  async function setActive(culture: LiquidCulture, active: boolean) {
    setError(null);
    setSuccess(null);
    setBusy(true);
    try {
      await apiPatch<LiquidCulture>(`/liquid-cultures/${culture.liquid_culture_id}`, { is_active: active });
      await loadAll();
      setSuccess(
        active
          ? `${culture.culture_code} is active again.`
          : `${culture.culture_code} is deactivated. It can no longer be chosen for inoculation; bags made from it still show it.`
      );
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  const speciesById = new Map(species.map((row) => [row.species_id, `${row.name} (${row.code})`]));

  return (
    <>
      <div className="card">
        <h1>Liquid Cultures</h1>
        <p>
          The cultures spawn bags are inoculated from. Record each one once. When a culture is finished or suspect,
          deactivate it: it leaves the pick lists and stays on the bags that were made from it.
        </p>
        {success && <p className="success" role="status">{success}</p>}
        {error && <p className="error" role="alert">{error}</p>}
      </div>

      <div className="card">
        <h2>Add a culture</h2>
        <form className="form stackedForm" onSubmit={onCreate}>
          <label>
            Culture code
            <input value={cultureCode} onChange={(e) => setCultureCode(e.target.value)} required placeholder="LC-LM-261101" />
          </label>
          <label>
            Species
            <select
              value={speciesId}
              onChange={(e) => {
                setSpeciesId(Number(e.target.value) || "");
                setParentId("");
              }}
              required
            >
              <option value="">— Select —</option>
              {species.filter((row) => row.is_active).map((row) => (
                <option key={row.species_id} value={row.species_id}>
                  {row.name} ({row.code})
                </option>
              ))}
            </select>
          </label>
          <div>
            <label>
              Made from
              <select
                value={parentId}
                onChange={(e) => setParentId(Number(e.target.value) || "")}
                aria-describedby="parent-hint"
              >
                <option value="">Not from one of our cultures</option>
                {possibleParents.map((culture) => (
                  <option key={culture.liquid_culture_id} value={culture.liquid_culture_id}>
                    {culture.culture_code}
                  </option>
                ))}
              </select>
            </label>
            <span className="fieldHint" id="parent-hint">
              If this culture was expanded from an earlier one, choose it, so that a problem can be followed back.
            </span>
          </div>
          <label>
            Source
            <input value={source} onChange={(e) => setSource(e.target.value)} placeholder="Supplier, lab, or our own" />
          </label>
          <label>
            Prepared or received
            <input type="datetime-local" value={preparedAt} onChange={(e) => setPreparedAt(e.target.value)} />
          </label>
          <label>
            Notes
            <input value={notes} onChange={(e) => setNotes(e.target.value)} />
          </label>
          <button className="btn btnSolid" type="submit" disabled={busy}>Add liquid culture</button>
        </form>
      </div>

      <div className="card">
        <h2>All cultures</h2>
        {cultures.length === 0 ? (
          <p>None yet.</p>
        ) : (
          <div className="tableWrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Species</th>
                  <th>Made from</th>
                  <th>Source</th>
                  <th>Prepared</th>
                  <th>State</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {cultures.map((culture) => (
                  <tr key={culture.liquid_culture_id} className={culture.is_active ? undefined : "rowInactive"}>
                    <td>
                      {culture.culture_code}
                      {culture.notes && <div className="tableMeta">{culture.notes}</div>}
                    </td>
                    <td>{speciesById.get(culture.species_id) ?? culture.species_id}</td>
                    <td>{culture.parent_culture_code ?? "-"}</td>
                    <td>{culture.source ?? "-"}</td>
                    <td>{culture.prepared_at ? new Date(culture.prepared_at).toLocaleDateString() : "-"}</td>
                    <td>{culture.is_active ? "Active" : "Deactivated"}</td>
                    <td>
                      <button
                        className="btn btnSmall"
                        type="button"
                        disabled={busy}
                        aria-label={`${culture.is_active ? "Deactivate" : "Reactivate"} ${culture.culture_code}`}
                        onClick={() => setActive(culture, !culture.is_active)}
                      >
                        {culture.is_active ? "Deactivate" : "Reactivate"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
