"use client";

import { useEffect, useState } from "react";
import { ApiError, apiGet, apiPatch, apiPost } from "../../lib/api";
import type { GrainType, MushroomSpecies, PurchasedSpawnLot } from "../../lib/types";

function describe(failure: unknown) {
  return failure instanceof ApiError ? failure.message : "That did not work. Try again.";
}

/** Today as the value of a date field, in the browser's own time zone. */
function today() {
  const now = new Date();
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

export default function PurchasedSpawnLotsPage() {
  const [lots, setLots] = useState<PurchasedSpawnLot[]>([]);
  const [species, setSpecies] = useState<MushroomSpecies[]>([]);
  const [grainTypes, setGrainTypes] = useState<GrainType[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [vendor, setVendor] = useState("");
  const [vendorLot, setVendorLot] = useState("");
  const [speciesId, setSpeciesId] = useState<number | "">("");
  const [grainTypeId, setGrainTypeId] = useState<number | "">("");
  const [receivedOn, setReceivedOn] = useState(today());
  const [quantity, setQuantity] = useState("");
  const [quantityUnit, setQuantityUnit] = useState("bags");
  const [notes, setNotes] = useState("");

  async function load() {
    const [lotRows, speciesRows, grainRows] = await Promise.all([
      apiGet<PurchasedSpawnLot[]>("/purchased-spawn-lots"),
      apiGet<MushroomSpecies[]>("/species"),
      apiGet<GrainType[]>("/grain-types"),
    ]);
    setLots(lotRows);
    setSpecies(speciesRows);
    setGrainTypes(grainRows.filter((row) => row.is_active));
  }

  useEffect(() => {
    load().catch((failure) => setError(describe(failure)));
  }, []);

  async function run(action: () => Promise<string>) {
    if (busy) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const done = await action();
      await load();
      setMessage(done);
    } catch (failure) {
      setError(describe(failure));
    } finally {
      setBusy(false);
    }
  }

  function addLot(event: React.FormEvent) {
    event.preventDefault();
    if (speciesId === "") {
      setError("Choose the species.");
      return;
    }
    run(async () => {
      const amount = quantity.trim() ? Number(quantity) : null;
      const created = await apiPost<PurchasedSpawnLot>("/purchased-spawn-lots", {
        vendor: vendor.trim(),
        vendor_lot_number: vendorLot.trim() || null,
        species_id: speciesId,
        grain_type_id: grainTypeId === "" ? null : grainTypeId,
        // Noon on the day chosen, in this device's time zone: the day is what matters.
        received_at: new Date(`${receivedOn}T12:00:00`).toISOString(),
        quantity: amount,
        quantity_unit: amount ? quantityUnit.trim() || null : null,
        notes: notes.trim() || null,
      });
      setVendorLot("");
      setQuantity("");
      setNotes("");
      return `Lot ${created.lot_code} recorded. It can now be chosen when inoculating.`;
    });
  }

  function change(lot: PurchasedSpawnLot, changes: Record<string, unknown>, done: string) {
    run(async () => {
      await apiPatch<PurchasedSpawnLot>(`/purchased-spawn-lots/${lot.purchased_spawn_lot_id}`, changes);
      return done;
    });
  }

  return (
    <div>
      <div className="card">
        <h1>Purchased spawn</h1>
        <p>
          Grain spawn bought from a supplier. Record each lot once when it arrives. It can then be chosen as
          the source every time bags are inoculated from it, until you mark it used up.
        </p>
        {message && <p className="success" role="status">{message}</p>}
        {error && <p className="error" role="alert">{error}</p>}
      </div>

      <div className="card">
        <h2>Record a lot</h2>
        <form className="form stackedForm" onSubmit={addLot}>
          <label>
            Supplier
            <input value={vendor} onChange={(e) => setVendor(e.target.value)} maxLength={160} required />
          </label>
          <label>
            Supplier&apos;s lot number
            <input value={vendorLot} onChange={(e) => setVendorLot(e.target.value)} maxLength={120} />
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
            Grain
            <select value={grainTypeId} onChange={(e) => setGrainTypeId(Number(e.target.value) || "")}>
              <option value="">Not known</option>
              {grainTypes.map((row) => (
                <option key={row.grain_type_id} value={row.grain_type_id}>{row.name}</option>
              ))}
            </select>
          </label>
          <label>
            Date received
            <input type="date" value={receivedOn} max={today()} onChange={(e) => setReceivedOn(e.target.value)} required />
          </label>
          <label>
            Quantity
            <input type="number" min="0" step="any" inputMode="decimal" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
          </label>
          <label>
            Unit
            <select value={quantityUnit} onChange={(e) => setQuantityUnit(e.target.value)}>
              <option value="bags">bags</option>
              <option value="lb">lb</option>
              <option value="kg">kg</option>
            </select>
          </label>
          <label>
            Notes
            <input value={notes} onChange={(e) => setNotes(e.target.value)} />
          </label>
          <button className="btn btnSolid" type="submit" disabled={busy}>Record lot</button>
        </form>
      </div>

      <div className="card">
        <h2>All lots</h2>
        {lots.length === 0 ? (
          <p>No purchased spawn has been recorded yet.</p>
        ) : (
          <div className="tableWrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Lot</th>
                  <th>Species</th>
                  <th>Supplier</th>
                  <th>Received</th>
                  <th>Quantity</th>
                  <th>State</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {lots.map((lot) => {
                  const state = !lot.is_active ? "Deactivated" : lot.is_used_up ? "Used up" : "Open";
                  return (
                    <tr key={lot.purchased_spawn_lot_id}>
                      <td>
                        {lot.lot_code}
                        {lot.notes && <div className="tableMeta">{lot.notes}</div>}
                      </td>
                      <td>
                        {lot.species_name}
                        <div className="tableMeta">{lot.grain_type_name ?? ""}</div>
                      </td>
                      <td>
                        {lot.vendor}
                        <div className="tableMeta">{lot.vendor_lot_number ? `Lot ${lot.vendor_lot_number}` : ""}</div>
                      </td>
                      <td>{new Date(lot.received_at).toLocaleDateString()}</td>
                      <td>{lot.quantity != null ? `${lot.quantity} ${lot.quantity_unit ?? ""}` : "—"}</td>
                      <td>{state}</td>
                      <td>
                        <div className="rowActions">
                          {lot.is_active && (
                            <button
                              type="button"
                              className="btn btnSmall"
                              disabled={busy}
                              onClick={() =>
                                change(
                                  lot,
                                  { used_up: !lot.is_used_up },
                                  lot.is_used_up
                                    ? `Lot ${lot.lot_code} is open again.`
                                    : `Lot ${lot.lot_code} marked used up. It stays on the bags it inoculated.`,
                                )
                              }
                            >
                              {lot.is_used_up ? "Reopen" : "Mark used up"}
                            </button>
                          )}
                          <button
                            type="button"
                            className="btn btnSmall"
                            disabled={busy}
                            onClick={() =>
                              change(
                                lot,
                                { is_active: !lot.is_active },
                                lot.is_active ? `Lot ${lot.lot_code} deactivated.` : `Lot ${lot.lot_code} is active again.`,
                              )
                            }
                          >
                            {lot.is_active ? "Deactivate" : "Reactivate"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
