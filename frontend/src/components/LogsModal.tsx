import { useCallback, useEffect, useRef, useState } from "react";
import "./LogsModal.css";

interface Props {
  workloadName: string;
  namespace: string;
  onClose: () => void;
}

export default function LogsModal({ workloadName, namespace, onClose }: Props) {
  const [lines, setLines]       = useState<string[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError]       = useState<string | null>(null);
  const [tail, setTail]         = useState(200);
  const [filter, setFilter]     = useState("");
  const [autoScroll, setAutoScroll] = useState(true);
  const preRef = useRef<HTMLPreElement>(null);
  const wsRef  = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    wsRef.current?.close();
    setLines([]);
    setError(null);
    const token = localStorage.getItem("access_token") ?? "";
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${window.location.host}/api/v1/ws/logs/${encodeURIComponent(workloadName)}?namespace=${encodeURIComponent(namespace)}&tail=${tail}&token=${encodeURIComponent(token)}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;
    ws.onopen  = () => setConnected(true);
    ws.onmessage = (e: MessageEvent<string>) => {
      const incoming = (e.data as string).split("\n");
      setLines((prev) => [...prev, ...incoming].slice(-3000));
    };
    ws.onerror  = () => setError("WebSocket connection failed");
    ws.onclose  = (e) => {
      setConnected(false);
      if (e.code === 4001) setError("Authentication failed");
    };
  }, [workloadName, namespace, tail]);

  useEffect(() => {
    connect();
    return () => { wsRef.current?.close(); };
  }, [connect]);

  useEffect(() => {
    if (autoScroll && preRef.current) {
      preRef.current.scrollTop = preRef.current.scrollHeight;
    }
  }, [lines, autoScroll]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const displayed = filter
    ? lines.filter((l) => l.toLowerCase().includes(filter.toLowerCase()))
    : lines;

  return (
    <div className="lm-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="lm-modal">
        <div className="lm-header">
          <div className="lm-title">
            <span className="lm-name">{workloadName}</span>
            <span className={`lm-live-badge ${connected ? "lm-live" : "lm-off"}`}>
              {connected ? "● LIVE" : "○ offline"}
            </span>
          </div>
          <div className="lm-controls">
            <input
              className="lm-filter"
              placeholder="Filter…"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
            <select className="lm-tail-sel" value={tail} onChange={(e) => { setTail(Number(e.target.value)); }}>
              <option value={50}>Last 50</option>
              <option value={200}>Last 200</option>
              <option value={500}>Last 500</option>
            </select>
            <button className="lm-btn-sm" onClick={connect}>Reconnect</button>
            <button className="lm-btn-sm" onClick={() => setLines([])}>Clear</button>
            <label className="lm-scroll-toggle">
              <input type="checkbox" checked={autoScroll} onChange={(e) => setAutoScroll(e.target.checked)} />
              Auto-scroll
            </label>
            <button className="lm-btn-close" onClick={onClose}>✕</button>
          </div>
        </div>
        <div className="lm-body">
          {error ? (
            <div className="lm-error">{error}</div>
          ) : (
            <pre className="lm-pre" ref={preRef}>
              {displayed.join("\n") || "(no output yet…)"}
            </pre>
          )}
        </div>
        <div className="lm-footer">
          <span>{lines.length} lines</span>
          {filter && <span> · {displayed.length} matching</span>}
        </div>
      </div>
    </div>
  );
}
