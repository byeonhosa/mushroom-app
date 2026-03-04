"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api";

export default function SpawnLabelsPage() {
  const searchParams = useSearchParams();
  const idsParam = searchParams.get("ids") || "";
  const bagIds = idsParam ? idsParam.split(",").map((s) => decodeURIComponent(s.trim())).filter(Boolean) : [];
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    setLoaded(true);
  }, []);

  if (!loaded || bagIds.length === 0) {
    return (
      <div className="card">
        <h1>Print Labels</h1>
        <p>No bag IDs provided. Create spawn bags first.</p>
        <a className="btn" href="/bags/create/spawn">Create Spawn Bags</a>
      </div>
    );
  }

  return (
    <div className="card">
      <h1 className="no-print">Print Labels ({bagIds.length} labels)</h1>
      <p className="no-print">
        <button className="btn" type="button" onClick={() => window.print()}>
          Print
        </button>
        <a className="btn" href="/bags" style={{ marginLeft: 8 }}>View Bags</a>
      </p>
      <div className="label-sheet">
        {bagIds.map((id) => (
          <div key={id} className="label-1x1">
            <img
              src={`${API_BASE}/labels/${encodeURIComponent(id)}/qr`}
              alt={id}
              width={64}
              height={64}
            />
            <div className="label-text">{id}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
