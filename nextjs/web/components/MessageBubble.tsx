"use client";

import ReactMarkdown from "react-markdown";
import ChartView from "./ChartView";
import DashboardView from "./DashboardView";
import ExportLinks from "./ExportLinks";
import type { ChatMessage } from "@/lib/types";
import type { ThemeTokens } from "@/lib/themes";

export default function MessageBubble({
  message,
  theme,
}: {
  message: ChatMessage;
  theme: ThemeTokens;
}) {
  if (message.role === "user") {
    return (
      <article className="msg">
        <div className="msg-role">You</div>
        <div className="msg-body">{message.content}</div>
      </article>
    );
  }

  const p = message.payload;
  const dashTitles = new Set(
    (p.dashboards || []).flatMap(
      (d) => (d.charts || []).map((c) => c.title).filter(Boolean) as string[]
    )
  );
  const standalone = (p.charts || []).filter(
    (c) => !c.title || !dashTitles.has(c.title)
  );

  return (
    <article className="msg">
      <div className="msg-role">Assistant</div>
      <div className="msg-body">
        <ReactMarkdown>
          {p.answer || message.content || "_No text response._"}
        </ReactMarkdown>

        {p.explanations && p.explanations.length > 0 && (
          <details className="details">
            <summary>How to read the chart</summary>
            {p.explanations.map((e, i) => (
              <p key={i}>{e}</p>
            ))}
          </details>
        )}

        {p.insights && p.insights.length > 0 && (
          <>
            <h4 className="section-title">Insights</h4>
            <ul>
              {p.insights.map((b, i) => (
                <li key={i}>{b}</li>
              ))}
            </ul>
          </>
        )}

        {p.critiques && p.critiques.length > 0 && (
          <details className="details" open>
            <summary>Critic review</summary>
            {p.critiques.map((c, i) => (
              <div key={i}>
                <p>
                  <strong>{c.approved ? "Approved" : "Needs work"}</strong>
                  {c.reason ? ` — ${c.reason}` : ""}
                </p>
                {(c.issues || []).map((issue, j) => (
                  <p key={j}>- {issue}</p>
                ))}
                {c.suggested_chart_type && (
                  <p>Suggested chart: {c.suggested_chart_type}</p>
                )}
              </div>
            ))}
          </details>
        )}

        {(p.dashboards || []).map((d, i) => (
          <DashboardView key={d.id || i} dashboard={d} theme={theme} />
        ))}

        {standalone.map((chart, i) => (
          <div key={`${chart.title || "chart"}-${i}`}>
            <ChartView spec={chart} theme={theme} />
            <details className="details">
              <summary>Chart JSON</summary>
              <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.8rem" }}>
                {JSON.stringify(chart, null, 2)}
              </pre>
            </details>
          </div>
        ))}

        <ExportLinks exports={p.exports || []} />
      </div>
    </article>
  );
}
