"use client";

import { useEffect, useState } from "react";
import { ApiError, apiGet, apiPatch, apiPost } from "../../lib/api";
import { useCurrentUser } from "../../lib/session";
import type { MushroomSpecies } from "../../lib/types";

// The farm website's own words for these (docs/research/website-contract-2026-11-11.md).
const TIERS = [
  ["year-round", "Year-round"],
  ["in-rotation-now", "In rotation now"],
  ["returning", "Returning"],
  ["wholesale-only", "Wholesale only"],
  ["functional-coming-later", "Functional, coming later"],
] as const;
const SALE_PATHS = [
  ["available", "Available"],
  ["low-stock", "Low stock"],
  ["sold-out", "Sold out"],
  ["coming-soon", "Coming soon"],
  ["seasonal", "Seasonal harvest"],
  ["preorder", "Preorder"],
  ["hidden", "Hidden"],
  ["wholesale-only", "Wholesale only"],
  ["inquiry-only", "Inquiry only"],
] as const;

type Tier = (typeof TIERS)[number][0];
type SalePath = (typeof SALE_PATHS)[number][0];
type Draft = {
  name: string;
  latin_name: string;
  availability_tier: Tier | "";
  sale_path: SalePath;
  in_rotation_now: boolean;
  restrictions: string;
  notes: string;
};

const label = (pairs: readonly (readonly [string, string])[], value: string | null | undefined) =>
  pairs.find(([key]) => key === value)?.[1] ?? "—";

function describe(failure: unknown) {
  return failure instanceof ApiError ? failure.message : "That did not work. Try again.";
}

