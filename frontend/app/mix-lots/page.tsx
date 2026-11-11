"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPost } from "../../lib/api";
import { RunCorrection } from "../../lib/run-correction";
import { useCurrentUser } from "../../lib/session";
import type { FillProfile, MixLot, SubstrateRecipeVersion } from "../../lib/types";

export default function MixLotsPage() {
  const isAdmin = useCurrentUser().role === "admin";
  const [lots, setLots] = useState<MixLot[]>([]);
  const [recipes, setRecipes] = useState<SubstrateRecipeVersion[]>([]);
  const [profiles, setProfiles] = useState<FillProfile[]>([]);
  const [lotCode, setLotCode] = useState("");
  const [recipeId, setRecipeId] = useState<number | "">("");
  const [profileId, setProfileId] = useState<number | "">("");
  const [notes, setNotes] = useState("");
  const [correctingId, setCorrectingId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadLots = useCallback(async () => {
    setLots(await apiGet<MixLot[]>("/mix-lots"));
  }, []);

  useEffect(() => {
    (async () => {
      const [lotRows, recipeRows, profileRows] = await Promise.all([
        apiGet<MixLot[]>("/mix-lots"),
        apiGet<SubstrateRecipeVersion[]>("/substrate-recipe-versions"),
        apiGet<FillProfile[]>("/fill-profiles"),
      ]);
      setLots(lotRows);
      setRecipes(recipeRows);
      setProfiles(profileRows);
      // Only active recipes and profiles are offered for a new lot.
      const firstRecipe = recipeRows.find((row) => row.is_active);
      const firstProfile = profileRows.find((row) => row.is_active);
      setRecipeId((current) => current || firstRecipe?.substrate_recipe_version_id || "");
      setProfileId((current) => current || firstProfile?.fill_profile_id || "");
    })().catch((e) => setError(e?.message || String(e)));
  }, []);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    if (recipeId === "" || profileId === "") {
      setError("Select a substrate recipe and a fill profile.");
      return;
    }
    setBusy(true);
    try {
      const created = await apiPost<MixLot>("/mix-lots", {
        lot_code: lotCode.trim(),
        substrate_recipe_version_id: recipeId,
        fill_profile_id: profileId,
        notes: notes.trim() || null,
      });
      setLotCode("");
      setNotes("");
      await loadLots();
      setMessage(`Mix lot ${created.lot_code} recorded.`);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  // Every recipe and profile, active or not, so that an old lot still shows what it was made with.
  const recipeName = new Map(recipes.map((row) => [row.substrate_recipe_version_id, `${row.name} (${row.recipe_code})`]));
  const profileName = new Map(profiles.map((row) => [row.fill_profile_id, row.name]));
  const correcting = lots.find((lot) => lot.mix_lot_id === correctingId) ?? null;

  return (
    <>
      <div className="card">
        <h1>Mix Lots</h1>
        <p>One mix lot is one batch of substrate mixed at one time. It can fill more than one pasteurization run.</p>
        {message && <p className="success" role="status">{message}</p>}
        {error && <p className="error" role="alert">{error}</p>}
        <form onSubmit={onCreate} className="form stackedForm">
          <label>
            Lot code
            <input value={lotCode} onChange={(e) => setLotCode(e.target.value)} placeholder="MIX-261109A" required />
          </label>
          <label>
            Substrate recipe
            <select value={recipeId} onChange={(e) => setRecipeId(Number(e.target.value) || "")} required>
              <option value="">— Select —</option>
              {recipes.filter((row) => row.is_active).map((row) => (
                <option key={row.substrate_recipe_version_id} value={row.substrate_recipe_version_id}>
                  {row.name} ({row.recipe_code})
                </option>
              ))}
            </select>
          </label>
          <label>
            Fill profile
            <select value={profileId} onChange={(e) => setProfileId(Number(e.target.value) || "")} required>
              <option value="">— Select —</option>
              {profiles.filter((row) => row.is_active).map((row) => (
                <option key={row.fill_profile_id} value={row.fill_profile_id}>
                  {row.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Notes
            <input value={notes} onChange={(e) => setNotes(e.target.value)} />
          </label>
          <button className="btn btnSolid" type="submit" disabled={busy}>Create Mix Lot</button>
        </form>
      </div>

      {correcting && (
        <RunCorrection
          key={correcting.mix_lot_id}
          path={`/mix-lots/${correcting.mix_lot_id}`}
          values={correcting}
          title={`Correct mix lot ${correcting.lot_code}`}
          intro="The lot's code, the time it was mixed and its notes can be corrected."
          savedMessage="Mix lot corrected."
          startOpen
          onSaved={loadLots}
          onClose={() => setCorrectingId(null)}
          fields={[
            { key: "lot_code", label: "Lot code", kind: "text", required: true },
            { key: "mixed_at", label: "Mixed at", kind: "datetime", required: true },
            { key: "notes", label: "Notes", kind: "text" },
          ]}
        />
      )}

      <div className="card">
        <h2>All mix lots</h2>
        {lots.length === 0 ? (
          <p>None yet.</p>
        ) : (
          <div className="tableWrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Lot code</th>
                  <th>Recipe</th>
                  <th>Fill profile</th>
                  <th>Mixed</th>
                  <th>Notes</th>
                  {isAdmin && <th>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {lots.map((lot) => (
                  <tr key={lot.mix_lot_id}>
                    <td>{lot.lot_code}</td>
                    <td>{recipeName.get(lot.substrate_recipe_version_id) ?? lot.substrate_recipe_version_id}</td>
                    <td>{profileName.get(lot.fill_profile_id) ?? lot.fill_profile_id}</td>
                    <td>{new Date(lot.mixed_at).toLocaleString()}</td>
                    <td>{lot.notes ?? "-"}</td>
                    {isAdmin && (
                      <td>
                        <button
                          className="btn btnSmall"
                          type="button"
                          aria-label={`Correct ${lot.lot_code}`}
                          onClick={() => {
                            setCorrectingId(lot.mix_lot_id);
                            window.scrollTo({ top: 0, behavior: "smooth" });
                          }}
                        >
                          Correct
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
