"use client";

import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPatch, apiPost } from "../../lib/api";
import type { SterilizationRun } from "../../lib/types";

function toIsoOrNull(value: string): string | null {
  if (!value) return null;
  return new Date(value).toISOString();
}

function toLocalInputValue(value?: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  const offsetMs = date.getTimezoneOffset() * 60 * 1000;
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16);
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

export default function SterilizationRunsPage() {
  const [runs, setRuns] = useState<SterilizationRun[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [filterRunCodeContains, setFilterRunCodeContains] = useState("");
  const [filterUnloadedFrom, setFilterUnloadedFrom] = useState("");
  const [filterUnloadedTo, setFilterUnloadedTo] = useState("");
  const [sortBy, setSortBy] = useState<"sterilization_run_id" | "run_code" | "unloaded_at">("sterilization_run_id");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  const [createRunCode, setCreateRunCode] = useState("");
  const [createCycleStart, setCreateCycleStart] = useState("");
  const [createCycleEnd, setCreateCycleEnd] = useState("");
  const [createUnloadedAt, setCreateUnloadedAt] = useState("");
  const [createTempC, setCreateTempC] = useState("");
  const [createPsi, setCreatePsi] = useState("");
  const [createHoldMinutes, setCreateHoldMinutes] = useState("");
  const [createNotes, setCreateNotes] = useState("");

  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const selectedRun = useMemo(
    () => runs.find((r) => r.sterilization_run_id === selectedRunId) || null,
    [runs, selectedRunId]
  );
  const [editCycleStart, setEditCycleStart] = useState("");
  const [editCycleEnd, setEditCycleEnd] = useState("");
  const [editUnloadedAt, setEditUnloadedAt] = useState("");
  const [editTempC, setEditTempC] = useState("");
  const [editPsi, setEditPsi] = useState("");
  const [editHoldMinutes, setEditHoldMinutes] = useState("");
  const [editNotes, setEditNotes] = useState("");

  async function loadRuns() {
    const params = new URLSearchParams();
    if (filterRunCodeContains.trim()) params.set("run_code_contains", filterRunCodeContains.trim());
    if (filterUnloadedFrom) params.set("unloaded_from", new Date(filterUnloadedFrom).toISOString());
    if (filterUnloadedTo) params.set("unloaded_to", new Date(filterUnloadedTo).toISOString());
    params.set("sort_by", sortBy);
    params.set("sort_order", sortOrder);
    const data = await apiGet<SterilizationRun[]>(`/sterilization-runs?${params.toString()}`);
    setRuns(data);
    if (!selectedRunId && data.length > 0) setSelectedRunId(data[0].sterilization_run_id);
  }

  useEffect(() => {
    loadRuns().catch((e) => setError(String(e)));
  }, [filterRunCodeContains, filterUnloadedFrom, filterUnloadedTo, sortBy, sortOrder]);

  useEffect(() => {
    if (!selectedRun) return;
    setEditCycleStart(toLocalInputValue(selectedRun.cycle_start_at));
    setEditCycleEnd(toLocalInputValue(selectedRun.cycle_end_at));
    setEditUnloadedAt(toLocalInputValue(selectedRun.unloaded_at));
    setEditTempC(selectedRun.temp_c == null ? "" : String(selectedRun.temp_c));
    setEditPsi(selectedRun.psi == null ? "" : String(selectedRun.psi));
    setEditHoldMinutes(selectedRun.hold_minutes == null ? "" : String(selectedRun.hold_minutes));
    setEditNotes(selectedRun.notes || "");
  }, [selectedRun]);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await apiPost<SterilizationRun>("/sterilization-runs", {
        run_code: createRunCode.trim(),
        cycle_start_at: toIsoOrNull(createCycleStart),
        cycle_end_at: toIsoOrNull(createCycleEnd),
        unloaded_at: new Date(createUnloadedAt).toISOString(),
        temp_c: toNullableNumber(createTempC),
        psi: toNullableNumber(createPsi),
        hold_minutes: toNullableInt(createHoldMinutes),
        notes: createNotes.trim() || null,
      });
      setCreateRunCode("");
      setCreateCycleStart("");
      setCreateCycleEnd("");
      setCreateUnloadedAt("");
      setCreateTempC("");
      setCreatePsi("");
      setCreateHoldMinutes("");
      setCreateNotes("");
      await loadRuns();
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  async function onUpdate(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedRun) return;
    setError(null);
    try {
      await apiPatch<SterilizationRun>(`/sterilization-runs/${selectedRun.sterilization_run_id}`, {
        cycle_start_at: toIsoOrNull(editCycleStart),
        cycle_end_at: toIsoOrNull(editCycleEnd),
        unloaded_at: editUnloadedAt ? new Date(editUnloadedAt).toISOString() : null,
        temp_c: toNullableNumber(editTempC),
        psi: toNullableNumber(editPsi),
        hold_minutes: toNullableInt(editHoldMinutes),
        notes: editNotes.trim() || null,
      });
      await loadRuns();
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  return (
    <div>
      <div className="card">
        <h1>Sterilization Runs (Autoclave)</h1>
        <h2>Filter + Sort</h2>
        <div className="form">
          <label>
            Run code contains
            <input value={filterRunCodeContains} onChange={(e) => setFilterRunCodeContains(e.target.value)} />
          </label>
          <label>
            Unloaded from
            <input type="datetime-local" value={filterUnloadedFrom} onChange={(e) => setFilterUnloadedFrom(e.target.value)} />
          </label>
          <label>
            Unloaded to
            <input type="datetime-local" value={filterUnloadedTo} onChange={(e) => setFilterUnloadedTo(e.target.value)} />
          </label>
          <label>
            Sort by
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value as "sterilization_run_id" | "run_code" | "unloaded_at")}>
              <option value="sterilization_run_id">ID</option>
              <option value="run_code">Run Code</option>
              <option value="unloaded_at">Unloaded At</option>
            </select>
          </label>
          <label>
            Sort order
            <select value={sortOrder} onChange={(e) => setSortOrder(e.target.value as "asc" | "desc")}>
              <option value="desc">desc</option>
              <option value="asc">asc</option>
            </select>
          </label>
        </div>

        <form onSubmit={onCreate} className="form">
          <label>
            Run Code
            <input
              value={createRunCode}
              onChange={(e) => setCreateRunCode(e.target.value)}
              placeholder="e.g., AUTO-2026-02-15-A"
              required
            />
          </label>
          <label>
            Cycle Start (optional)
            <input type="datetime-local" value={createCycleStart} onChange={(e) => setCreateCycleStart(e.target.value)} />
          </label>
          <label>
            Cycle End (optional)
            <input type="datetime-local" value={createCycleEnd} onChange={(e) => setCreateCycleEnd(e.target.value)} />
          </label>
          <label>
            Unloaded At
            <input type="datetime-local" value={createUnloadedAt} onChange={(e) => setCreateUnloadedAt(e.target.value)} required />
          </label>
          <label>
            Temp C (optional)
            <input type="number" step="0.01" value={createTempC} onChange={(e) => setCreateTempC(e.target.value)} />
          </label>
          <label>
            PSI (optional)
            <input type="number" step="0.01" value={createPsi} onChange={(e) => setCreatePsi(e.target.value)} />
          </label>
          <label>
            Hold Minutes (optional)
            <input type="number" step="1" min="0" value={createHoldMinutes} onChange={(e) => setCreateHoldMinutes(e.target.value)} />
          </label>
          <label>
            Notes
            <input value={createNotes} onChange={(e) => setCreateNotes(e.target.value)} />
          </label>
          <button className="btn" type="submit">Create Run</button>
        </form>
      </div>

      <div className="card">
        <h2>All Runs</h2>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Run Code</th>
              <th>Unloaded At</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr
                key={run.sterilization_run_id}
                onClick={() => setSelectedRunId(run.sterilization_run_id)}
                style={{ cursor: "pointer", background: selectedRunId === run.sterilization_run_id ? "#f2f7ff" : "transparent" }}
              >
                <td>{run.sterilization_run_id}</td>
                <td>{run.run_code}</td>
                <td>{new Date(run.unloaded_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selectedRun && (
        <div className="card">
          <h2>Edit Selected Run: {selectedRun.run_code}</h2>
          <form onSubmit={onUpdate} className="form">
            <label>
              Cycle Start
              <input type="datetime-local" value={editCycleStart} onChange={(e) => setEditCycleStart(e.target.value)} />
            </label>
            <label>
              Cycle End
              <input type="datetime-local" value={editCycleEnd} onChange={(e) => setEditCycleEnd(e.target.value)} />
            </label>
            <label>
              Unloaded At
              <input type="datetime-local" value={editUnloadedAt} onChange={(e) => setEditUnloadedAt(e.target.value)} />
            </label>
            <label>
              Temp C
              <input type="number" step="0.01" value={editTempC} onChange={(e) => setEditTempC(e.target.value)} />
            </label>
            <label>
              PSI
              <input type="number" step="0.01" value={editPsi} onChange={(e) => setEditPsi(e.target.value)} />
            </label>
            <label>
              Hold Minutes
              <input type="number" step="1" min="0" value={editHoldMinutes} onChange={(e) => setEditHoldMinutes(e.target.value)} />
            </label>
            <label>
              Notes
              <input value={editNotes} onChange={(e) => setEditNotes(e.target.value)} />
            </label>
            <button className="btn" type="submit">Update Run</button>
          </form>
        </div>
      )}

      {error && <p className="error">{error}</p>}
    </div>
  );
}