export default function SpeciesPage() {
  const me = useCurrentUser();
  const isAdmin = me.role === "admin";
  const [rows, setRows] = useState<MushroomSpecies[]>([]);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [latinName, setLatinName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);

  async function loadAll() {
    setRows(await apiGet<MushroomSpecies[]>("/species?active_only=false"));
  }

  useEffect(() => {
    loadAll().catch((failure) => setError(describe(failure)));
  }, []);

  async function run(action: () => Promise<string>) {
    if (busy) return;
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      const message = await action();
      await loadAll();
      setSuccess(message);
    } catch (failure) {
      setError(describe(failure));
    } finally {
      setBusy(false);
    }
  }

  function onCreate(event: React.FormEvent) {
    event.preventDefault();
    run(async () => {
      const created = await apiPost<MushroomSpecies>("/species", {
        code: code.trim(),
        name: name.trim(),
        latin_name: latinName.trim() || null,
      });
      setCode("");
      setName("");
      setLatinName("");
      return `${created.name} added with code ${created.code}. It is hidden from the website until you choose otherwise.`;
    });
  }

  function startEdit(row: MushroomSpecies) {
    setEditing(row.species_id);
    setDraft({
      name: row.name,
      latin_name: row.latin_name ?? "",
      availability_tier: (row.availability_tier ?? "") as Tier | "",
      sale_path: row.sale_path as SalePath,
      in_rotation_now: row.in_rotation_now,
      restrictions: row.restrictions ?? "",
      notes: row.notes ?? "",
    });
  }

  function saveEdit(event: React.FormEvent, row: MushroomSpecies) {
    event.preventDefault();
    if (!draft) return;
    run(async () => {
      await apiPatch<MushroomSpecies>(`/species/${row.species_id}`, {
        name: draft.name.trim(),
        latin_name: draft.latin_name.trim() || null,
        availability_tier: draft.availability_tier || null,
        sale_path: draft.sale_path,
        in_rotation_now: draft.in_rotation_now,
        restrictions: draft.restrictions.trim() || null,
        notes: draft.notes.trim() || null,
      });
      setEditing(null);
      setDraft(null);
      return `${draft.name.trim()} saved.`;
    });
  }

  function toggleActive(row: MushroomSpecies) {
    run(async () => {
      await apiPatch<MushroomSpecies>(`/species/${row.species_id}`, { is_active: !row.is_active });
      return row.is_active
        ? `${row.name} deactivated. It stays on the records that used it.`
        : `${row.name} is active again.`;
    });
  }

  return (
    <div>
      <div className="card">
        <h1>Species</h1>
        <p>
          The varieties the farm grows. The code is printed in every bag code. The slug is the name the
          farm website knows a variety by and never changes. Growing conditions for each are on the{" "}
          <a href="/reference/species">species reference</a> page.
        </p>
        {success && <p className="success" role="status">{success}</p>}
        {error && <p className="error" role="alert">{error}</p>}
      </div>

      {isAdmin && (
        <div className="card">
          <h2>Add a species</h2>
          <form className="form" onSubmit={onCreate}>
            <label>
              Code
              <input
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                placeholder="e.g. LM"
                pattern="[A-Za-z0-9]{2,3}"
                title="Two or three letters or digits. It is printed in every bag code."
                maxLength={3}
                required
              />
            </label>
            <label>
              Name
              <input value={name} onChange={(e) => setName(e.target.value)} maxLength={120} required />
            </label>
            <label>
              Latin name
              <input value={latinName} onChange={(e) => setLatinName(e.target.value)} />
            </label>
            <button className="btn btnSolid" type="submit" disabled={busy}>Add species</button>
          </form>
        </div>
      )}

      <div className="card">
        <h2>All species</h2>
        <div className="tableWrap">
          <table className="table">
            <thead>
              <tr>
                <th>Code</th>
                <th>Name</th>
                <th>Slug</th>
                <th>Growing now</th>
                <th>Website tier</th>
                <th>Website sale</th>
                <th>Active</th>
                {isAdmin && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.species_id}>
                  <td>{row.code}</td>
                  <td>
                    {row.name}
                    <div className="tableMeta">{row.latin_name ?? ""}</div>
                    {row.restrictions && <div className="tableMeta">Restriction: {row.restrictions}</div>}
                    {editing === row.species_id && draft && (
                      <form className="inlineForm speciesEdit" onSubmit={(event) => saveEdit(event, row)}>
                        <label>
                          Name
                          <input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} maxLength={120} required />
                        </label>
                        <label>
                          Latin name
                          <input value={draft.latin_name} onChange={(e) => setDraft({ ...draft, latin_name: e.target.value })} />
                        </label>
                        <label>
                          Website tier
                          <select
                            value={draft.availability_tier}
                            onChange={(e) => setDraft({ ...draft, availability_tier: e.target.value as Tier | "" })}
                          >
                            <option value="">Not set</option>
                            {TIERS.map(([value, text]) => <option key={value} value={value}>{text}</option>)}
                          </select>
                        </label>
                        <label>
                          Website sale
                          <select
                            value={draft.sale_path}
                            onChange={(e) => setDraft({ ...draft, sale_path: e.target.value as SalePath })}
                          >
                            {SALE_PATHS.map(([value, text]) => <option key={value} value={value}>{text}</option>)}
                          </select>
                        </label>
                        <label className="checkLabel">
                          <input
                            type="checkbox"
                            checked={draft.in_rotation_now}
                            onChange={(e) => setDraft({ ...draft, in_rotation_now: e.target.checked })}
                          />
                          Growing now
                        </label>
                        <label>
                          Restriction
                          <input
                            value={draft.restrictions}
                            onChange={(e) => setDraft({ ...draft, restrictions: e.target.value })}
                            placeholder="e.g. legal-review"
                          />
                        </label>
                        <label>
                          Notes
                          <input value={draft.notes} onChange={(e) => setDraft({ ...draft, notes: e.target.value })} />
                        </label>
                        <button className="btn btnSmall btnSolid" type="submit" disabled={busy}>Save</button>
                        <button className="btn btnSmall" type="button" onClick={() => { setEditing(null); setDraft(null); }}>
                          Cancel
                        </button>
                      </form>
                    )}
                  </td>
                  <td>{row.slug ?? "—"}</td>
                  <td>{row.in_rotation_now ? "Yes" : "No"}</td>
                  <td>{label(TIERS, row.availability_tier)}</td>
                  <td>{label(SALE_PATHS, row.sale_path)}</td>
                  <td>{row.is_active ? "Yes" : "No"}</td>
                  {isAdmin && (
                    <td>
                      <div className="rowActions">
                        {editing !== row.species_id && (
                          <button className="btn btnSmall" type="button" disabled={busy} onClick={() => startEdit(row)}>
                            Edit
                          </button>
                        )}
                        <button className="btn btnSmall" type="button" disabled={busy} onClick={() => toggleActive(row)}>
                          {row.is_active ? "Deactivate" : "Activate"}
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
