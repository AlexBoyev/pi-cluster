import { useEffect, useState } from "react";
import { getNodes } from "./api/nodes";
import type { Node } from "./types/node";

export default function App() {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getNodes()
      .then(setNodes)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main>
      <h1>Pi Cluster</h1>
      {loading && <p>Loading...</p>}
      {error && <p>Error: {error}</p>}
      <ul>
        {nodes.map((node) => (
          <li key={node.id}>
            {node.name} — {node.ip_address} — {node.status}
          </li>
        ))}
      </ul>
    </main>
  );
}
