import { useEffect, useRef, useState } from "react";
import type { Workload } from "../types/workload";
import "./TerminalModal.css";

const ANSI_RE = /\x1b\[[0-9;]*[a-zA-Z]/g;

function stripAnsi(s: string): string {
  return s.replace(ANSI_RE, "");
}

interface Props {
  workload: Workload;
  onClose: () => void;
}

export default function TerminalModal({ workload, onClose }: Props) {
  const [lines, setLines]       = useState<string[]>([]);
  const [input, setInput]       = useState("");
  const [connected, setConnected] = useState(false);
  const [error, setError]         = useState<string | null>(null);

  const wsRef     = useRef<WebSocket | null>(null);
  const outputRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token") ?? "";
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${window.location.host}/api/v1/ws/exec/${encodeURIComponent(workload.name)}?namespace=${encodeURIComponent(workload.namespace)}&token=${encodeURIComponent(token)}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setLines([`Connected to pod in ${workload.name} (${workload.namespace})\r\n`]);
    };

    ws.onmessage = (e: MessageEvent<string>) => {
      const text = stripAnsi(e.data);
      setLines((prev) => [...prev, text]);
    };

    ws.onclose = () => {
      setConnected(false);
      setLines((prev) => [...prev, "\r\n[session closed]\r\n"]);
    };

    ws.onerror = () => {
      setError("Connection failed. Check that the workload has a running pod and exec is permitted.");
    };

    return () => { ws.close(); };
  }, [workload.name, workload.namespace]);

  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [lines]);

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      wsRef.current?.send(input + "\n");
      setInput("");
    } else if (e.key === "c" && e.ctrlKey) {
      e.preventDefault();
      wsRef.current?.send("\x03");
    } else if (e.key === "l" && e.ctrlKey) {
      e.preventDefault();
      setLines([]);
    }
  }

  return (
    <div
      className="term-overlay"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="term-modal">
        <div className="term-header">
          <div className="term-header-left">
            <span className="term-label">Terminal</span>
            <span className="term-name">{workload.name}</span>
            <span className="term-ns">{workload.namespace}</span>
          </div>
          <div className="term-header-right">
            <span className={`term-dot ${connected ? "term-dot-on" : "term-dot-off"}`} />
            <span className="term-status-txt">{connected ? "Connected" : "Disconnected"}</span>
            <button className="term-close" onClick={onClose}>✕</button>
          </div>
        </div>

        {error && <div className="term-error">{error}</div>}

        <div className="term-output" ref={outputRef}>
          <pre className="term-pre">{lines.join("")}</pre>
        </div>

        <div className="term-input-row">
          <span className="term-prompt">$</span>
          <input
            className="term-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!connected}
            autoFocus
            autoComplete="off"
            spellCheck={false}
            placeholder={connected ? "Type a command and press Enter…" : "Connecting…"}
          />
        </div>
        <div className="term-hint">Ctrl+C to interrupt · Ctrl+L to clear · click outside to close</div>
      </div>
    </div>
  );
}
