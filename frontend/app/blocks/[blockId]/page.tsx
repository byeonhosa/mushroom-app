"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiGet } from "../../../lib/api";
import type { Block, HarvestEvent, Inoculation, MushroomSpecies } from "../../../lib/types";

export default function BlockDetailPage() {
  const params = useParams();
  const blockId = typeof params?.blockId === "string" ? params.blockId : Array.isArray(params?.blockId) ? params?.blockId[0] : "";
  const [block, setBlock] = useState<Block | null>(null);
  const [speciesRows, setSpeciesRows] = useState<MushroomSpecies[]>([]);
  const [inoculation, setInoculation] = useState<Inoculation | null>(null);
  const [harvestEvents, setHarvestEvents] = useState<HarvestEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!blockId) return;
    (async () => {
      try {
        const row = await apiGet<Block>(`/blocks/${blockId}`);
        setBlock(row);
        const allSpecies = await apiGet<MushroomSpecies[]>("/species?active_only=false");
        setSpeciesRows(allSpecies);
        if (row?.block_type === "SUBSTRATE") {
          try {
            const inoc = await apiGet<Inoculation>(`/blocks/${blockId}/inoculation`);
            setInoculation(inoc);
          } catch {
            setInoculation(null);
          }
          const events = await apiGet<HarvestEvent[]>(`/blocks/${blockId}/harvest-events`);
          setHarvestEvents(events);
        }
      } catch (e: any) {
        setError(e?.message || String(e));
      }
    })();
  }, [blockId]);

  return (
    <div className="card">
      <h1>Block {blockId}</h1>
      {error && <p className="error">{error}</p>}
      {!block ? (
        <p>Loading...</p>
      ) : (
        <>
          <p><strong>Code:</strong> {block.block_code}</p>
          <p><strong>Type:</strong> {block.block_type}</p>
          <p><strong>Species:</strong> {speciesRows.find((s) => s.species_id === block.species_id)?.name ?? block.species_id}</p>
          <p><strong>Mix Lot:</strong> {block.mix_lot_id ?? ""}</p>
          <p><strong>Pasteurization Run:</strong> {block.pasteurization_run_id ?? ""}</p>
          <p><strong>Sterilization Run:</strong> {block.sterilization_run_id ?? ""}</p>
          <p><strong>Spawn Recipe ID:</strong> {block.spawn_recipe_id ?? ""}</p>
          <p><strong>Status:</strong> {block.status ?? ""}</p>
          <p><strong>Notes:</strong> {block.notes ?? ""}</p>
          {block.block_type === "SUBSTRATE" && (
            <>
              <h2>Inoculation</h2>
              {!inoculation ? <p>No inoculation record.</p> : <p>Parent spawn block: {inoculation.parent_spawn_block_code || inoculation.parent_spawn_block_id}</p>}
              <h2>Harvest Events</h2>
              <a className="btn" href="/harvest/new">Add Harvest</a>
              <table className="table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Flush</th>
                    <th>Weight (kg)</th>
                    <th>Harvested At</th>
                    <th>Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {harvestEvents.map((h) => (
                    <tr key={h.harvest_event_id}>
                      <td>{h.harvest_event_id}</td>
                      <td>{h.flush_number}</td>
                      <td>{h.fresh_weight_kg}</td>
                      <td>{new Date(h.harvested_at).toLocaleString()}</td>
                      <td>{h.notes ?? ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </>
      )}
    </div>
  );
}
