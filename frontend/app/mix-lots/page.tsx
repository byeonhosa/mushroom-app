"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../../lib/api";
import type { MixLot, SubstrateRecipeVersion, FillProfile } from "../../lib/types";

export default function MixLotsPage() {
  const [lots, setLots] = useState<MixLot[]>([]);
  const [recipes, setRecipes] = useState<SubstrateRecipeVersion[]>([]);
  const [profiles, setProfiles] = useState<FillProfile[]>([]);
  const [lotCode, setLotCode] = useState("");
  const [recipeId, setRecipeId] = useState<number | "">("");
  const [profileId, setProfileId] = useState<number | "">("");
  const [error, setError] = useState<string | null>(null);

  async function loadLots() {
    const data = await apiGet<MixLot[]>("/mix-lots");
    setLots(data);
  }

  useEffect(() => {
    (async () => {
      const [l, r, p] = await Promise.all([
        apiGet<MixLot[]>("/mix-lots"),
        apiGet<SubstrateRecipeVersion[]>("/substrate-recipe-versions"),
        apiGet<FillProfile[]>("/fill-profiles"),
      ]);
      setLots(l);
      setRecipes(r);
      setProfiles(p);
      if (r.length > 0 && !recipeId) setRecipeId(r[0].substrate_recipe_version_id);
      if (p.length > 0 && !profileId) setProfileId(p[0].fill_profile_id);
    })().catch((e) => setError(String(e)));
  }, []);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (recipeId === "" || profileId === "") {
      setError("Select recipe and fill profile.");
      return;
    }
    try {
      await apiPost<MixLot>("/mix-lots", {
        lot_code: lotCode.trim(),
        substrate_recipe_version_id: recipeId,
        fill_profile_id: profileId,
      });
      setLotCode("");
      await loadLots();
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  return (
    <div>
      <div className="card">
        <h1>Mix Lots</h1>
        <p>One mix lot = one substrate mix event. A mix lot can supply multiple pasteurization runs.</p>
        <form onSubmit={onCreate} className="form">
          <label>
            Lot code
            <input value={lotCode} onChange={(e) => setLotCode(e.target.value)} placeholder="e.g. ML-2026-03-01" required />
          </label>
          <label>
            Substrate recipe
            <select value={recipeId} onChange={(e) => setRecipeId(Number(e.target.value) || "")} required>
              <option value="">Select</option>
              {recipes.map((r) => (
                <option key={r.substrate_recipe_version_id} value={r.substrate_recipe_version_id}>
                  {r.name} ({r.recipe_code})
                </option>
              ))}
            </select>
          </label>
          <label>
            Fill profile
            <select value={profileId} onChange={(e) => setProfileId(Number(e.target.value) || "")} required>
              <option value="">Select</option>
              {profiles.map((p) => (
                <option key={p.fill_profile_id} value={p.fill_profile_id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <button className="btn" type="submit">Create Mix Lot</button>
        </form>
      </div>
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Lot code</th>
              <th>Recipe</th>
              <th>Mixed at</th>
            </tr>
          </thead>
          <tbody>
            {lots.map((lot) => (
              <tr key={lot.mix_lot_id}>
                <td>{lot.lot_code}</td>
                <td>{lot.substrate_recipe_version_id}</td>
                <td>{new Date(lot.mixed_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {lots.length === 0 && <p>No mix lots.</p>}
      </div>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
