import React, { useState, useEffect, useRef } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import {
  Shield,
  Search,
  FileText,
  Network,
  AlertTriangle,
  Clock,
  Download,
  Copy,
  CheckCircle2,
  ExternalLink,
  ChevronRight,
  RefreshCw,
  Layers,
  Database,
  ArrowRight,
  Flame,
  Activity,
  Maximize2,
  HelpCircle,
  FolderOpen
} from "lucide-react";
import "./App.css";

// API Base URL config (Auto-detects localhost vs production)
const API_BASE =
  window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://127.0.0.1:8000"
    : "https://guardchain.onrender.com";

// Sample high-profile fraud cases for quick demo testing
const SAMPLE_CASES = [
  {
    name: "Ethereum: Exchange Exit (Binance)",
    chain: "Ethereum",
    address: "0xDFd5293D8e347dFe59E90eFd55b2956a1343963d",
  },
  {
    name: "Ethereum: Multi-Hop Layering",
    chain: "Ethereum",
    address: "0x28C6c06298d514Db089934071355E5743bf21d60",
  },
  {
    name: "Tron: USDT Cyber Scam Rail",
    chain: "Tron",
    address: "TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH",
  },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("trace"); // 'trace' | 'clusters' | 'notice' | 'history'
  const [walletAddress, setWalletAddress] = useState("");
  const [selectedChain, setSelectedChain] = useState("Ethereum");
  const [hops, setHops] = useState(4);
  
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [error, setError] = useState("");
  
  const [traceData, setTraceData] = useState(null);
  const [elements, setElements] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [copiedText, setCopiedText] = useState("");
  
  const [clustersData, setClustersData] = useState(null);
  const [loadingClusters, setLoadingClusters] = useState(false);
  
  const cyRef = useRef(null);

  // Staged loading progress simulation for responsive feedback during long queries
  useEffect(() => {
    let interval;
    if (loading) {
      setLoadingStep(1);
      interval = setInterval(() => {
        setLoadingStep((prev) => (prev < 4 ? prev + 1 : prev));
      }, 2500);
    } else {
      setLoadingStep(0);
    }
    return () => clearInterval(interval);
  }, [loading]);

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopiedText(text);
    setTimeout(() => setCopiedText(""), 2000);
  };

  // Main Trace Execution
  const handleTrace = async (overrideAddress = null, overrideChain = null) => {
    const targetAddr = (overrideAddress || walletAddress).trim();
    const chainToUse = overrideChain || selectedChain;

    if (!targetAddr) {
      setError("Please enter a valid wallet address.");
      return;
    }

    setLoading(true);
    setError("");
    setSelectedNode(null);
    setTraceData(null);
    setElements([]);

    try {
      const res = await fetch(
        `${API_BASE}/trace/${encodeURIComponent(targetAddr)}?chain=${chainToUse}&hops=${hops}`
      );
      if (!res.ok) {
        throw new Error(`Server returned HTTP status ${res.status}`);
      }
      const data = await res.json();
      setTraceData(data);

      // Convert edges into Cytoscape nodes and edges
      const nodesMap = new Map();
      const cyEdges = [];
      const isTron = chainToUse === "Tron";
      const unit = isTron ? "USDT" : "ETH";

      // Register root node
      nodesMap.set(data.wallet, {
        data: {
          id: data.wallet,
          label: `${data.wallet.slice(0, 6)}...${data.wallet.slice(-4)}`,
          fullAddress: data.wallet,
          isRoot: true,
          isExchange: false,
          exchangeLabel: null,
          isCycled: data.cycle_detection?.cycled_wallets?.includes(data.wallet.toLowerCase()),
          chain: chainToUse,
        },
      });

      data.edges.forEach((edge, idx) => {
        // Source node
        if (!nodesMap.has(edge.from)) {
          nodesMap.set(edge.from, {
            data: {
              id: edge.from,
              label: `${edge.from.slice(0, 6)}...${edge.from.slice(-4)}`,
              fullAddress: edge.from,
              isRoot: edge.from.toLowerCase() === data.wallet.toLowerCase(),
              isExchange: false,
              exchangeLabel: null,
              isCycled: data.cycle_detection?.cycled_wallets?.includes(edge.from.toLowerCase()),
              chain: chainToUse,
            },
          });
        }

        // Target node
        if (!nodesMap.has(edge.to)) {
          nodesMap.set(edge.to, {
            data: {
              id: edge.to,
              label: edge.exchange_label ? edge.exchange_label : `${edge.to.slice(0, 6)}...${edge.to.slice(-4)}`,
              fullAddress: edge.to,
              isRoot: false,
              isExchange: edge.is_exchange,
              exchangeLabel: edge.exchange_label,
              isCycled: data.cycle_detection?.cycled_wallets?.includes(edge.to.toLowerCase()),
              chain: chainToUse,
            },
          });
        } else if (edge.is_exchange) {
          const existing = nodesMap.get(edge.to);
          existing.data.isExchange = true;
          if (edge.exchange_label) existing.data.exchangeLabel = edge.exchange_label;
        }

        // Edge
        cyEdges.push({
          data: {
            id: `edge-${idx}-${edge.from}-${edge.to}`,
            source: edge.from,
            target: edge.to,
            label: `${edge.value.toFixed(2)} ${unit}`,
            value: edge.value,
            hop: edge.hop,
          },
        });
      });

      setElements([...nodesMap.values(), ...cyEdges]);
    } catch (err) {
      console.error(err);
      setError(`Failed to perform trace: ${err.message}. Ensure backend is running.`);
    } finally {
      setLoading(false);
    }
  };

  // Fetch Cross-Investigation Clusters
  const fetchClusters = async () => {
    setLoadingClusters(true);
    try {
      const res = await fetch(`${API_BASE}/cases/clusters`);
      const data = await res.json();
      setClustersData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingClusters(false);
    }
  };

  useEffect(() => {
    if (activeTab === "clusters" && !clustersData) {
      fetchClusters();
    }
  }, [activeTab]);

  // Cytoscape setup
  const layout = {
    name: "breadthfirst",
    directed: true,
    padding: 30,
    spacingFactor: 1.4,
    avoidOverlap: true,
  };

  const cytoscapeStylesheet = [
    {
      selector: "node",
      style: {
        label: "data(label)",
        "background-color": "#1e293b",
        "border-color": "#38bdf8",
        "border-width": 2,
        color: "#f8fafc",
        "font-size": "10px",
        "font-family": "JetBrains Mono, monospace",
        "text-valign": "bottom",
        "text-margin-y": 6,
        width: 48,
        height: 48,
        "transition-property": "background-color, border-color, width, height",
        "transition-duration": "0.2s",
      },
    },
    {
      selector: "node[?isRoot]",
      style: {
        "background-color": "#0284c7",
        "border-color": "#38bdf8",
        "border-width": 4,
        width: 60,
        height: 60,
        shape: "round-hexagon",
      },
    },
    {
      selector: "node[?isExchange]",
      style: {
        "background-color": "#dc2626",
        "border-color": "#f87171",
        "border-width": 3,
        width: 58,
        height: 58,
        shape: "diamond",
      },
    },
    {
      selector: "node[?isCycled]",
      style: {
        "border-color": "#f59e0b",
        "border-width": 4,
        "border-style": "dashed",
      },
    },
    {
      selector: "node:selected",
      style: {
        "border-color": "#ffffff",
        "border-width": 4,
        "background-color": "#0284c7",
      },
    },
    {
      selector: "edge",
      style: {
        label: "data(label)",
        "font-size": "9px",
        "font-family": "JetBrains Mono, monospace",
        color: "#94a3b8",
        "text-background-color": "#0b1329",
        "text-background-opacity": 0.85,
        "text-background-padding": 3,
        "text-background-shape": "roundrectangle",
        "curve-style": "bezier",
        "target-arrow-shape": "triangle",
        "line-color": "#334155",
        "target-arrow-color": "#38bdf8",
        width: 2,
        "arrow-scale": 1.2,
      },
    },
  ];

  // Freeze Window Severity Colors & Badges
  const getSeverityBadge = (level) => {
    switch (level) {
      case "Critical":
        return {
          bg: "bg-red-500/20 text-red-400 border-red-500/40",
          pill: "bg-red-600 text-white",
          border: "border-red-500",
          glow: "glow-crimson",
        };
      case "High":
        return {
          bg: "bg-orange-500/20 text-orange-400 border-orange-500/40",
          pill: "bg-orange-600 text-white",
          border: "border-orange-500",
          glow: "glow-amber",
        };
      case "Moderate":
        return {
          bg: "bg-amber-500/20 text-amber-400 border-amber-500/40",
          pill: "bg-amber-600 text-white",
          border: "border-amber-500",
          glow: "glow-amber",
        };
      default:
        return {
          bg: "bg-emerald-500/20 text-emerald-400 border-emerald-500/40",
          pill: "bg-emerald-600 text-white",
          border: "border-emerald-500",
          glow: "glow-cyan",
        };
    }
  };

  const loadingMessages = [
    "Establishing connection to blockchain nodes...",
    "Crawling outgoing transactions & peeling chains (Hop 1-4)...",
    "Checking exchange registry & high-fan-in deposit heuristics...",
    "Computing Freeze Window Score & Isolation Forest anomaly metrics...",
  ];

  return (
    <div className="min-h-screen bg-[#070c18] text-slate-100 flex flex-col">
      {/* Top Law Enforcement & Forensic Navigation Bar */}
      <header className="border-b border-slate-800 bg-[#0b1329]/90 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 border border-cyan-400/30">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg tracking-wider text-white">GUARDCHAIN</span>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                  v2.0 PRO
                </span>
                <span className="hidden md:inline px-1.5 py-0.5 rounded text-[10px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20">
                  SIH2026 PS-26183
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block">
                Autonomous Multi-Chain Fraud Tracing & Freeze Window Intelligence
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center gap-1 sm:gap-2">
            <button
              onClick={() => setActiveTab("trace")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition ${
                activeTab === "trace"
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
              }`}
            >
              <Network className="w-3.5 h-3.5" />
              Trace Canvas
            </button>

            <button
              onClick={() => setActiveTab("clusters")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition ${
                activeTab === "clusters"
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
              }`}
            >
              <Database className="w-3.5 h-3.5" />
              Syndicate Clusters
            </button>

            <button
              onClick={() => setActiveTab("notice")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition ${
                activeTab === "notice"
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              Statutory Notice (Sec 91/94)
            </button>
          </nav>

          {/* Backend Status Indicator */}
          <div className="hidden lg:flex items-center gap-2 text-xs text-slate-400 font-mono">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
            <span>Neo4j Aura: Connected</span>
          </div>
        </div>
      </header>

      {/* Main Body Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 flex flex-col gap-6">
        {/* TAB 1: Trace Canvas */}
        {activeTab === "trace" && (
          <>
            {/* Investigation Search & Control Deck */}
            <div className="p-5 rounded-2xl bg-[#0b1329] border border-slate-800 shadow-xl shadow-black/40 flex flex-col gap-4">
              <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
                {/* Chain Selector */}
                <div className="flex items-center gap-2 bg-slate-900/80 p-1.5 rounded-xl border border-slate-800">
                  <span className="text-xs font-medium text-slate-400 px-2">Chain:</span>
                  <button
                    onClick={() => setSelectedChain("Ethereum")}
                    className={`px-3 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
                      selectedChain === "Ethereum"
                        ? "bg-blue-600 text-white shadow-md shadow-blue-500/30"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <span className="w-2 h-2 rounded-full bg-blue-300"></span>
                    Ethereum (ETH)
                  </button>
                  <button
                    onClick={() => setSelectedChain("Tron")}
                    className={`px-3 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
                      selectedChain === "Tron"
                        ? "bg-red-600 text-white shadow-md shadow-red-500/30"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <span className="w-2 h-2 rounded-full bg-red-300"></span>
                    Tron (USDT TRC-20)
                  </button>
                </div>

                {/* Quick Sample Selector */}
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs text-slate-400 flex items-center gap-1">
                    <Flame className="w-3.5 h-3.5 text-amber-400" />
                    Demo Presets:
                  </span>
                  {SAMPLE_CASES.map((sc, i) => (
                    <button
                      key={i}
                      onClick={() => {
                        setWalletAddress(sc.address);
                        setSelectedChain(sc.chain);
                        handleTrace(sc.address, sc.chain);
                      }}
                      className="px-2.5 py-1 rounded-lg text-[11px] bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 border border-slate-700/60 transition"
                    >
                      {sc.name}
                    </button>
                  ))}
                </div>
              </div>

              {/* Input Form & Trace Trigger */}
              <div className="flex flex-col sm:flex-row items-center gap-3">
                <div className="relative flex-1 w-full">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder={
                      selectedChain === "Ethereum"
                        ? "Enter Ethereum suspect address (0x...)"
                        : "Enter Tron TRC20 suspect address (T...)"
                    }
                    value={walletAddress}
                    onChange={(e) => setWalletAddress(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleTrace()}
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-sm font-mono text-white placeholder:text-slate-500 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 transition"
                  />
                </div>

                <div className="flex items-center gap-3 w-full sm:w-auto">
                  <div className="flex items-center gap-2 bg-slate-900 px-3 py-2 rounded-xl border border-slate-700 text-xs text-slate-400 font-mono">
                    <span>Depth:</span>
                    <select
                      value={hops}
                      onChange={(e) => setHops(Number(e.target.value))}
                      className="bg-transparent text-white font-bold focus:outline-none cursor-pointer"
                    >
                      <option value={2} className="bg-slate-900">2 Hops</option>
                      <option value={3} className="bg-slate-900">3 Hops</option>
                      <option value={4} className="bg-slate-900">4 Hops</option>
                      <option value={5} className="bg-slate-900">5 Hops</option>
                    </select>
                  </div>

                  <button
                    onClick={() => handleTrace()}
                    disabled={loading}
                    className="flex-1 sm:flex-none px-6 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-cyan-500/20 disabled:opacity-50 transition cursor-pointer"
                  >
                    {loading ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin text-slate-950" />
                        Analyzing...
                      </>
                    ) : (
                      <>
                        <Search className="w-4 h-4 text-slate-950" />
                        Trace Wallet
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Loading Skeleton & Stepper */}
              {loading && (
                <div className="p-4 rounded-xl bg-slate-900/90 border border-cyan-500/30 flex flex-col gap-3 animate-pulse">
                  <div className="flex items-center justify-between text-xs text-cyan-400 font-mono">
                    <span className="flex items-center gap-2">
                      <Activity className="w-4 h-4 animate-spin" />
                      {loadingMessages[loadingStep - 1] || "Forensic tracing in progress..."}
                    </span>
                    <span>Step {loadingStep} of 4</span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-cyan-400 h-1.5 transition-all duration-500"
                      style={{ width: `${(loadingStep / 4) * 100}%` }}
                    ></div>
                  </div>
                </div>
              )}

              {/* Error Message */}
              {error && (
                <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}
            </div>

            {/* Trace Analytics & Graph View */}
            {traceData && (
              <div className="flex flex-col gap-6">
                {/* 1. Forensic Intelligence Metrics Header */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Freeze Window Urgency Score Card */}
                  {(() => {
                    const fw = traceData.freeze_window;
                    const badge = getSeverityBadge(fw?.level);
                    return (
                      <div
                        className={`p-5 rounded-2xl bg-[#0b1329] border ${badge.border} ${badge.glow} flex flex-col justify-between`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                              Freeze Window Score
                            </span>
                            <div className="flex items-baseline gap-2 mt-1">
                              <span className="text-3xl font-black text-white font-mono">
                                {fw?.score}
                              </span>
                              <span className="text-slate-400 text-sm font-mono">/100</span>
                              <span
                                className={`px-2 py-0.5 rounded text-xs font-bold font-mono uppercase ${badge.pill}`}
                              >
                                {fw?.level}
                              </span>
                            </div>
                          </div>
                          <Clock className={`w-6 h-6 ${badge.bg}`} />
                        </div>

                        <div className="mt-4 pt-3 border-t border-slate-800 text-xs text-slate-300">
                          <p className="font-semibold text-cyan-300 mb-1">
                            Action Window: {fw?.recommended_action_window}
                          </p>
                          <p className="text-[11px] text-slate-400 leading-relaxed">
                            {fw?.reason}
                          </p>
                        </div>
                      </div>
                    );
                  })()}

                  {/* Statistical Anomaly Score (Isolation Forest) */}
                  {(() => {
                    const an = traceData.statistical_anomaly;
                    return (
                      <div className="p-5 rounded-2xl bg-[#0b1329] border border-slate-800 flex flex-col justify-between">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                              Statistical Anomaly Rating
                            </span>
                            <div className="flex items-baseline gap-2 mt-1">
                              <span className="text-3xl font-black text-amber-400 font-mono">
                                {an?.anomaly_score || 0}
                              </span>
                              <span className="text-slate-400 text-sm font-mono">/100</span>
                              <span className="px-2 py-0.5 rounded text-xs font-mono font-medium bg-amber-500/20 text-amber-300 border border-amber-500/30">
                                {an?.verdict || "Standard"}
                              </span>
                            </div>
                          </div>
                          <Activity className="w-6 h-6 text-amber-400" />
                        </div>

                        <div className="mt-4 pt-3 border-t border-slate-800 text-xs text-slate-300">
                          <p className="text-[11px] text-slate-400 mb-1 font-mono">
                            Method: {an?.method}
                          </p>
                          <ul className="text-[11px] text-slate-400 list-disc list-inside space-y-0.5">
                            {an?.indicators?.slice(0, 2).map((ind, i) => (
                              <li key={i}>{ind}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    );
                  })()}

                  {/* Fast Action & Report Exporter */}
                  <div className="p-5 rounded-2xl bg-[#0b1329] border border-slate-800 flex flex-col justify-between">
                    <div>
                      <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                        Investigative Actions
                      </span>
                      <div className="mt-2 text-xs text-slate-300">
                        <p className="text-slate-400 text-[11px] mb-3">
                          Generate court-admissible forensic PDF dossiers and Section 91 CrPC requisitions.
                        </p>
                      </div>
                    </div>

                    <div className="flex flex-col gap-2">
                      <a
                        href={`${API_BASE}/trace/${encodeURIComponent(
                          traceData.wallet
                        )}/report?chain=${traceData.chain}`}
                        target="_blank"
                        rel="noreferrer"
                        className="w-full py-2 px-3 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs flex items-center justify-center gap-2 shadow-md transition"
                      >
                        <Download className="w-3.5 h-3.5" />
                        Download PDF Dossier
                      </a>

                      <button
                        onClick={() => setActiveTab("notice")}
                        className="w-full py-2 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-cyan-300 font-semibold text-xs flex items-center justify-center gap-2 border border-slate-700 transition"
                      >
                        <FileText className="w-3.5 h-3.5" />
                        Draft Statutory Notice
                      </button>
                    </div>
                  </div>
                </div>

                {/* Circular Laundering Warning Banner (if detected) */}
                {traceData.cycle_detection?.circular_pattern_detected && (
                  <div className="p-4 rounded-xl bg-amber-500/15 border border-amber-500/40 text-amber-300 flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 shrink-0 text-amber-400 mt-0.5" />
                    <div>
                      <h4 className="text-sm font-bold flex items-center gap-2">
                        Circular Laundering Cycle Detected!
                      </h4>
                      <p className="text-xs text-amber-200/90 mt-1 leading-relaxed">
                        {traceData.cycle_detection.summary} Wallets involved:{" "}
                        {traceData.cycle_detection.cycled_wallets
                          .map((w) => `${w.slice(0, 6)}...${w.slice(-4)}`)
                          .join(", ")}
                      </p>
                    </div>
                  </div>
                )}

                {/* 2. Interactive Cytoscape Graph Canvas & Inspector */}
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
                  {/* Graph Canvas */}
                  <div className="lg:col-span-3 rounded-2xl bg-[#0b1329] border border-slate-800 overflow-hidden relative shadow-2xl">
                    <div className="absolute top-4 left-4 z-10 flex items-center gap-2 bg-slate-900/90 backdrop-blur px-3 py-1.5 rounded-xl border border-slate-800 text-xs font-mono text-slate-300">
                      <Network className="w-3.5 h-3.5 text-cyan-400" />
                      <span>
                        Nodes: {elements.filter((e) => !e.data.source).length} | Edges:{" "}
                        {elements.filter((e) => e.data.source).length}
                      </span>
                    </div>

                    <div className="absolute top-4 right-4 z-10 flex items-center gap-2">
                      <button
                        onClick={() => cyRef.current && cyRef.current.fit()}
                        className="p-2 rounded-lg bg-slate-900/90 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs flex items-center gap-1 transition"
                        title="Fit View"
                      >
                        <Maximize2 className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <div className="w-full h-[520px] bg-[#070c18] grid-bg">
                      <CytoscapeComponent
                        elements={elements}
                        style={{ width: "100%", height: "100%" }}
                        layout={layout}
                        stylesheet={cytoscapeStylesheet}
                        cy={(cy) => {
                          cyRef.current = cy;
                          cy.off("tap", "node");
                          cy.on("tap", "node", (evt) => {
                            setSelectedNode(evt.target.data());
                          });
                        }}
                      />
                    </div>

                    {/* Graph Legend */}
                    <div className="p-3 bg-[#0b1329]/95 border-t border-slate-800 flex items-center justify-between flex-wrap gap-2 text-[11px] font-mono text-slate-400">
                      <div className="flex items-center gap-4 flex-wrap">
                        <span className="flex items-center gap-1.5">
                          <span className="w-3 h-3 rounded-full bg-blue-500 border border-cyan-300"></span>
                          Target Suspect
                        </span>
                        <span className="flex items-center gap-1.5">
                          <span className="w-3 h-3 rounded-full bg-slate-700 border border-cyan-400"></span>
                          Intermediary Wallet
                        </span>
                        <span className="flex items-center gap-1.5">
                          <span className="w-3 h-3 rotate-45 bg-red-600 border border-red-400"></span>
                          Exchange Off-ramp
                        </span>
                        <span className="flex items-center gap-1.5">
                          <span className="w-3 h-3 rounded-full border-2 border-amber-400 border-dashed bg-slate-800"></span>
                          Cycled Address
                        </span>
                      </div>
                      <span className="text-slate-500">Click any node to inspect details</span>
                    </div>
                  </div>

                  {/* Node Inspector Panel */}
                  <div className="p-5 rounded-2xl bg-[#0b1329] border border-slate-800 flex flex-col justify-between">
                    <div>
                      <h3 className="text-xs font-mono uppercase tracking-wider text-slate-400 flex items-center gap-2 mb-3">
                        <FolderOpen className="w-3.5 h-3.5 text-cyan-400" />
                        Node Intelligence
                      </h3>

                      {selectedNode ? (
                        <div className="flex flex-col gap-3">
                          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                            <span className="text-[10px] font-mono text-slate-400 uppercase">
                              Wallet Identifier
                            </span>
                            <div className="flex items-center justify-between gap-1 mt-1">
                              <span className="font-mono text-xs text-cyan-300 break-all">
                                {selectedNode.fullAddress}
                              </span>
                              <button
                                onClick={() => copyToClipboard(selectedNode.fullAddress)}
                                className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition"
                                title="Copy address"
                              >
                                {copiedText === selectedNode.fullAddress ? (
                                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                                ) : (
                                  <Copy className="w-3.5 h-3.5" />
                                )}
                              </button>
                            </div>
                          </div>

                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                              <span className="text-[10px] text-slate-400 block font-mono">
                                Classification
                              </span>
                              <span
                                className={`font-semibold ${
                                  selectedNode.isExchange ? "text-red-400" : "text-slate-200"
                                }`}
                              >
                                {selectedNode.exchangeLabel ||
                                  (selectedNode.isExchange ? "Exchange" : "Unhosted Private Wallet")}
                              </span>
                            </div>

                            <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                              <span className="text-[10px] text-slate-400 block font-mono">
                                Network
                              </span>
                              <span className="font-semibold text-slate-200">
                                {selectedNode.chain || selectedChain}
                              </span>
                            </div>
                          </div>

                          {selectedNode.isCycled && (
                            <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs">
                              Flagged in circular fund layering loop.
                            </div>
                          )}

                          <button
                            onClick={() => {
                              setWalletAddress(selectedNode.fullAddress);
                              handleTrace(selectedNode.fullAddress, selectedNode.chain);
                            }}
                            className="mt-2 w-full py-2 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-cyan-400 flex items-center justify-center gap-1.5 border border-slate-700 transition"
                          >
                            <Search className="w-3 h-3" />
                            Deep Trace from Here
                          </button>
                        </div>
                      ) : (
                        <div className="py-12 text-center text-slate-500 text-xs flex flex-col items-center gap-2">
                          <HelpCircle className="w-8 h-8 text-slate-600" />
                          <p>Click on any wallet or exchange node in the graph to view intelligence details.</p>
                        </div>
                      )}
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-500">
                      Case Hash: {traceData.wallet.slice(0, 10)}... | Edges: {traceData.total_edges}
                    </div>
                  </div>
                </div>

                {/* 3. Hop-by-Hop Forensic Ledger Table */}
                <div className="p-5 rounded-2xl bg-[#0b1329] border border-slate-800 shadow-xl overflow-hidden">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-4">
                    <Layers className="w-4 h-4 text-cyan-400" />
                    Traced Transaction Flow Ledger
                  </h3>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs font-mono">
                      <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800">
                        <tr>
                          <th className="py-3 px-4">Hop</th>
                          <th className="py-3 px-4">Sender (From)</th>
                          <th className="py-3 px-4">Receiver (To)</th>
                          <th className="py-3 px-4 text-right">Value ({traceData.currency})</th>
                          <th className="py-3 px-4">Classification</th>
                          <th className="py-3 px-4 text-center">Explorer</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60">
                        {traceData.edges.map((edge, idx) => {
                          const isEth = traceData.chain === "Ethereum";
                          const explorerBase = isEth
                            ? "https://etherscan.io/address/"
                            : "https://tronscan.org/#/address/";

                          return (
                            <tr
                              key={idx}
                              className={`hover:bg-slate-800/40 transition ${
                                edge.is_exchange ? "bg-red-500/5" : ""
                              }`}
                            >
                              <td className="py-3 px-4 font-bold text-cyan-400">{edge.hop}</td>
                              <td className="py-3 px-4 text-slate-300">
                                {edge.from.slice(0, 8)}...{edge.from.slice(-6)}
                              </td>
                              <td className="py-3 px-4 text-slate-300">
                                {edge.to.slice(0, 8)}...{edge.to.slice(-6)}
                              </td>
                              <td className="py-3 px-4 text-right font-bold text-white">
                                {edge.value.toFixed(4)}
                              </td>
                              <td className="py-3 px-4">
                                {edge.is_exchange ? (
                                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-500/20 text-red-400 border border-red-500/30">
                                    {edge.exchange_label || "Exchange Exit"}
                                  </span>
                                ) : (
                                  <span className="text-slate-400">Unhosted Wallet</span>
                                )}
                              </td>
                              <td className="py-3 px-4 text-center">
                                <a
                                  href={`${explorerBase}${edge.to}`}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-cyan-400 hover:text-cyan-300 inline-flex items-center"
                                  title="View on Block Explorer"
                                >
                                  <ExternalLink className="w-3.5 h-3.5" />
                                </a>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {/* TAB 2: Syndicate Clustering */}
        {activeTab === "clusters" && (
          <div className="flex flex-col gap-6">
            <div className="p-6 rounded-2xl bg-[#0b1329] border border-slate-800">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    <Database className="w-5 h-5 text-cyan-400" />
                    Cross-Investigation Syndicate Clustering
                  </h2>
                  <p className="text-xs text-slate-400 mt-1 max-w-2xl">
                    GuardChain automatically indexes all traced investigations into Neo4j Aura. When separate
                    cases overlap at common intermediary wallets or exchange deposit addresses, they are
                    flagged as part of a connected cyber fraud syndicate.
                  </p>
                </div>

                <button
                  onClick={fetchClusters}
                  disabled={loadingClusters}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-cyan-300 flex items-center gap-2 border border-slate-700 transition"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingClusters ? "animate-spin" : ""}`} />
                  Refresh Clusters
                </button>
              </div>

              {loadingClusters ? (
                <div className="py-16 text-center text-slate-400 text-xs flex flex-col items-center gap-3">
                  <RefreshCw className="w-6 h-6 animate-spin text-cyan-400" />
                  <span>Scanning Neo4j graph for overlapping case paths...</span>
                </div>
              ) : clustersData?.syndicate_linkages?.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
                  {clustersData.syndicate_linkages.map((linkage, i) => (
                    <div
                      key={i}
                      className="p-5 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-cyan-500/50 transition flex flex-col justify-between"
                    >
                      <div>
                        <div className="flex items-center justify-between text-xs font-mono text-cyan-400 mb-2">
                          <span className="font-bold">Syndicate Link #{i + 1}</span>
                          <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[10px]">
                            {linkage.overlap_count} Shared Wallets
                          </span>
                        </div>

                        <div className="p-3 rounded-lg bg-[#0b1329] border border-slate-800 space-y-2 text-xs font-mono">
                          <div className="flex items-center justify-between">
                            <span className="text-slate-400">Case A:</span>
                            <span className="text-slate-200">{linkage.case_1}</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-slate-400">Case B:</span>
                            <span className="text-slate-200">{linkage.case_2}</span>
                          </div>
                        </div>

                        <div className="mt-3 text-xs">
                          <span className="text-slate-400 text-[11px] block font-mono">
                            Common Bridging Addresses:
                          </span>
                          <div className="mt-1 space-y-1">
                            {linkage.shared_wallets.map((w, wi) => (
                              <div
                                key={wi}
                                className="p-1.5 rounded bg-slate-800/80 font-mono text-[11px] text-cyan-300 break-all"
                              >
                                {w}
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>

                      <button
                        onClick={() => {
                          setActiveTab("trace");
                          setWalletAddress(linkage.root_1);
                          handleTrace(linkage.root_1, linkage.chain_1);
                        }}
                        className="mt-4 w-full py-2 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 text-xs font-semibold flex items-center justify-center gap-1 transition"
                      >
                        Inspect Primary Case ({linkage.case_1})
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-16 text-center text-slate-500 text-xs flex flex-col items-center gap-2">
                  <Database className="w-8 h-8 text-slate-600" />
                  <p>No multi-case overlaps detected in current database state.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 3: Statutory Investigation Notice Generator */}
        {activeTab === "notice" && (
          <div className="flex flex-col gap-6">
            <div className="p-6 rounded-2xl bg-[#0b1329] border border-slate-800">
              <div className="flex items-start justify-between gap-4 flex-wrap mb-4">
                <div>
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    <FileText className="w-5 h-5 text-cyan-400" />
                    Statutory Preservation & KYC Notice (Draft Template)
                  </h2>
                  <p className="text-xs text-slate-400 mt-1">
                    Modeled after Section 91 Cr.P.C. / Section 94 BNSS (Bharatiya Nagarik Suraksha Sanhita, 2023)
                    protocols.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  {traceData?.draft_notice && (
                    <button
                      onClick={() => copyToClipboard(traceData.draft_notice.notice_text)}
                      className="px-3 py-1.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs flex items-center gap-1.5 transition"
                    >
                      {copiedText ? (
                        <>
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Copied!
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          Copy Draft Notice
                        </>
                      )}
                    </button>
                  )}
                </div>
              </div>

              {/* Prototype Honesty Notice Disclaimer */}
              <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-start gap-2.5 mb-4">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                <span className="leading-relaxed">
                  <strong>LEGAL NOTICE DISCLAIMER:</strong> This is an auto-generated draft template designed for
                  Investigating Officer (I.O.) review. It is <strong>NOT</strong> connected to live government
                  gateways (NCRP, SAHYOG, CFCFRMS) and requires formal officer authorization before dispatch to
                  exchanges.
                </span>
              </div>

              {traceData?.draft_notice ? (
                <div className="p-5 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs text-slate-300 whitespace-pre-wrap leading-relaxed overflow-x-auto">
                  {traceData.draft_notice.notice_text}
                </div>
              ) : (
                <div className="py-16 text-center text-slate-500 text-xs flex flex-col items-center gap-2">
                  <FileText className="w-8 h-8 text-slate-600" />
                  <p>Run a wallet trace first to generate an auto-populated statutory requisition notice.</p>
                  <button
                    onClick={() => setActiveTab("trace")}
                    className="mt-2 px-4 py-2 rounded-xl bg-cyan-500 text-slate-950 font-bold text-xs"
                  >
                    Go to Trace Canvas
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-[#0b1329] py-4 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-slate-500">
          <div>
            GuardChain Blockchain Forensic Engine — Smart India Hackathon 2026 (PS 26183)
          </div>
          <div className="flex items-center gap-4">
            <span>Zero-Paid API Architecture</span>
            <span>•</span>
            <span>Neo4j Aura Free Tier</span>
            <span>•</span>
            <span>Etherscan & TronGrid</span>
          </div>
        </div>
      </footer>
    </div>
  );
}