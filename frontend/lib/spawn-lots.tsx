"use client";

import { useEffect, useState } from "react";
import { apiGet } from "./api";
import type { PurchasedSpawnLot } from "./types";

/** How a lot reads in a list: its code, what it is, and who sold it. */
export function lotLabel(lot: PurchasedSpawnLot): string {
  return `${lot.lot_code} · ${lot.species_name ?? "?"} · ${lot.vendor}`;
}

/** Purchased spawn lots that can inoculate now: active and not marked used up. */
export function useUsableSpawnLots(refreshKey: number = 0) {
  const [lots, setLots] = useState<PurchasedSpawnLot[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    apiGet<PurchasedSpawnLot[]>("/purchased-spawn-lots?usable_only=true")
      .then((rows) => {
        if (!cancelled) {
          setLots(rows);
          setLoaded(true);
        }
      })
      .catch(() => {
        if (!cancelled) setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  return { lots, loaded };
}

export type SubstrateSource = "PURCHASED_SPAWN" | "SPAWN_BAG";

/**
 * The two fields that say where the grain came from when substrate is
 * inoculated: which kind of source, and which lot or spawn bag (SRS INO-3,
 * INO-6). Used on the inoculation screen and on the pasteurization run page.
 */
export function SubstrateSourceFields(props: {
  source: SubstrateSource;
  onSourceChange: (source: SubstrateSource) => void;
  lots: PurchasedSpawnLot[];
  lotId: number | "";
  onLotChange: (lotId: number | "") => void;
  spawnBagRef: string;
  onSpawnBagChange: (ref: string) => void;
  spawnBagListId?: string;
}) {
  return (
    <>
      <label>
        Inoculated from
        <select value={props.source} onChange={(e) => props.onSourceChange(e.target.value as SubstrateSource)}>
          <option value="PURCHASED_SPAWN">Purchased spawn lot</option>
          <option value="SPAWN_BAG">One of our own spawn bags</option>
        </select>
      </label>
      {props.source === "PURCHASED_SPAWN" ? (
        <label>
          Purchased spawn lot
          <select value={props.lotId} onChange={(e) => props.onLotChange(Number(e.target.value) || "")} required>
            <option value="">— Select —</option>
            {props.lots.map((lot) => (
              <option key={lot.purchased_spawn_lot_id} value={lot.purchased_spawn_lot_id}>
                {lotLabel(lot)}
              </option>
            ))}
          </select>
          {props.lots.length === 0 && (
            <span className="fieldHint">
              No purchased spawn lot is open. <a href="/purchased-spawn-lots">Record the lot</a> first.
            </span>
          )}
        </label>
      ) : (
        <label>
          Ready spawn bag code
          <input
            list={props.spawnBagListId}
            value={props.spawnBagRef}
            onChange={(e) => props.onSpawnBagChange(e.target.value)}
            placeholder="e.g. SP-LM-261109A-01"
          />
        </label>
      )}
    </>
  );
}
