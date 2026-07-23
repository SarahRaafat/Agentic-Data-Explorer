"use client";

type Kpi = { label: string; value: string | number };

export default function KpiGrid({ kpis }: { kpis: Kpi[] }) {
  if (!kpis.length) return null;
  return (
    <div className="kpi-grid">
      {kpis.map((kpi, i) => (
        <div className="kpi-card" key={`${kpi.label}-${i}`}>
          <div className="kpi-label">{kpi.label}</div>
          <div className="kpi-value">{String(kpi.value)}</div>
        </div>
      ))}
    </div>
  );
}
