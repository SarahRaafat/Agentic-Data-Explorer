import type { Data, Layout } from "plotly.js";
import type { ChartSpec } from "./types";
import type { ThemeTokens } from "./themes";

/** Build Plotly traces + layout from ChartSpec (mirrors shared charts logic). */
export function chartSpecToPlotly(
  spec: ChartSpec,
  theme: ThemeTokens
): { data: Data[]; layout: Partial<Layout> } {
  const chartType = spec.chart_type || "bar";
  const title = spec.title || "Chart";
  const labels = (spec.labels || []).map(String);
  const values = (spec.values || []).map(Number);
  const xLabel = spec.x_label || "";
  const yLabel = spec.y_label || "";
  const accent = theme.accent;
  const textColor = theme.text;
  const muted = theme.muted;
  const border = theme.border;
  const card = theme.card;

  let data: Data[] = [];

  if (chartType === "line") {
    data = [
      {
        type: "scatter",
        mode: "lines+markers",
        x: labels,
        y: values,
        line: { color: accent },
        marker: { color: accent },
      },
    ];
  } else if (chartType === "area") {
    data = [
      {
        type: "scatter",
        mode: "lines",
        x: labels,
        y: values,
        fill: "tozeroy",
        line: { color: accent },
        fillcolor: accent + "55",
      },
    ];
  } else if (chartType === "pie") {
    data = [
      {
        type: "pie",
        labels,
        values,
        textfont: { color: textColor },
      },
    ];
  } else if (chartType === "scatter") {
    data = [
      {
        type: "scatter",
        mode: "markers",
        x: labels,
        y: values,
        marker: { color: accent },
      },
    ];
  } else if (chartType === "horizontal_bar") {
    data = [
      {
        type: "bar",
        orientation: "h",
        x: values,
        y: labels,
        marker: { color: accent },
      },
    ];
  } else {
    data = [
      {
        type: "bar",
        x: labels,
        y: values,
        marker: { color: accent },
      },
    ];
  }

  const needsAngledTicks =
    chartType !== "pie" && chartType !== "horizontal_bar";
  const longYLabel = yLabel.length > 12;
  const longCategory =
    chartType === "horizontal_bar" && labels.some((l) => l.length > 10);

  const layout: Partial<Layout> = {
    title: {
      text: title,
      font: { color: textColor, size: 16 },
      x: 0.02,
      xanchor: "left",
    },
    xaxis: {
      title: xLabel
        ? { text: xLabel, font: { color: textColor, size: 12 }, standoff: 18 }
        : undefined,
      tickfont: { color: textColor, size: 11 },
      gridcolor: border,
      linecolor: muted,
      zerolinecolor: border,
      tickangle: needsAngledTicks ? -35 : 0,
      automargin: true,
    },
    yaxis: {
      title: yLabel
        ? { text: yLabel, font: { color: textColor, size: 12 }, standoff: 12 }
        : undefined,
      tickfont: { color: textColor, size: 11 },
      gridcolor: border,
      linecolor: muted,
      zerolinecolor: border,
      automargin: true,
    },
    margin: {
      l: longYLabel || longCategory ? 90 : 70,
      r: 24,
      t: 56,
      b: needsAngledTicks ? 100 : 64,
    },
    height: 440,
    paper_bgcolor: card,
    plot_bgcolor: card,
    font: { color: textColor },
    legend: { font: { color: textColor } },
    autosize: true,
  };

  return { data, layout };
}
