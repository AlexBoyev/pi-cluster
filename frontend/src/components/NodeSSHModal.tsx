import { useEffect, useRef, useState } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";
import type { NodeHealth } from "../types/node";
import "./NodeSSHModal.css";

interface Props {
  node: NodeHealth;
  onClose: () => void;
}

export default function NodeSSHModal({ node, onClose }: Props) {
  const [connected, setConnected] = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const termRef      = useRef<Terminal | null>(null);

  useEffect(() => {
    const term = new Terminal({
      cursorBlink: true,
      fontSize: 13,
      fontFamily: '"Cascadia Code", "Fira Code", "Consolas", monospace',
      theme: {
        background: "#0d1117",
        foreground: "#c9d1d9",
        cursor:     "#e6edf3",
        selectionBackground: "#264f78",
      },
      scrollback: 5000,
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    if (containerRef.current) {
      term.open(containerRef.current);
      fit.fit();
    }
    termRef.current = term;

    let alive = true;
    const token = localStorage.getItem("access_token") ?? "";
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const url   = `${proto}://${window.location.host}/api/v1/ws/ssh/${encodeURIComponent(node.ip_address)}?token=${encodeURIComponent(token)}`;
    const ws    = new WebSocket(url);

    ws.onopen    = () => { if (alive) setConnected(true); };
    ws.onmessage = (e: MessageEvent<string>) => { if (alive) term.write(e.data); };
    ws.onclose   = (e) => {
      if (!alive) return;
      setConnected(false);
      term.write("\r\n\x1b[33m[session closed]\x1b[0m\r\n");
      if (e.code === 4001) setError("Authentication failed");
    };
    ws.onerror   = () => {
      if (alive) setError("Connection failed. Check that the node is reachable via SSH.");
    };

    term.onData((data) => { ws.send(data); });

    const onResize = () => { if (alive) fit.fit(); };
    window.addEventListener("resize", onResize);

    return () => {
      alive = false;
      ws.close();
      term.dispose();
      window.removeEventListener("resize", onResize);
    };
  }, [node.ip_address]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

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
        <div className="nssh-term" ref={containerRef} />
        <div className="nssh-hint">Type directly into the terminal &middot; Ctrl+C interrupt &middot; Esc or click outside to close</div>
      </div>
    </div>
  );
}
