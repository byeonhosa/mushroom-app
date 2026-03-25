"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api";

function SpawnLabelsContent() {
  const searchParams = useSearchParams();
  const idsParam = searchParams.get("ids") || "";
  const bagRefs = idsParam ? idsParam.split(",").map((s) => decodeURIComponent(s.trim())).filter(Boolean) : [];

  if (bagRefs.length === 0) {
    return (
      <div className="card">
        <h1>Print Labels</h1>
        <p>No spawn bag codes provided. Run spawn inoculation first.</p>
        <a className="btn" href="/events/spawn-inoculation">Go to Spawn Inoculation</a>
      </div>
    );
  }

  return (
    <div className="card">
      <h1 className="no-print">Print Labels ({bagRefs.length} labels)</h1>
      <p className="no-print workflow-note">
        Attach these labels after spawn inoculation, then scan the bags when they enter incubation.
      </p>
      <p className="no-print">
        <button className="btn" type="button" onClick={() => window.print()}>
          Print
        </button>
        <a className="btn" href="/bags" style={{ marginLeft: 8 }}>View Bags</a>
      </p>
      <div className="label-sheet">
        {bagRefs.map((bagRef) => (
          <div key={bagRef} className="label-1x1">
            <img
              src={`${API_BASE}/labels/${encodeURIComponent(bagRef)}/qr`}
              alt={bagRef}
              width={64}
              height={64}
            />
            <div className="label-text">{bagRef}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function SpawnLabelsPage() {
  return (
    <Suspense
      fallback={
        <div className="card">
          <h1>Print Labels</h1>
          <p>Loading labels...</p>
        </div>
      }
    >
      <SpawnLabelsContent />
    </Suspense>
  );
}
