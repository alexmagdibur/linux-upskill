import { FitAddon } from "@xterm/addon-fit";
import { Terminal as XTerm } from "@xterm/xterm";
import { useEffect, useRef, useState } from "react";

import { ApiError, api } from "../../api/client";
import type { TerminalTicket } from "../../types/api";

export type TerminalState = "connecting" | "connected" | "reconnecting" | "ended" | "error";

interface Props {
  sessionId: string;
  /** false — сессия завершена/остановлена, подключаться нельзя */
  enabled: boolean;
  onState?: (s: TerminalState) => void;
}

const MAX_RETRIES = 8;
// коды закрытия, при которых переподключение бессмысленно (см. app/websocket/terminal.py)
const FATAL_CLOSE = new Set([4401, 4403, 4404, 4410]);

export function Terminal({ sessionId, enabled, onState }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<TerminalState>("connecting");
  const [note, setNote] = useState("");
  const stateCb = useRef(onState);
  stateCb.current = onState;

  useEffect(() => {
    if (!enabled || !hostRef.current) return;
    let disposed = false;
    let ws: WebSocket | null = null;
    let retries = 0;
    let retryTimer: number | undefined;

    const term = new XTerm({
      cursorBlink: true,
      scrollback: 5000,
      fontFamily: '"Cascadia Code", "Fira Code", Menlo, Consolas, monospace',
      fontSize: 14,
      theme: { background: "#020617", foreground: "#e2e8f0", cursor: "#34d399" },
      allowProposedApi: false,
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(hostRef.current);
    const encoder = new TextEncoder();

    const set = (s: TerminalState, n = "") => {
      setState(s);
      setNote(n);
      stateCb.current?.(s);
    };
    const sendResize = () => {
      if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "resize", cols: term.cols, rows: term.rows }));
    };
    const doFit = () => {
      try {
        fit.fit();
      } catch {
        /* контейнер ещё не отрисован */
      }
    };

    const dataSub = term.onData((d) => {
      if (ws?.readyState === WebSocket.OPEN) ws.send(encoder.encode(d)); // ввод — бинарные кадры PTY
    });
    const resizeSub = term.onResize(sendResize);
    const ro = new ResizeObserver(doFit);
    ro.observe(hostRef.current);
    doFit();

    async function connect() {
      if (disposed) return;
      try {
        const t = await api<TerminalTicket>(`/sessions/${sessionId}/terminal-ticket`, { method: "POST" });
        if (disposed) return;
        const proto = location.protocol === "https:" ? "wss" : "ws";
        const sock = new WebSocket(`${proto}://${location.host}${t.ws_path}?ticket=${encodeURIComponent(t.ticket)}`);
        sock.binaryType = "arraybuffer";
        ws = sock;
        let firstFrame = true;
        sock.onopen = () => {
          retries = 0;
          set("connected");
          sendResize();
        };
        sock.onmessage = (ev) => {
          if (ev.data instanceof ArrayBuffer) {
            if (firstFrame) {
              term.reset(); // worker присылает scrollback при переподключении
              firstFrame = false;
            }
            term.write(new Uint8Array(ev.data));
          } else {
            try {
              const msg = JSON.parse(ev.data as string) as { type: string; code?: string };
              if (msg.type === "session_expired") set("ended", "Сессия завершена.");
              else if (msg.type === "shell_exited") set("ended", "Оболочка завершена. Переподключитесь для новой.");
              else if (msg.type === "error" && msg.code === "output_limit") set("ended", "Превышен лимит вывода терминала.");
            } catch {
              /* игнорируем неизвестные кадры */
            }
          }
        };
        sock.onclose = (ev) => {
          if (disposed) return;
          if (FATAL_CLOSE.has(ev.code)) return set("ended", "Терминал недоступен: сессия не активна.");
          scheduleRetry();
        };
        sock.onerror = () => sock.close();
      } catch (e) {
        if (disposed) return;
        if (e instanceof ApiError && (e.code === "INVALID_STATE" || e.status === 404)) {
          return set("ended", "Терминал недоступен: сессия не активна.");
        }
        scheduleRetry();
      }
    }

    function scheduleRetry() {
      if (disposed) return;
      if (retries >= MAX_RETRIES) return set("error", "Не удалось переподключиться к терминалу.");
      retries += 1;
      set("reconnecting", `Связь потеряна, попытка ${retries}…`);
      retryTimer = window.setTimeout(connect, Math.min(500 * 2 ** retries, 8000));
    }

    void connect();
    term.focus();

    return () => {
      disposed = true;
      window.clearTimeout(retryTimer);
      ro.disconnect();
      dataSub.dispose();
      resizeSub.dispose();
      ws?.close();
      term.dispose();
    };
  }, [sessionId, enabled]);

  const banner =
    state === "connected" ? null : (
      <div role="status" className="absolute inset-x-0 top-0 z-10 bg-slate-900/90 px-3 py-1.5 text-xs text-amber-200">
        {state === "connecting" && "Подключение к терминалу…"}
        {(state === "reconnecting" || state === "ended" || state === "error") && note}
      </div>
    );

  return (
    <div className="relative h-full min-h-[320px] overflow-hidden rounded-lg border border-slate-800 bg-slate-950">
      {enabled ? banner : <div className="absolute inset-x-0 top-0 z-10 bg-slate-900/90 px-3 py-1.5 text-xs text-amber-200">Терминал недоступен: сессия не активна.</div>}
      <div
        ref={hostRef}
        data-testid="terminal"
        data-state={state}
        role="application"
        aria-label="Терминал Linux. Ctrl+Shift+V — вставка, Ctrl+C — прерывание команды."
        className="xterm-host h-full w-full"
      />
    </div>
  );
}
