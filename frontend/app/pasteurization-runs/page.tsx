"use client";

import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPatch, apiPost } from "../../lib/api";
import type { PasteurizationRun } from "../../lib/types";

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

export default function PasteurizationRunsPage() {
  const [runs, setRuns] = useState<PasteurizationRun[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [createRunCode, setCreateRunCode] = useState("");
  const [createSteamStart, setCreateSteamStart] = useState("");
  const [createSteamEnd, setCreateSteamEnd] = useState("");
  const [createUnloadedAt, setCreateUnloadedAt] = useState("");
  const [createNotes, setCreateNotes] = useState("");

  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const selectedRun = useMemo(
    () => runs.find(r => r.pasteurization_run_id === selectedRunId) || null,
    [runs, selectedRunId]
  );
  const [editSteamStart, setEditSteamStart] = useState("");
  const [editSteamEnd, setEditSteamEnd] = useState("");
  const [editUnloadedAt, setEditUnloadedAt] = useState("");
  const [editNotes, setEditNotes] = useState("");

  async function loadRuns() {
    const data = await apiGet<PasteurizationRun[]>("/pasteurization-runs");
    setRuns(data);
    if (!selectedRunId && data.length > 0) setSelectedRunId(data[0].pasteurization_run_id);
  }

  useEffect(() => {
    loadRuns().catch(e => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!selectedRun) return;
    setEditSteamStart(toLocalInputValue(selectedRun.steam_start_at));
    setEditSteamEnd(toLocalInputValue(selectedRun.steam_end_at));
    setEditUnloadedAt(toLocalInputValue(selectedRun.unloaded_at));
    setEditNotes(selectedRun.notes || "");
  }, [selectedRun]);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await apiPost<PasteurizationRun>("/pasteurization-runs", {
        run_code: createRunCode,
        steam_start_at: toIsoOrNull(createSteamStart),
        steam_end_at: toIsoOrNull(createSteamEnd),
        unloaded_at: new Date(createUnloadedAt).toISOString(),
        notes: createNotes || null
      });
      setCreateRunCode("");
      setCreateSteamStart("");
      setCreateSteamEnd("");
      setCreateUnloadedAt("");
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
      await apiPatch<PasteurizationRun>(`/pasteurization-runs/${selectedRun.pasteurization_run_id}`, {
        steam_start_at: toIsoOrNull(editSteamStart),
        steam_end_at: toIsoOrNull(editSteamEnd),
        unloaded_at: editUnloadedAt ? new Date(editUnloadedAt).toISOString() : null,
        notes: editNotes || null
      });
      await loadRuns();
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  return (
    <div>
      <div className="card">
        <h1>Pasteurization Runs (Steam)</h1>
        <form onSubmit={onCreate} className="form">
          <label>
            Run Code
            <input value={createRunCode} onChange={e => setCreateRunCode(e.target.value)} placeholder="e.g., PS-2026-02-15-A" required />
          </label>
          <label>
            Steam Start (optional)
            <input type="datetime-local" value={createSteamStart} onChange={e => setCreateSteamStart(e.target.value)} />
          </label>
          <label>
            Steam End (optional)
            <input type="datetime-local" value={createSteamEnd} onChange={e => setCreateSteamEnd(e.target.value)} />
          </label>
          <label>
            Unloaded At
            <input type="datetime-local" value={createUnloadedAt} onChange={e => setCreateUnloadedAt(e.target.value)} required />
          </label>
          <label>
            Notes
            <input value={createNotes} onChange={e => setCreateNotes(e.target.value)} />
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
            {runs.map(run => (
              <tr
                key={run.pasteurization_run_id}
                onClick={() => setSelectedRunId(run.pasteurization_run_id)}
                style={{ cursor: "pointer", background: selectedRunId === run.pasteurization_run_id ? "#f2f7ff" : "transparent" }}
              >
                <td>{run.pasteurization_run_id}</td>
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
              Steam Start
              <input type="datetime-local" value={editSteamStart} onChange={e => setEditSteamStart(e.target.value)} />
            </label>
            <label>
              Steam End
              <input type="datetime-local" value={editSteamEnd} onChange={e => setEditSteamEnd(e.target.value)} />
            </label>
            <label>
              Unloaded At
              <input type="datetime-local" value={editUnloadedAt} onChange={e => setEditUnloadedAt(e.target.value)} />
            </label>
            <label>
              Notes
              <input value={editNotes} onChange={e => setEditNotes(e.target.value)} />
            </label>
            <button className="btn" type="submit">Update Run</button>
          </form>
        </div>
      )}

      {error && <p className="error">{error}</p>}
    </div>
  );
}
