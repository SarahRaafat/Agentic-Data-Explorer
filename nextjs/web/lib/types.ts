export type ChartSpec = {
  tool?: string;
  chart_type?: string;
  title?: string;
  labels?: string[];
  values?: number[];
  x_label?: string;
  y_label?: string;
  recommendation?: {
    recommended_chart?: string;
    reason?: string;
    confidence?: number;
  };
};

export type Critique = {
  approved?: boolean;
  issues?: string[];
  suggested_chart_type?: string;
  reason?: string;
};

export type Dashboard = {
  tool?: string;
  id?: string;
  title?: string;
  theme?: string;
  kpis?: { label: string; value: string | number }[];
  charts?: ChartSpec[];
  table?: { records?: Record<string, unknown>[]; columns?: string[]; rows?: unknown[][] };
  insights?: string[];
  layout?: unknown;
  created_at?: string;
};

export type ExportItem = {
  tool?: string;
  format?: string;
  path?: string;
  note?: string;
};

export type VizPayload = {
  answer?: string;
  charts?: ChartSpec[];
  dashboards?: Dashboard[];
  insights?: string[];
  explanations?: string[];
  critiques?: Critique[];
  exports?: ExportItem[];
  theme?: Record<string, string> | null;
};

export type ChatMessage =
  | { id: string; role: "user"; content: string }
  | { id: string; role: "assistant"; content: string; payload: VizPayload };

export type MetaResponse = {
  model: string;
  dataset: string;
  dataset_exists: boolean;
  files: string[];
  themes: Record<string, Record<string, string>>;
  agent_root: string;
};
