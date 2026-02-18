"use client";

import { useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import type { Block, MushroomSpecies } from "../../lib/types";

type BlockTypeFilter = "" | "SPAWN" | "SUBSTRATE";

export default function BlocksPage() {
  const [items, setItems] = useState<Block[]>([]);
  const [speciesRows, setSpeciesRows] = useState<MushroomSpecies[]>([]);
  const [blockType, setBlockType] = useState<BlockTypeFilter>("");
  const [error, setError] = useState<string | null>(null);

  async function refresh(nextType: BlockTypeFilter = blockType) {
    const qs = new URLSearchParams();
    if (nextType) qs.set("block_type", nextType);
    qs.set("limit", "500");
    const data = await apiGet<Block[]>(`/blocks?${qs.toString()}`);
    setItems(data);
  }

  useEffect(() => {
    Promise.all([
      refresh(),
      apiGet<MushroomSpecies[]>("/species?active_only=false").then(setSpeciesRows),
    ]).catch((e) => setError(e?.message || String(e)));
  }, []);

  const speciesNameById = Object.fromEntries(speciesRows.map((s) => [s.species_id, `${s.code} - ${s.name}`]));

  return (
    <div className="card">
      <h1>Blocks</h1>
      <div className="form">
        <label>
          Filter Type
          <select
            value={blockType}
            onChange={(e) => {
              const v = e.target.value as BlockTypeFilter;
              setBlockType(v);
              refresh(v).catch((err) => setError(err?.message || String(err)));
            }}
          >
            <option value="">All</option>
            <option value="SPAWN">SPAWN</option>
            <option value="SUBSTRATE">SUBSTRATE</option>
          </select>
        </label>
      </div>

      <table className="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Code</th>
            <th>Type</th>
            <th>Species</th>
            <th>Mix Lot</th>
            <th>Pasteurization Run</th>
            <th>Sterilization Run</th>
            <th>Spawn Recipe</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {items.map((b) => (
            <tr key={b.block_id}>
              <td>{b.block_id}</td>
              <td><a href={`/blocks/${b.block_id}`}>{b.block_code}</a></td>
              <td>{b.block_type}</td>
              <td>{speciesNameById[b.species_id] ?? b.species_id}</td>
              <td>{b.mix_lot_id ?? ""}</td>
              <td>{b.pasteurization_run_id ?? ""}</td>
              <td>{b.sterilization_run_id ?? ""}</td>
              <td>{b.spawn_recipe_id ?? ""}</td>
              <td>{new Date(b.created_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {error && <p className="error">{error}</p>}
    </div>
  );
}
