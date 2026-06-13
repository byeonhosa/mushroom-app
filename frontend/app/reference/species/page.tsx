"use client";

import { useEffect, useMemo, useState } from "react";
import { apiGet } from "../../../lib/api";
import type { SpeciesProfile } from "../../../lib/types";

// Fixed temperature scale shared by every band, so species that share a grow
// room cluster by color (teal ~50°F → amber ~68°F → orange ~84°F).
const SCALE_MIN = 45;
const SCALE_MAX = 90;

type UseFilter = "all" | "culinary" | "medicinal" | "both";
type SortKey =
  | "name"
  | "difficulty_rank"
  | "fruiting_temp_f_low"
  | "colonization_days_low"
  | "pin_to_harvest_days_low"
  | "biological_efficiency_pct_high";

const USE_OPTIONS: { value: UseFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "culinary", label: "Culinary" },
  { value: "medicinal", label: "Medicinal" },
  { value: "both", label: "Both" },
];

// difficulty_rank in the seed data uses 1=Easy, 3=Medium, 4=Med-Hard, 5=Hard.
const DIFFICULTY_OPTIONS: { value: "all" | number; label: string }[] = [
  { value: "all", label: "All" },
  { value: 1, label: "Easy" },
  { value: 3, label: "Medium" },
  { value: 4, label: "Med-Hard" },
  { value: 5, label: "Hard" },
];

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: "name", label: "Name" },
  { value: "difficulty_rank", label: "Difficulty" },
  { value: "fruiting_temp_f_low", label: "Fruiting temp" },
  { value: "colonization_days_low", label: "Colonization time" },
  { value: "pin_to_harvest_days_low", label: "Pin-to-harvest" },
  { value: "biological_efficiency_pct_high", label: "Biological efficiency" },
];

const USE_LABEL: Record<string, string> = {
  culinary: "Culinary",
  medicinal: "Medicinal",
  both: "Culinary + Medicinal",
};

const TRIGGER_LABEL: Record<string, string> = {
  fae_increase: "Fresh-air increase",
  temp_drop: "Temperature drop (deliberate)",
  co2_drop: "CO₂ crash via FAE jump",
  co2_drop_cold_shock: "CO₂ drop + cold shock",
  cold_shock_and_strike: "Cold-water soak + smack",
  combined: "Combined (temp + CO₂ + light + RH)",
  form_dependent: "Form-dependent (conks vs antlers)",
};

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

function scalePct(t: number) {
  return ((clamp(t, SCALE_MIN, SCALE_MAX) - SCALE_MIN) / (SCALE_MAX - SCALE_MIN)) * 100;
}

// Midpoint-of-range → ramp color: teal (cool) → amber (mid) → orange (warm).
function tempColor(t: number) {
  const lo = 50;
  const mid = 68;
  const hi = 84;
  const cool = [79, 179, 191];
  const midc = [224, 179, 65];
  const warm = [224, 123, 79];
  let a: number[];
  let b: number[];
  let f: number;
  if (t <= mid) {
    a = cool;
    b = midc;
    f = (t - lo) / (mid - lo);
  } else {
    a = midc;
    b = warm;
    f = (t - mid) / (hi - mid);
  }
  f = clamp(f, 0, 1);
  const c = a.map((v, i) => Math.round(v + (b[i] - v) * f));
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
}

// Null-aware range formatter. A null low bound renders as "<high" (e.g. CO₂),
// a null high bound as ">low", both null as an em dash.
function rangeText(lo: number | null | undefined, hi: number | null | undefined, unit = "") {
  const u = unit ? ` ${unit}` : "";
  if (lo == null && hi == null) return "—";
  if (lo == null) return `<${hi}${u}`;
  if (hi == null) return `>${lo}${u}`;
  if (lo === hi) return `${lo}${u}`;
  return `${lo}–${hi}${u}`;
}

