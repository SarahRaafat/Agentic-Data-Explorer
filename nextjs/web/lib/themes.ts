export type ThemeName = "light" | "dark";

export type ThemeTokens = {
  name: ThemeName;
  bg: string;
  card: string;
  text: string;
  muted: string;
  accent: string;
  border: string;
  shadow: string;
  button: string;
  button_hover: string;
  button_text: string;
  input_bg: string;
  plotly_template: string;
};

export const THEMES: Record<ThemeName, ThemeTokens> = {
  light: {
    name: "light",
    bg: "#f3eef9",
    card: "#faf7fd",
    text: "#1a1028",
    muted: "#5c4d70",
    accent: "#ae70e0",
    border: "#ddd0ef",
    shadow: "rgba(174,112,224,0.10)",
    button: "#ae70e0",
    button_hover: "#c48ef0",
    button_text: "#ffffff",
    input_bg: "#ede4f7",
    plotly_template: "plotly_white",
  },
  dark: {
    name: "dark",
    bg: "#0f1419",
    card: "#1a2332",
    text: "#e7ecf3",
    muted: "#9ca3af",
    accent: "#60a5fa",
    border: "#334155",
    shadow: "rgba(0,0,0,0.45)",
    button: "#123a63",
    button_hover: "#0d2d4f",
    button_text: "#e7ecf3",
    input_bg: "#1a2332",
    plotly_template: "plotly_dark",
  },
};

export function themeToCssVars(theme: ThemeTokens): Record<string, string> {
  return {
    "--bg": theme.bg,
    "--card": theme.card,
    "--text": theme.text,
    "--muted": theme.muted,
    "--accent": theme.accent,
    "--border": theme.border,
    "--shadow": theme.shadow,
    "--button": theme.button,
    "--button-hover": theme.button_hover,
    "--button-text": theme.button_text,
    "--input-bg": theme.input_bg,
  };
}
