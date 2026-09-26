"""
GuardChain — Blockchain Fraud Tracing Platform
FastAPI Application Backend (SIH2026 Problem Statement 26183)

Complete Feature Set:
- Multi-chain Recursive Tracing (Ethereum + Tron USDT + Bitcoin Blockchair)
- Freeze Window Urgency Scoring (0-100)
- Automated PDF Forensic Dossier Generation (fpdf2)
- Cross-Investigation Case Clustering (Neo4j Graph Database)
- Circular Laundering Cycle Detection (DFS)
- Statistical Anomaly Scoring (scikit-learn Isolation Forest)
- Machine Learning Wallet Clustering (K-Means)
- Tamper-Evident Audit Logging & Officer RBAC
- Pandas Forensic Ledger CSV Export
- Auto-Drafted Statutory Preservation & KYC Notice (Sec 91 CrPC / Sec 94 BNSS)
"""

import io
import re
import csv
from fastapi import FastAPI, Query, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from trace import trace_wallet
from tron_trace import trace_tron_wallet
from btc_trace import trace_btc_wallet
from freeze_scoring import calculate_freeze_score
from report_generator import generate_pdf_report
from cycle_detector import detect_circular_patterns
from anomaly_scorer import compute_anomaly_score
from ml_clustering import cluster_traced_wallets
from audit_logger import log_investigation_search, get_audit_trail
from notice_generator import generate_draft_notice
from graph_store import GraphStore

app = FastAPI(
    title="GuardChain API",
    description="Decentralized Blockchain Fraud Tracing & Freeze Window Intelligence Engine",
    version="2.0.0"
)

# --- Security Headers Middleware ---
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


def validate_wallet_address(address: str, chain: str) -> str:
    """
    Strict cryptographic address format validation to prevent injection or malicious inputs.
    """
    clean_addr = address.strip()
    chain_clean = chain.strip().lower()

    if chain_clean == "ethereum":
        if not re.match(r"^0x[a-fA-F0-9]{40}$", clean_addr):
            raise HTTPException(status_code=400, detail="Invalid Ethereum address format (must be 42-char hex with 0x prefix).")
    elif chain_clean == "tron":
        if not re.match(r"^T[1-9A-HJ-NP-za-km-z]{33}$", clean_addr):
            raise HTTPException(status_code=400, detail="Invalid Tron address format (must be 34-char base58 starting with T).")
    elif chain_clean in ["bitcoin", "btc"]:
        if not re.match(r"^(bc1[a-z0-9]{25,90}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})$", clean_addr):
            raise HTTPException(status_code=400, detail="Invalid Bitcoin address format (must be valid Bech32 or Base58 address).")
    else:
        if not re.match(r"^[a-zA-Z0-9]{8,100}$", clean_addr):
            raise HTTPException(status_code=400, detail="Invalid wallet address characters.")

    return clean_addr


@app.get("/")
def root():
    return {
        "platform": "GuardChain Forensic Engine",
        "version": "2.0.0",
        "supported_chains": ["Ethereum", "Tron (TRC20 USDT)", "Bitcoin (Blockchair/UTXO)"],
        "status": "operational",
        "compliance": "100% Free-Tier, GDPR & DPDP Compliant"
    }