function TemperatureBar({
  label,
  lo,
  hi,
}: {
  label: string;
  lo: number | null | undefined;
  hi: number | null | undefined;
}) {
  if (lo == null || hi == null) {
    return (
      <div className="sp-bandrow">
        <span className="sp-blab">{label}</span>
        <div className="sp-track">
          <span className="sp-band-empty">—</span>
        </div>
      </div>
    );
  }
  const left = scalePct(lo);
  const width = Math.max(2.5, scalePct(hi) - left);
  const color = tempColor((lo + hi) / 2);
  const text = lo === hi ? `${lo}°` : `${lo}–${hi}°`;
  return (
    <div className="sp-bandrow">
      <span className="sp-blab">{label}</span>
      <div className="sp-track">
        <div className="sp-fill" style={{ left: `${left}%`, width: `${width}%`, background: color }}>
          <span className="sp-ftxt">{text}</span>
        </div>
      </div>
    </div>
  );
}

function Readout({ label, value }: { label: string; value: string }) {
  return (
    <div className="sp-ro">
      <span className="sp-ro-k">{label}</span>
      <span className="sp-ro-v">{value}</span>
    </div>
  );
}

function SpeciesCard({ s }: { s: SpeciesProfile }) {
  const lightValue =
    s.light_lux_low == null && s.light_lux_high == null
      ? "—"
      : rangeText(s.light_lux_low, s.light_lux_high, "lux");
  return (
    <article className="card sp-card">
      <div className="sp-card-top">
        <div>
          <div className="sp-cname">{s.common_name}</div>
          <div className="sp-sname">{s.scientific_name}</div>
        </div>
        <div className="sp-tags">
          {s.use_type && <span className="statusBadge">{USE_LABEL[s.use_type] ?? s.use_type}</span>}
          {s.difficulty && <span className="sp-diff">{s.difficulty}</span>}
        </div>
      </div>

      <div className="sp-band">
        <TemperatureBar label="Incubation" lo={s.incubation_temp_f_low} hi={s.incubation_temp_f_high} />
        <TemperatureBar label="Fruiting" lo={s.fruiting_temp_f_low} hi={s.fruiting_temp_f_high} />
        <div className="sp-ticks" aria-hidden="true">
          <span>45</span>
          <span>56</span>
          <span>68</span>
          <span>79</span>
          <span>90°F</span>
        </div>
      </div>

      <div className="sp-readouts">
        <Readout label="Spawn rate" value={rangeText(s.spawn_rate_pct_low, s.spawn_rate_pct_high, "%")} />
        <Readout label="Colonization" value={rangeText(s.colonization_days_low, s.colonization_days_high, "d")} />
        <Readout label="Fruiting RH" value={rangeText(s.fruiting_humidity_pct_low, s.fruiting_humidity_pct_high, "%")} />
        <Readout label="Fruiting CO₂" value={rangeText(s.fruiting_co2_ppm_low, s.fruiting_co2_ppm_high, "ppm")} />
        <Readout label="Fresh air" value={rangeText(s.fae_ach_low, s.fae_ach_high, "ACH")} />
        <Readout label="Light" value={lightValue} />
        <Readout label="Pin→harvest" value={rangeText(s.pin_to_harvest_days_low, s.pin_to_harvest_days_high, "d")} />
        <Readout label="Biol. eff." value={rangeText(s.biological_efficiency_pct_low, s.biological_efficiency_pct_high, "%")} />
        <Readout label="Flushes" value={rangeText(s.typical_flushes_low, s.typical_flushes_high)} />
        <Readout label="Moisture" value={rangeText(s.substrate_moisture_pct_low, s.substrate_moisture_pct_high, "%")} />
      </div>

      <p className="sp-trigger">
        Pinning trigger: <strong>{s.pinning_trigger ? TRIGGER_LABEL[s.pinning_trigger] ?? s.pinning_trigger : "—"}</strong>
        {s.substrate_primary ? <> · substrate: {s.substrate_primary}</> : null}
      </p>

      <details className="sp-more">
        <summary>Notes, yield &amp; pricing</summary>
        <div className="sp-more-body">
          {s.notes && (
            <p>
              <span className="sp-lbl">Notes</span>
              {s.notes}
            </p>
          )}
          {s.yield_notes && (
            <p>
              <span className="sp-lbl">Yield</span>
              {s.yield_notes}
            </p>
          )}
          {s.pricing_notes && (
            <p>
              <span className="sp-lbl">Market / pricing</span>
              {s.pricing_notes}
            </p>
          )}
        </div>
      </details>
    </article>
  );
}

