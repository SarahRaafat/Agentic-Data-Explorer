"use client";

import { useEffect, useState } from "react";
import { fetchMeta, setServerTheme } from "@/lib/api";
import type { MetaResponse } from "@/lib/types";
import type { ThemeName } from "@/lib/themes";

const EXAMPLE_PROMPTS = [
  "Show a line chart of orders by hour of day, then explain and generate insights",
  "Bar chart of top 10 departments by product count — ask the critic to review it",
  "Build a dashboard for this grocery dataset with KPIs and charts",
  "Filter to produce-related analysis if possible, then visualize product counts",
  "Switch to dark mode and export the last dashboard as markdown",
];

export default function Sidebar({
  themeName,
  onThemeChange,
  onExample,
  onClear,
  busy,
}: {
  themeName: ThemeName;
  onThemeChange: (name: ThemeName) => void;
  onExample: (prompt: string) => void;
  onClear: () => void;
  busy: boolean;
}) {
  const [meta, setMeta] = useState<MetaResponse | null>(null);
  const [metaError, setMetaError] = useState<string | null>(null);
  const [filesOpen, setFilesOpen] = useState(false);

  useEffect(() => {
    fetchMeta()
      .then(setMeta)
      .catch((e: Error) => setMetaError(e.message));
  }, []);

  async function handleTheme(name: ThemeName) {
    onThemeChange(name);
    try {
      await setServerTheme(name);
    } catch {
      /* UI still updates */
    }
  }

  return (
    <aside className="sidebar">
      <h1>Instacart Viz Agent</h1>
      <p className="caption">
        10 presentation tools: visualize, recommend, dashboard, layout,
        insights, explain, filter, export, theme, critic.
      </p>

      {metaError && (
        <p className="status-err">
          API offline: {metaError}
          {"\n"}Start uvicorn on :8000
        </p>
      )}

      {meta && (
        <>
          <p className="meta-line">
            <strong>Model:</strong> <code>{meta.model}</code>
          </p>
          <p className="meta-line">
            <strong>Dataset:</strong> <code>{meta.dataset}</code>
          </p>
          {meta.dataset_exists ? (
            <>
              <p className="status-ok">{meta.files.length} CSV files found</p>
              <button
                type="button"
                className="btn btn-sm"
                onClick={() => setFilesOpen((v) => !v)}
              >
                {filesOpen ? "Hide files" : "Show files"}
              </button>
              {filesOpen && (
                <ul className="file-list">
                  {meta.files.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
              )}
            </>
          ) : (
            <p className="status-err">Dataset folder missing</p>
          )}
        </>
      )}

      <div className="divider" />
      <label htmlFor="theme-select">Theme</label>
      <select
        id="theme-select"
        className="select"
        value={themeName}
        onChange={(e) => handleTheme(e.target.value as ThemeName)}
      >
        <option value="dark">dark</option>
        <option value="light">light</option>
      </select>

      <div className="divider" />
      <strong>Try an example</strong>
      {EXAMPLE_PROMPTS.map((prompt) => (
        <button
          key={prompt}
          type="button"
          className="btn"
          disabled={busy}
          onClick={() => onExample(prompt)}
        >
          {prompt}
        </button>
      ))}

      <div className="divider" />
      <button type="button" className="btn" disabled={busy} onClick={onClear}>
        Clear chat
      </button>
    </aside>
  );
}
