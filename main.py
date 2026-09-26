"""
GuardChain — Blockchain Fraud Tracing Platform
FastAPI Application Backend (SIH2026 Problem Statement 26183)

Features:
- Multi-chain Recursive Tracing (Ethereum + Tron TRC20 USDT)
- Freeze Window Urgency Scoring (0-100)
- Automated PDF Forensic Dossier Generation (fpdf2)
- Cross-Investigation Case Clustering (Neo4j Graph Database)
- Circular Laundering Cycle Detection
- Statistical Anomaly Scoring (scikit-learn Isolation Forest)
- Auto-Drafted Statutory Preservation & KYC Notice (Sec 91 CrPC / Sec 94 BNSS)
"""

from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

from trace import trace_wallet
from tron_trace import trace_tron_wallet
from freeze_scoring import calculate_freeze_score
from report_generator import generate_pdf_report
from cycle_detector import detect_circular_patterns
from anomaly_scorer import compute_anomaly_score
from notice_generator import generate_draft_notice
from graph_store import GraphStore

app = FastAPI(
    title="GuardChain API",
    description="Decentralized Blockchain Fraud Tracing & Freeze Window Intelligence Engine",
    version="2.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "platform": "GuardChain Forensic Engine",
        "version": "2.0.0",
        "supported_chains": ["Ethereum", "Tron (TRC20 USDT)"],
        "status": "operational",
        "compliance": "100% Free-Tier & Open Source"
    }


def _run_trace_pipeline(wallet_address: str, chain: str = "Ethereum", hops: int = 4):
    """
    Internal shared pipeline for running recursive trace and all forensic analytics.
    Reused by both /trace and /trace/{wallet_address}/report to ensure consistency.
    """
    chain_clean = chain.strip().capitalize()
    if chain_clean == "Tron":
        raw_edges = trace_tron_wallet(wallet_address, max_hops=hops)
        curr_unit = "USDT"
    else:
        chain_clean = "Ethereum"
        raw_edges = trace_wallet(wallet_address, max_hops=hops)
        curr_unit = "ETH"

    # Convert raw edges into clean structured dictionaries
    structured_edges = []
    for edge in raw_edges:
        if len(edge) >= 6:
            f_addr, t_addr, val, hop, is_ex, label = edge[0], edge[1], edge[2], edge[3], edge[4], edge[5]
        elif len(edge) == 5:
            f_addr, t_addr, val, hop, is_ex = edge[0], edge[1], edge[2], edge[3], edge[4]
            label = "Exchange" if is_ex else None
        else:
            f_addr, t_addr, val, hop = edge[0], edge[1], edge[2], edge[3]
            is_ex, label = False, None

        structured_edges.append({
            "from": f_addr,
            "to": t_addr,
            "value_eth": float(val),
            "value": float(val),
            "currency": curr_unit,
            "hop": int(hop),
            "is_exchange": bool(is_ex),
            "exchange_label": label
        })

    # Compute Forensic Intelligence metrics
    freeze_info = calculate_freeze_score(structured_edges)
    cycle_info = detect_circular_patterns(structured_edges)
    anomaly_info = compute_anomaly_score(structured_edges, wallet_address)
    draft_notice = generate_draft_notice(wallet_address, structured_edges, freeze_info, chain=chain_clean)

    # Persist to Neo4j Graph Database & local cache
    try:
        store = GraphStore()
        store.save_case_and_edges(
            root_wallet=wallet_address,
            chain=chain_clean,
            freeze_score=freeze_info.get("score", 0),
            edges=raw_edges
        )
        store.close()
    except Exception as e:
        print(f"[main] GraphStore persistence notice: {e}")

    return {
        "wallet": wallet_address,
        "chain": chain_clean,
        "currency": curr_unit,
        "total_edges": len(structured_edges),
        "edges": structured_edges,
        "freeze_window": freeze_info,
        "cycle_detection": cycle_info,
        "statistical_anomaly": anomaly_info,
        "draft_notice": draft_notice
    }


@app.get("/trace/{wallet_address}")
def trace(
    wallet_address: str,
    chain: str = Query("Ethereum", description="Blockchain network: Ethereum or Tron"),
    hops: int = Query(4, ge=1, le=6, description="Trace depth")
):
    """
    Traces a wallet address recursively, detects exchange exit nodes,
    computes Freeze Window Urgency, statistical anomaly metrics, and circular cycles.
    """
    if not wallet_address or len(wallet_address.strip()) < 10:
        raise HTTPException(status_code=400, detail="Invalid wallet address provided.")

    return _run_trace_pipeline(wallet_address.strip(), chain=chain, hops=hops)


@app.get("/trace/{wallet_address}/report")
def download_pdf_report(
    wallet_address: str,
    chain: str = Query("Ethereum", description="Blockchain network: Ethereum or Tron"),
    hops: int = Query(4, ge=1, le=6)
):
    """
    Generates a publication-grade PDF Forensic Dossier for law enforcement and returns it as a downloadable file.
    """
    if not wallet_address or len(wallet_address.strip()) < 10:
        raise HTTPException(status_code=400, detail="Invalid wallet address.")

    data = _run_trace_pipeline(wallet_address.strip(), chain=chain, hops=hops)
    pdf_bytes = generate_pdf_report(
        wallet_address=data["wallet"],
        edges=data["edges"],
        freeze_info=data["freeze_window"],
        chain=data["chain"],
        cycle_info=data["cycle_detection"],
        anomaly_info=data["statistical_anomaly"]
    )

    clean_addr = wallet_address.strip()[:10]
    filename = f"guardchain_trace_{data['chain'].lower()}_{clean_addr}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )


@app.get("/trace/{wallet_address}/notice")
def get_notice(
    wallet_address: str,
    chain: str = Query("Ethereum", description="Blockchain network: Ethereum or Tron")
):
    """
    Returns the auto-drafted statutory preservation & KYC notice template for officer review.
    """
    data = _run_trace_pipeline(wallet_address.strip(), chain=chain, hops=4)
    return data["draft_notice"]


@app.get("/cases/clusters")
def get_case_clusters():
    """
    Analyzes historical wallet traces across investigations and detects overlapping
    downstream wallets or common exchange deposit nodes (Syndicate Clustering).
    """
    store = GraphStore()
    clusters = store.get_clusters()
    store.close()
    return clusters