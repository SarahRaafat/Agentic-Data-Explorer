"use client";

import { useCallback, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import Chat from "@/components/Chat";
import Sidebar from "@/components/Sidebar";
import { THEMES, themeToCssVars, type ThemeName } from "@/lib/themes";

export default function HomePage() {
  const [themeName, setThemeName] = useState<ThemeName>("dark");
  const [pendingPrompt, setPendingPrompt] = useState<string | null>(null);
  const [clearSignal, setClearSignal] = useState(0);
  const [busy, setBusy] = useState(false);

  const theme = THEMES[themeName];
  const cssVars = useMemo(() => themeToCssVars(theme), [theme]);
  const onThemeChange = useCallback((name: ThemeName) => {
    setThemeName(name);
  }, []);

  return (
    <div className="app-shell" style={cssVars as CSSProperties}>
      <Sidebar
        themeName={themeName}
        onThemeChange={onThemeChange}
        onExample={(p) => setPendingPrompt(p)}
        onClear={() => {
          setClearSignal((n) => n + 1);
          setPendingPrompt(null);
        }}
        busy={busy}
      />
      <Chat
        theme={theme}
        onThemeFromAgent={onThemeChange}
        pendingPrompt={pendingPrompt}
        onPendingConsumed={() => setPendingPrompt(null)}
        clearSignal={clearSignal}
        onBusyChange={setBusy}
      />
    </div>
  );
}