export default function SpeciesReferencePage() {
  const [species, setSpecies] = useState<SpeciesProfile[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [useFilter, setUseFilter] = useState<UseFilter>("all");
  const [difficulty, setDifficulty] = useState<"all" | number>("all");
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [ascending, setAscending] = useState(true);

  useEffect(() => {
    apiGet<SpeciesProfile[]>("/species-profiles")
      .then((data) => setSpecies(data))
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const visible = useMemo(() => {
    const dir = ascending ? 1 : -1;
    const q = query.trim().toLowerCase();
    const rows = species.filter((s) => {
      if (useFilter !== "all" && s.use_type !== useFilter) return false;
      if (difficulty !== "all" && s.difficulty_rank !== difficulty) return false;
      if (q) {
        const hay = [s.common_name, s.scientific_name, s.substrate_primary, s.notes]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
    rows.sort((a, b) => {
      if (sortKey === "name") return a.common_name.localeCompare(b.common_name) * dir;
      const av = a[sortKey] ?? Infinity;
      const bv = b[sortKey] ?? Infinity;
      return (Number(av) - Number(bv)) * dir;
    });
    return rows;
  }, [species, useFilter, difficulty, query, sortKey, ascending]);

  function clearFilters() {
    setUseFilter("all");
    setDifficulty("all");
    setQuery("");
  }

  return (
    <div>
      <div className="card">
        <p className="sectionEyebrow">Cultivation Reference</p>
        <h1>Species Reference</h1>
        <p className="muted">
          Eight species with commercial-protocol detail. Each temperature band is graded cool → warm on a fixed
          45–90°F scale, so species that share a grow room cluster by color. Read-only reference; verify against your
          own production.
        </p>

        <div className="sp-controls">
          <div className="sp-group" role="group" aria-label="Filter by use">
            <span className="sp-group-label">Use</span>
            <div className="toolbar">
              {USE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  className="btn sp-chip"
                  aria-pressed={useFilter === opt.value}
                  onClick={() => setUseFilter(opt.value)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div className="sp-group" role="group" aria-label="Filter by difficulty">
            <span className="sp-group-label">Difficulty</span>
            <div className="toolbar">
              {DIFFICULTY_OPTIONS.map((opt) => (
                <button
                  key={String(opt.value)}
                  type="button"
                  className="btn sp-chip"
                  aria-pressed={difficulty === opt.value}
                  onClick={() => setDifficulty(opt.value)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div className="sp-group">
            <label className="sp-group-label" htmlFor="sp-sort">
              Sort by
            </label>
            <div className="toolbar">
              <select id="sp-sort" value={sortKey} onChange={(e) => setSortKey(e.target.value as SortKey)}>
                {SORT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="btn"
                onClick={() => setAscending((v) => !v)}
                aria-label={`Sort ${ascending ? "ascending" : "descending"}, toggle`}
              >
                {ascending ? "↑ Asc" : "↓ Desc"}
              </button>
            </div>
          </div>

          <div className="sp-group sp-group-search">
            <label className="sp-group-label" htmlFor="sp-search">
              Search
            </label>
            <input
              id="sp-search"
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="name, substrate, notes…"
              autoComplete="off"
            />
          </div>
        </div>

        <p className="sp-count" aria-live="polite">
          {loading ? "Loading…" : `${visible.length} of ${species.length} species`}
        </p>
      </div>

      {error && <p className="error">{error}</p>}

      {!loading && !error && visible.length === 0 && (
        <div className="card">
          <p className="muted">No species match these filters.</p>
          <button type="button" className="btn" onClick={clearFilters}>
            Clear filters
          </button>
        </div>
      )}

      <div className="sp-grid">
        {visible.map((s) => (
          <SpeciesCard key={s.code} s={s} />
        ))}
      </div>
    </div>
  );
}
