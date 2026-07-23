"use client";

import ChartView from "./ChartView";
import KpiGrid from "./KpiGrid";
import type { Dashboard } from "@/lib/types";
import type { ThemeTokens } from "@/lib/themes";

function recordsFromTable(table: Dashboard["table"]): Record<string, unknown>[] {
  if (!table) return [];
  if (table.records?.length) return table.records;
  if (table.columns && table.rows) {
    return table.rows.map((row) => {
      const obj: Record<string, unknown> = {};
      table.columns!.forEach((col, i) => {
        obj[col] = Array.isArray(row) ? row[i] : row;
      });
      return obj;
    });
  }
  return [];
}

export default function DashboardView({
  dashboard,
  theme,
}: {
  dashboard: Dashboard;
  theme: ThemeTokens;
}) {
  const records = recordsFromTable(dashboard.table);
  const columns =
    dashboard.table?.columns || (records[0] ? Object.keys(records[0]) : []);

  return (
    <section>
      <h3 className="section-title">{dashboard.title || "Dashboard"}</h3>
      <KpiGrid kpis={dashboard.kpis || []} />
      {(dashboard.charts || []).map((chart, i) => (
        <ChartView key={`${chart.title || "c"}-${i}`} spec={chart} theme={theme} />
      ))}
      {dashboard.insights && dashboard.insights.length > 0 && (
        <>
          <h4 className="section-title">Insights</h4>
          <ul>
            {dashboard.insights.map((b, i) => (
              <li key={i}>{b}</li>
            ))}
          </ul>
        </>
      )}
      {records.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {columns.map((c) => (
                  <th key={c}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {records.slice(0, 50).map((row, ri) => (
                <tr key={ri}>
                  {columns.map((c) => (
                    <td key={c}>{String(row[c] ?? "")}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {dashboard.layout != null && (
        <details className="details">
          <summary>Layout / JSON</summary>
          <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.8rem" }}>
            {JSON.stringify(dashboard.layout, null, 2)}
          </pre>
        </details>
      )}
    </section>
  );
}
