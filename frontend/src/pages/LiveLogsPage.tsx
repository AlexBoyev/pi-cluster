import { useCallback, useEffect, useRef, useState } from "react";
import { listPods } from "../api/pods";
import { apiFetch } from "../api/client";
import type { PodBasic } from "../types/pod";
import "./LiveLogsPage.css";

interface NsInfo { name: string; }

export default function LiveLogsPage() {
  const [namespaces, setNamespaces] = useState<string[]>([]);
  const [pods, setPods]             = useState<PodBasic[]>([]);
  const [selectedNs, setSelectedNs]           = useState("pi-apps");
  const [selectedPod, setSelectedPod]         = useState("");
  const [selectedContainer, setSelectedContainer] = useState("");
  const [tail, setTail]             = useState(200);
  const [lines, setLines]           = useState<string[]>([]);
  const [connected, setConnected]   = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [filter, setFilter]         = useState("");
  const [autoScroll, setAutoScroll] = useState(true);
  const [error, setError]           = useState<string | null>(null);
  const wsRef  = useRef<WebSocket | null>(null);
  const preRef = useRef<HTMLPreElement>(null);

  useEffect(() => {
    apiFetch<NsInfo[]>("/namespaces/").then((ns) => {
      const names = ns.map((n) => n.name).sort();
      setNamespaces(names);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedNs) return;
    setPods([]);
    setSelectedPod("");
    setSelectedContainer("");
    listPods(selectedNs).then((ps) => {
      setPods(ps);
      if (ps.length > 0) {
        setSelectedPod(ps[0].name);
        setSelectedContainer(ps[0].containers[0] ?? "");
      }
    }).catch(() => {});
  }, [selectedNs]);

  useEffect(() => {
    const pod = pods.find((p) => p.name === selectedPod);
    setSelectedContainer(pod?.containers[0] ?? "");
  }, [selectedPod, pods]);

  useEffect(() => {
    if (autoScroll && preRef.current) {
      preRef.current.scrollTop = preRef.current.scrollHeight;
    }
  }, [lines, autoScroll]);

  useEffect(() => () => { wsRef.current?.close(); }, []);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setConnected(false);
    setConnecting(false);
  }, []);

  const connect = useCallback(() => {
    if (!selectedPod) return;
    disconnect();
    setLines([]);
    setError(null);
    setConnecting(true);
    const token = localStorage.getItem("access_token") ?? "";
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const containerParam = selectedContainer ? `&container=${encodeURIComponent(selectedContainer)}` : "";
    const url = `${proto}://${window.location.host}/api/v1/ws/logs/${encodeURIComponent(selectedPod)}`
      + `?namespace=${encodeURIComponent(selectedNs)}`
      + `&pod=${encodeURIComponent(selectedPod)}`
      + `&tail=${tail}`
      + `&token=${encodeURIComponent(token)}`
      + containerParam;
    const ws = new WebSocket(url);
    wsRef.current = ws;
    ws.onopen    = () => { setConnected(true); setConnecting(false); };
    ws.onmessage = (e: MessageEvent<string>) => {
      setLines((prev) => [...prev, ...e.data.split("\n")].slice(-5000));
    };
    ws.onerror   = () => { setError("WebSocket connection failed"); setConnecting(false); };
    ws.onclose   = (ev) => {
      setConnected(false);
      setConnecting(false);
      if (ev.code === 4001) setError("Authentication failed — please log in again");
    };
  }, [selectedPod, selectedNs, selectedContainer, tail, disconnect]);

  const containers = pods.find((p) => p.name === selectedPod)?.containers ?? [];
  const displayed  = filter
    ? lines.filter((l) => l.toLowerCase().includes(filter.toLowerCase()))
    : lines;

  return (
    <div className="ll-page">

      <div className="ll-toolbar">
        <div className="ll-selectors">
          <div className="ll-field">
            <label className="ll-lbl">Namespace</label>
            <select
              className="ll-sel"
              value={selectedNs}
              onChange={(e) => setSelectedNs(e.target.value)}
              disabled={connected}
            >
              {namespaces.map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>

          <div className="ll-field">
            <label className="ll-lbl">Pod</label>
            <select
              className="ll-sel ll-sel-pod"
              value={selectedPod}
              onChange={(e) => setSelectedPod(e.target.value)}
              disabled={connected || pods.length === 0}
            >
              {pods.length === 0
                ? <option value="">No pods</option>
                : pods.map((p) => (
                    <option key={p.name} value={p.name}>
                      {p.name}
                    </option>
                  ))
              }
            </select>
          </div>

          {containers.length > 1 && (
            <div className="ll-field">
              <label className="ll-lbl">Container</label>
              <select
                className="ll-sel"
                value={selectedContainer}
                onChange={(e) => setSelectedContainer(e.target.value)}
                disabled={connected}
              >
                {containers.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          )}

          <div className="ll-field">
            <label className="ll-lbl">Tail lines</label>
            <select
              className="ll-sel ll-sel-tail"
              value={tail}
              onChange={(e) => setTail(Number(e.target.value))}
              disabled={connected}
            >
              <option value={50}>50</option>
              <option value={200}>200</option>
              <option value={500}>500</option>
              <option value={1000}>1000</option>
            </select>
          </div>
        </div>

        <div className="ll-actions">
          <span className={`ll-badge ${connected ? "ll-live" : "ll-off"}`}>
            {connected ? "● LIVE" : "○ offline"}
          </span>
          {connected ? (
            <button className="ll-btn-disconnect" onClick={disconnect}>Disconnect</button>
          ) : (
            <button
              className="ll-btn-connect"
              onClick={connect}
              disabled={!selectedPod || connecting}
            >
              {connecting ? "Connecting…" : "Connect"}
            </button>
          )}
        </div>
      </div>

      {error && <div className="ll-error">{error}</div>}

      <div className="ll-log-bar">
        <input
          className="ll-filter"
          placeholder="Filter lines…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        <span className="ll-line-count">
          {lines.length} lines{filter ? ` · ${displayed.length} matching` : ""}
        </span>
        <label className="ll-autoscroll">
          <input type="checkbox" checked={autoScroll} onChange={(e) => setAutoScroll(e.target.checked)} />
          Auto-scroll
        </label>
        <button className="ll-btn-sm" onClick={() => setLines([])}>Clear</button>
      </div>

      <div className="ll-log-wrap">
        <pre className="ll-pre" ref={preRef}>
          {displayed.length > 0
            ? displayed.join("\n")
            : connected
              ? "(waiting for output…)"
              : "(not connected — select a pod and click Connect)"}
        </pre>
      </div>

    </div>
  );
}
