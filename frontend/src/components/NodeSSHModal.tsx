import { useEffect, useRef, useState } from "react";
import type { NodeHealth } from "../types/node";
import "./NodeSSHModal.css";

interface Props {
  node: NodeHealth;
  onClose: () => void;
}

export default function NodeSSHModal({ node, onClose }: Props) {
  const [lines, setLines]         = useState<string[]>([]);
  const [input, setInput]         = useState("");
  const [connected, setConnected] = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const wsRef     = useRef<WebSocket | null>(null);
  const outputRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token") ?? "";
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${window.location.host}/api/v1/ws/ssh/${encodeURIComponent(node.ip_address)}?token=${encodeURIComponent(token)}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;
    ws.onopen    = () => { setConnected(true); };
    ws.onmessage = (e: MessageEvent<string>) => { setLines((p) => [...p, e.data]); };
    ws.onclose   = (e) => {
      setConnected(false);
      setLines((p) => [...p, "\r\n[session closed]\r\n"]);
      if (e.code === 4001) setError("Authentication failed");
    };
    ws.onerror   = () => setError("Connection failed. Check that the node is reachable via SSH.");
    return () => ws.close();
  }, [node.ip_address]);

  useEffect(() => {
    if (outputRef.current) outputRef.current.scrollTop = outputRef.current.scrollHeight;
  }, [lines]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

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
    <div className="nssh-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="nssh-modal">
        <div className="nssh-header">
          <div className="nssh-header-left">
            <span className="nssh-label">SSH</span>
            <span className="nssh-name">{node.node_name}</span>
            <span className="nssh-ip">{node.ip_address}</span>
          </div>
          <div className="nssh-header-right">
            <span className={`nssh-dot ${connected ? "nssh-dot-on" : "nssh-dot-off"}`} />
            <span className="nssh-status">{connected ? "Connected" : "Disconnected"}</span>
            <button className="nssh-close" onClick={onClose}>&#x2715;</button>
          </div>
        </div>
        {error && <div className="nssh-error">{error}</div>}
        <div className="nssh-output" ref={outputRef}>
          <pre className="nssh-pre">{lines.join("")}</pre>
        </div>
        <div className="nssh-input-row">
          <span className="nssh-prompt">$</span>
          <input
            className="nssh-input"
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
        <div className="nssh-hint">Ctrl+C to interrupt &middot; Ctrl+L to clear &middot; Esc or click outside to close</div>
      </div>
    </div>
  );
}
