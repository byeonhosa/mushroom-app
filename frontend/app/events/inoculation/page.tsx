"use client";

import { useState } from "react";
import { apiPost } from "../../../lib/api";

export default function InoculationPage() {
  const [substrateBagId, setSubstrateBagId] = useState("");
  const [spawnBagId, setSpawnBagId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    const sub = substrateBagId.trim();
    const spawn = spawnBagId.trim();
    if (!sub || !spawn) {
      setError("Enter both substrate and spawn bag IDs.");
      return;
    }
    try {
      await apiPost("/inoculations", {
        substrate_bag_id: sub,
        spawn_bag_id: spawn,
      });
      setSuccess(`Inoculated ${sub} with spawn ${spawn}`);
      setSubstrateBagId("");
      setSpawnBagId("");
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  return (
    <div className="card">
      <h1>Inoculation</h1>
      <p>Scan or enter substrate bag ID and spawn bag ID when inoculating.</p>
      <form onSubmit={submit} className="form">
        <label>
          Substrate bag ID
          <input
            value={substrateBagId}
            onChange={(e) => setSubstrateBagId(e.target.value)}
            placeholder="e.g. PAST-20260301-001-MM-LM-0001"
            autoFocus
          />
        </label>
        <label>
          Spawn bag ID
          <input
            value={spawnBagId}
            onChange={(e) => setSpawnBagId(e.target.value)}
            placeholder="e.g. STER-20260215-003-SR1-LM-0042"
          />
        </label>
        <button className="btn" type="submit">Record Inoculation</button>
      </form>
      {success && <p className="success">{success}</p>}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
