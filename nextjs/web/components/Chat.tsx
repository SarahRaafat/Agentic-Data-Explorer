"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import MessageBubble from "./MessageBubble";
import { sendChat } from "@/lib/api";
import type { ChatMessage, VizPayload } from "@/lib/types";
import type { ThemeName, ThemeTokens } from "@/lib/themes";
import { THEMES } from "@/lib/themes";

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export default function Chat({
  theme,
  onThemeFromAgent,
  pendingPrompt,
  onPendingConsumed,
  clearSignal,
  onBusyChange,
}: {
  theme: ThemeTokens;
  onThemeFromAgent: (name: ThemeName) => void;
  pendingPrompt: string | null;
  onPendingConsumed: () => void;
  clearSignal: number;
  onBusyChange?: (busy: boolean) => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  function setBusyBoth(v: boolean) {
    setBusy(v);
    onBusyChange?.(v);
  }

  useEffect(() => {
    setMessages([]);
    setError(null);
  }, [clearSignal]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function ask(question: string) {
    const q = question.trim();
    if (!q || busy) return;
    setError(null);
    setBusyBoth(true);
    setMessages((m) => [...m, { id: uid(), role: "user", content: q }]);
    setInput("");
    try {
      const payload: VizPayload = await sendChat(q);
      if (payload.theme && typeof payload.theme.name === "string") {
        const name = payload.theme.name as ThemeName;
        if (name in THEMES) onThemeFromAgent(name);
      }
      setMessages((m) => [
        ...m,
        {
          id: uid(),
          role: "assistant",
          content: payload.answer || "",
          payload,
        },
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusyBoth(false);
    }
  }

  useEffect(() => {
    if (!pendingPrompt) return;
    onPendingConsumed();
    void ask(pendingPrompt);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingPrompt]);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void ask(input);
  }

  return (
    <div className="main">
      <header className="main-header">
        <h2>Chat with the viz agent</h2>
        <p>
          Ask for charts, dashboards, insights, theme changes, or exports. The
          agent runs PII-safe Python over the Instacart CSVs.
        </p>
      </header>

      <div className="chat-scroll">
        {error && <div className="err-banner">{error}</div>}
        {messages.length === 0 && !busy && (
          <p className="empty-hint">
            Pick an example in the sidebar or type a question below.
          </p>
        )}
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} theme={theme} />
        ))}
        {busy && <p className="loading">Agent is working…</p>}
        <div ref={bottomRef} />
      </div>

      <form className="chat-composer" onSubmit={onSubmit}>
        <textarea
          className="chat-input"
          rows={2}
          placeholder="Ask for a chart, dashboard, or insight…"
          value={input}
          disabled={busy}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void ask(input);
            }
          }}
        />
        <button
          className="btn btn-sm"
          type="submit"
          disabled={busy || !input.trim()}
        >
          Send
        </button>
      </form>
    </div>
  );
}
