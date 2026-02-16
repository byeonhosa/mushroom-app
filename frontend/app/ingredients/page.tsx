"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../../lib/api";
import type { Ingredient, IngredientLot } from "../../lib/types";

type IngredientForm = {
  name: string;
  category: string;
  notes: string;
};

type IngredientLotForm = {
  ingredient_id: string;
  vendor: string;
  lot_code: string;
  received_at: string;
  unit_cost_per_kg: string;
  notes: string;
};

const emptyIngredientForm: IngredientForm = { name: "", category: "", notes: "" };
const emptyIngredientLotForm: IngredientLotForm = {
  ingredient_id: "",
  vendor: "",
  lot_code: "",
  received_at: "",
  unit_cost_per_kg: "",
  notes: "",
};

function toNumberOrNull(raw: string): number | null {
  if (!raw.trim()) return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

export default function IngredientsPage() {
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [lots, setLots] = useState<IngredientLot[]>([]);
  const [ingredientForm, setIngredientForm] = useState<IngredientForm>(emptyIngredientForm);
  const [lotForm, setLotForm] = useState<IngredientLotForm>(emptyIngredientLotForm);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    const [ingredientRes, lotRes] = await Promise.all([
      apiGet<Ingredient[]>("/ingredients"),
      apiGet<IngredientLot[]>("/ingredient-lots"),
    ]);
    setIngredients(ingredientRes);
    setLots(lotRes);
  }

  useEffect(() => {
    refresh().catch((e) => setError(String(e)));
  }, []);

  async function onCreateIngredient(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await apiPost<Ingredient>("/ingredients", {
        name: ingredientForm.name.trim(),
        category: ingredientForm.category.trim() || null,
        notes: ingredientForm.notes.trim() || null,
      });
      setIngredientForm(emptyIngredientForm);
      await refresh();
    } catch (err: any) {
      setError(err?.message || String(err));
    }
  }

  async function onCreateLot(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await apiPost<IngredientLot>("/ingredient-lots", {
        ingredient_id: Number(lotForm.ingredient_id),
        vendor: lotForm.vendor.trim() || null,
        lot_code: lotForm.lot_code.trim() || null,
        received_at: lotForm.received_at ? new Date(lotForm.received_at).toISOString() : null,
        unit_cost_per_kg: toNumberOrNull(lotForm.unit_cost_per_kg),
        notes: lotForm.notes.trim() || null,
      });
      setLotForm((p) => ({ ...emptyIngredientLotForm, ingredient_id: p.ingredient_id }));
      await refresh();
    } catch (err: any) {
      setError(err?.message || String(err));
    }
  }

  return (
    <div className="card">
      <h1>Ingredients</h1>

      <h2>Create Ingredient</h2>
      <form className="form" onSubmit={onCreateIngredient}>
        <label>
          Name
          <input
            required
            value={ingredientForm.name}
            onChange={(e) => setIngredientForm((p) => ({ ...p, name: e.target.value }))}
          />
        </label>
        <label>
          Category
          <input
            value={ingredientForm.category}
            onChange={(e) => setIngredientForm((p) => ({ ...p, category: e.target.value }))}
          />
        </label>
        <label>
          Notes
          <input
            value={ingredientForm.notes}
            onChange={(e) => setIngredientForm((p) => ({ ...p, notes: e.target.value }))}
          />
        </label>
        <button className="btn" type="submit">Create Ingredient</button>
      </form>

      <h2>Ingredient Lots</h2>
      <form className="form" onSubmit={onCreateLot}>
        <label>
          Ingredient
          <select
            required
            value={lotForm.ingredient_id}
            onChange={(e) => setLotForm((p) => ({ ...p, ingredient_id: e.target.value }))}
          >
            <option value="">Select ingredient...</option>
            {ingredients.map((ingredient) => (
              <option key={ingredient.ingredient_id} value={ingredient.ingredient_id}>
                {ingredient.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Vendor
          <input value={lotForm.vendor} onChange={(e) => setLotForm((p) => ({ ...p, vendor: e.target.value }))} />
        </label>
        <label>
          Lot Code
          <input value={lotForm.lot_code} onChange={(e) => setLotForm((p) => ({ ...p, lot_code: e.target.value }))} />
        </label>
        <label>
          Received At
          <input
            type="datetime-local"
            value={lotForm.received_at}
            onChange={(e) => setLotForm((p) => ({ ...p, received_at: e.target.value }))}
          />
        </label>
        <label>
          Unit Cost Per kg
          <input
            type="number"
            step="0.0001"
            min="0"
            value={lotForm.unit_cost_per_kg}
            onChange={(e) => setLotForm((p) => ({ ...p, unit_cost_per_kg: e.target.value }))}
          />
        </label>
        <label>
          Notes
          <input value={lotForm.notes} onChange={(e) => setLotForm((p) => ({ ...p, notes: e.target.value }))} />
        </label>
        <button className="btn" type="submit">Create Ingredient Lot</button>
      </form>

      <h2>Ingredients List</h2>
      <table className="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Category</th>
            <th>Notes</th>
          </tr>
        </thead>
        <tbody>
          {ingredients.map((item) => (
            <tr key={item.ingredient_id}>
              <td>{item.ingredient_id}</td>
              <td>{item.name}</td>
              <td>{item.category ?? ""}</td>
              <td>{item.notes ?? ""}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Lots List</h2>
      <table className="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Ingredient</th>
            <th>Vendor</th>
            <th>Lot Code</th>
            <th>Received At</th>
            <th>Unit Cost/kg</th>
            <th>Notes</th>
          </tr>
        </thead>
        <tbody>
          {lots.map((item) => (
            <tr key={item.ingredient_lot_id}>
              <td>{item.ingredient_lot_id}</td>
              <td>{item.ingredient?.name ?? `#${item.ingredient_id}`}</td>
              <td>{item.vendor ?? ""}</td>
              <td>{item.lot_code ?? ""}</td>
              <td>{item.received_at ? new Date(item.received_at).toLocaleString() : ""}</td>
              <td>{item.unit_cost_per_kg == null ? "" : item.unit_cost_per_kg.toFixed(4)}</td>
              <td>{item.notes ?? ""}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {error && <p className="error">{error}</p>}
    </div>
  );
}