def _run_trace_pipeline(wallet_address: str, chain: str = "Ethereum", hops: int = 4, usdt_only: bool = True):
    """
    Unified multi-chain tracing & intelligence pipeline.
    """
    chain_clean = chain.strip().capitalize()
    
    if chain_clean == "Tron":
        raw_edges = trace_tron_wallet(wallet_address, max_hops=hops, usdt_only=usdt_only)
        curr_unit = "USDT"
    elif chain_clean in ["Bitcoin", "Btc"]:
        chain_clean = "Bitcoin"
        raw_edges = trace_btc_wallet(wallet_address, max_hops=hops)
        curr_unit = "BTC"
    else:
        chain_clean = "Ethereum"
        raw_edges = trace_wallet(wallet_address, max_hops=hops)
        curr_unit = "ETH"

    # Convert raw edges into clean structured dictionaries
    structured_edges = []
    for edge in raw_edges:
        token_currency = curr_unit
        if len(edge) >= 7:
            f_addr, t_addr, val, hop, is_ex, label, token_currency = edge[0], edge[1], edge[2], edge[3], edge[4], edge[5], edge[6]
        elif len(edge) == 6:
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
            "currency": token_currency,
            "hop": int(hop),
            "is_exchange": bool(is_ex),
            "exchange_label": label
        })

    # Compute Forensic Intelligence metrics
    freeze_info = calculate_freeze_score(structured_edges)
    cycle_info = detect_circular_patterns(structured_edges)
    anomaly_info = compute_anomaly_score(structured_edges, wallet_address)
    ml_clusters = cluster_traced_wallets(structured_edges)
    draft_notice = generate_draft_notice(wallet_address, structured_edges, freeze_info, chain=chain_clean)

    # Log query to audit trail for compliance
    log_investigation_search(wallet_address, chain=chain_clean)

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
        "ml_clustering": ml_clusters,
        "draft_notice": draft_notice
    }


@app.get("/trace/{wallet_address}")
def trace(
    wallet_address: str,
    request: Request,
    chain: str = Query("Ethereum", description="Blockchain network: Ethereum, Tron, or Bitcoin"),
    hops: int = Query(4, ge=1, le=6, description="Trace depth"),
    usdt_only: bool = Query(True, description="Filter Tron transfers to USDT-only (ignoring random meme/airdrop tokens)")
):
    valid_addr = validate_wallet_address(wallet_address, chain)
    client_ip = request.client.host if request.client else "127.0.0.1"
    return _run_trace_pipeline(valid_addr, chain=chain, hops=hops, usdt_only=usdt_only)


@app.get("/trace/{wallet_address}/report")
def download_pdf_report(
    wallet_address: str,
    chain: str = Query("Ethereum", description="Blockchain network: Ethereum, Tron, or Bitcoin"),
    hops: int = Query(4, ge=1, le=6),
    usdt_only: bool = Query(True, description="Filter Tron transfers to USDT-only")
):
    valid_addr = validate_wallet_address(wallet_address, chain)
    data = _run_trace_pipeline(valid_addr, chain=chain, hops=hops, usdt_only=usdt_only)
    pdf_bytes = generate_pdf_report(
        wallet_address=data["wallet"],
        edges=data["edges"],
        freeze_info=data["freeze_window"],
        chain=data["chain"],
        cycle_info=data["cycle_detection"],
        anomaly_info=data["statistical_anomaly"]
    )

    clean_addr = valid_addr[:10]
    filename = f"guardchain_trace_{data['chain'].lower()}_{clean_addr}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )


@app.get("/trace/{wallet_address}/export")
def export_ledger_csv(
    wallet_address: str,
    chain: str = Query("Ethereum"),
    hops: int = Query(4)
):
    """
    Exports the full traced transaction ledger to CSV.
    """
    valid_addr = validate_wallet_address(wallet_address, chain)
    data = _run_trace_pipeline(valid_addr, chain=chain, hops=hops)
    edges = data.get("edges", [])
    
    output = io.StringIO()
    if edges:
        fieldnames = list(edges[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(edges)
    else:
        output.write("from,to,value_eth,value,currency,hop,is_exchange,exchange_label\n")
    
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="guardchain_ledger_{valid_addr[:8]}.csv"'}
    )


@app.get("/trace/{wallet_address}/notice")
def get_notice(
    wallet_address: str,
    chain: str = Query("Ethereum")
):
    valid_addr = validate_wallet_address(wallet_address, chain)
    data = _run_trace_pipeline(valid_addr, chain=chain, hops=4)
    return data["draft_notice"]


@app.get("/cases/clusters")
def get_case_clusters():
    store = GraphStore()
    clusters = store.get_clusters()
    store.close()
    return clusters


@app.get("/audit/trail")
def get_audit_logs():
    """
    Returns cryptographic officer audit logs for legal compliance.
    """
    return {
        "status": "verified",
        "audit_logs": get_audit_trail()
    }