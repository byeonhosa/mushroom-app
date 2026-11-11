"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPost } from "../../lib/api";
import { ReferenceList } from "../../lib/reference-list";
import { useCurrentUser } from "../../lib/session";
import type { Ingredient, IngredientLot } from "../../lib/types";

type LotForm = {
  ingredient_id: string;
  vendor: string;
  lot_code: string;
  received_at: string;
  notes: string;
};

const emptyLotForm: LotForm = { ingredient_id: "", vendor: "", lot_code: "", received_at: "", notes: "" };

export default function IngredientsPage() {
  const canEdit = useCurrentUser().role === "admin";
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [lots, setLots] = useState<IngredientLot[]>([]);
  const [lotForm, setLotForm] = useState<LotForm>(emptyLotForm);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [ingredientRows, lotRows] = await Promise.all([
      apiGet<Ingredient[]>("/ingredients"),
      apiGet<IngredientLot[]>("/ingredient-lots"),
    ]);
    setIngredients(ingredientRows);
    setLots(lotRows);
  }, []);

  useEffect(() => {
    refresh().catch((e) => setError(e?.message || String(e)));
  }, [refresh]);

  const nameById = new Map(ingredients.map((ingredient) => [ingredient.ingredient_id, ingredient.name]));
  // A deactivated ingredient keeps its lots on the list and takes no new ones.
  const usable = ingredients.filter((ingredient) => ingredient.is_active);

  async function addLot(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setBusy(true);
    try {
      await apiPost<IngredientLot>("/ingredient-lots", {
        ingredient_id: Number(lotForm.ingredient_id),
        vendor: lotForm.vendor.trim() || null,
        lot_code: lotForm.lot_code.trim() || null,
        received_at: lotForm.received_at ? new Date(lotForm.received_at).toISOString() : null,
        notes: lotForm.notes.trim() || null,
      });
      setLotForm((current) => ({ ...emptyLotForm, ingredient_id: current.ingredient_id }));
      await refresh();
      setMessage("Ingredient lot recorded.");
    } catch (err: any) {
      setError(err?.message || String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="card">
        <h1>Ingredients</h1>
        <p>
          What substrate is mixed from, and the deliveries of each. Recording these is optional: a mix lot does not
          need them.
          {!canEdit && " Only an administrator can change the list of ingredients."}
        </p>
      </div>

      <ReferenceList
        title="Ingredient list"
        path="/ingredients"
        idKey="ingredient_id"
        noun="ingredient"
        canEdit={canEdit}
        onChanged={() => void refresh()}
        fields={[
          { key: "name", label: "Name", required: true, placeholder: "Soy hulls" },
          { key: "category", label: "Category", placeholder: "Supplement" },
          { key: "notes", label: "Notes" },
        ]}
      />

      <section className="card" aria-label="Ingredient lots">
        <h2>Ingredient lots</h2>
        <p>One delivery of one ingredient.</p>
        {message && <p className="success" role="status">{message}</p>}
        {error && <p className="error" role="alert">{error}</p>}

        {lots.length === 0 ? (
          <p>None yet.</p>
        ) : (
          <div className="tableWrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Ingredient</th>
                  <th>Supplier</th>
                  <th>Lot code</th>
                  <th>Received</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {lots.map((lot) => (
                  <tr key={lot.ingredient_lot_id}>
                    <td>{nameById.get(lot.ingredient_id) ?? `#${lot.ingredient_id}`}</td>
                    <td>{lot.vendor ?? "-"}</td>
                    <td>{lot.lot_code ?? "-"}</td>
                    <td>{lot.received_at ? new Date(lot.received_at).toLocaleDateString() : "-"}</td>
                    <td>{lot.notes ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <form className="form stackedForm" onSubmit={addLot}>
          <h3>Record a lot</h3>
          <label>
            Ingredient
            <select
              required
              value={lotForm.ingredient_id}
              onChange={(e) => setLotForm((current) => ({ ...current, ingredient_id: e.target.value }))}
            >
              <option value="">— Select —</option>
              {usable.map((ingredient) => (
                <option key={ingredient.ingredient_id} value={ingredient.ingredient_id}>
                  {ingredient.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Supplier
            <input value={lotForm.vendor} onChange={(e) => setLotForm((current) => ({ ...current, vendor: e.target.value }))} />
          </label>
          <label>
            Supplier's lot code
            <input value={lotForm.lot_code} onChange={(e) => setLotForm((current) => ({ ...current, lot_code: e.target.value }))} />
          </label>
          <label>
            Received
            <input
              type="datetime-local"
              value={lotForm.received_at}
              onChange={(e) => setLotForm((current) => ({ ...current, received_at: e.target.value }))}
            />
          </label>
          <label>
            Notes
            <input value={lotForm.notes} onChange={(e) => setLotForm((current) => ({ ...current, notes: e.target.value }))} />
          </label>
          <button className="btn btnSolid" type="submit" disabled={busy}>Record ingredient lot</button>
        </form>
      </section>
    </>
  );
}
