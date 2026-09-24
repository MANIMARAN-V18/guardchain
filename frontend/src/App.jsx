import { useState } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import "./App.css";

function App() {
  const [walletAddress, setWalletAddress] = useState("");
  const [elements, setElements] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleTrace = async () => {
    if (!walletAddress) return;

    setLoading(true);
    setError("");
    setElements([]);

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/trace/${walletAddress}`
      );
      const data = await response.json();

      // Convert backend edges into Cytoscape's node/edge format
      const nodesMap = new Map();
      const edges = [];

      data.edges.forEach((edge) => {
        if (!nodesMap.has(edge.from)) {
          nodesMap.set(edge.from, {
            data: { id: edge.from, label: edge.from.slice(0, 8) + "...", isExchange: false },
          });
        }
        if (!nodesMap.has(edge.to)) {
          nodesMap.set(edge.to, {
            data: { id: edge.to, label: edge.to.slice(0, 8) + "...", isExchange: edge.is_exchange },
          });
        } else if (edge.is_exchange) {
          nodesMap.get(edge.to).data.isExchange = true;
        }

        edges.push({
          data: {
            source: edge.from,
            target: edge.to,
            label: `${edge.value_eth.toFixed(4)} ETH`,
          },
        });
      });

      setElements([...nodesMap.values(), ...edges]);
    } catch (err) {
      setError("Failed to fetch trace. Is the backend server running?");
    } finally {
      setLoading(false);
    }
  };

  const layout = { name: "breadthfirst", directed: true, spacingFactor: 1.5 };

  const stylesheet = [
    {
      selector: "node",
      style: {
        label: "data(label)",
        "background-color": "#4A90D9",
        color: "#fff",
        "font-size": "10px",
        "text-valign": "center",
        "text-halign": "center",
        width: "60px",
        height: "60px",
      },
    },
    {
      selector: "node[?isExchange]",
      style: {
        "background-color": "#E74C3C",
        width: "70px",
        height: "70px",
      },
    },
    {
      selector: "edge",
      style: {
        label: "data(label)",
        "font-size": "8px",
        "curve-style": "bezier",
        "target-arrow-shape": "triangle",
        "line-color": "#999",
        "target-arrow-color": "#999",
        width: 2,
      },
    },
  ];

  return (
    <div style={{ padding: "20px", fontFamily: "sans-serif" }}>
      <h1>GuardChain — Wallet Trace</h1>

      <div style={{ marginBottom: "20px" }}>
        <input
          type="text"
          placeholder="Enter wallet address (0x...)"
          value={walletAddress}
          onChange={(e) => setWalletAddress(e.target.value)}
          style={{ width: "400px", padding: "8px", marginRight: "10px" }}
        />
        <button onClick={handleTrace} disabled={loading} style={{ padding: "8px 16px" }}>
          {loading ? "Tracing..." : "Trace Wallet"}
        </button>
      </div>

      {error && <p style={{ color: "red" }}>{error}</p>}

      {elements.length > 0 && (
        <CytoscapeComponent
          elements={elements}
          style={{ width: "100%", height: "600px", border: "1px solid #ccc" }}
          layout={layout}
          stylesheet={stylesheet}
        />
      )}
    </div>
  );
}

export default App;