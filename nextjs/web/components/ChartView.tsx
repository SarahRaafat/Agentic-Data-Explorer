"use client";

import dynamic from "next/dynamic";
import { useMemo } from "react";
import { chartSpecToPlotly } from "@/lib/chartSpec";
import type { ChartSpec } from "@/lib/types";
import type { ThemeTokens } from "@/lib/themes";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

export default function ChartView({
  spec,
  theme,
}: {
  spec: ChartSpec;
  theme: ThemeTokens;
}) {
  const { data, layout } = useMemo(
    () => chartSpecToPlotly(spec, theme),
    [spec, theme]
  );
  return (
    <div className="chart-wrap">
      <Plot
        data={data}
        layout={layout}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: "100%", height: "440px" }}
        useResizeHandler
      />
    </div>
  );
}
