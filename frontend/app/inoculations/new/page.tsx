"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../../../lib/api";
import type { Block, Inoculation } from "../../../lib/types";

export default function NewInoculationPage() {
  const [spawnBlocks, setSpawnBlocks] = useState<Block[]>([]);
  const [substrateBlocks, setSubstrateBlocks] = useState<Block[]>([]);
  const [parentSpawnBlockId, setParentSpawnBlockId] = useState("");
  const [childBlockId, setChildBlockId] = useState("");
  const [notes, setNotes] = useState("");
  const [created, setCreated] = useState<Inoculation | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      apiGet<Block[]>("/blocks?block_type=SPAWN&limit=500"),
      apiGet<Block[]>("/blocks?block_type=SUBSTRATE&limit=500"),
    ])
      .then(([spawnRows, subRows]) => {
        setSpawnBlocks(spawnRows);
        setSubstrateBlocks(subRows);
        if (spawnRows[0]) setParentSpawnBlockId(String(spawnRows[0].block_id));
        if (subRows[0]) setChildBlockId(String(subRows[0].block_id));
      })
      .catch((e) => setError(e?.message || String(e)));
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setCreated(null);
    try {
      const row = await apiPost<Inoculation>("/inoculations", {
        child_block_id: Number(childBlockId),
        parent_spawn_block_id: Number(parentSpawnBlockId),
        notes: notes.trim() || null,
      });
      setCreated(row);
      setNotes("");
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  return (
    <div className="card">
      <h1>New Inoculation</h1>
      {created && (
        <p style={{ background: "#e9f8ed", border: "1px solid #9fd3ab", padding: 10, borderRadius: 8 }}>
          Inoculation saved. Parent <a href={`/blocks/${created.parent_spawn_block_id}`}>{created.parent_spawn_block_code || created.parent_spawn_block_id}</a>{" "}
          → Child <a href={`/blocks/${created.child_block_id}`}>{created.child_block_code || created.child_block_id}</a>
        </p>
      )}
      {error && <p className="error">{error}</p>}
      <form className="form" onSubmit={onSubmit}>
        <label>
          Parent Spawn Block
          <select value={parentSpawnBlockId} onChange={(e) => setParentSpawnBlockId(e.target.value)} required>
            <option value="">Select spawn block...</option>
            {spawnBlocks.map((b) => <option key={b.block_id} value={b.block_id}>{b.block_code}</option>)}
          </select>
        </label>
        <label>
          Child Substrate Block
          <select value={childBlockId} onChange={(e) => setChildBlockId(e.target.value)} required>
            <option value="">Select substrate block...</option>
            {substrateBlocks.map((b) => <option key={b.block_id} value={b.block_id}>{b.block_code}</option>)}
          </select>
        </label>
        <label>
          Notes
          <input value={notes} onChange={(e) => setNotes(e.target.value)} />
        </label>
        <button className="btn" type="submit">Record Inoculation</button>
      </form>
    </div>
  );
}
