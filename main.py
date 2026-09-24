from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from trace import trace_wallet
from graph_store import GraphStore

app = FastAPI(title="GuardChain API")

# Allow the React frontend (running on a different port) to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # for development only; we'll restrict this later
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "GuardChain API is running"}


@app.get("/trace/{wallet_address}")
def trace(wallet_address: str):
    """
    Traces a wallet address hop by hop, saves the result to Neo4j,
    and returns the traced edges as JSON.
    """
    edges = trace_wallet(wallet_address)

    store = GraphStore()
    store.save_all_edges(edges)
    store.close()

    # Convert edges into a clean JSON-friendly format
    result = [
        {
            "from": from_addr,
            "to": to_addr,
            "value_eth": value_eth,
            "hop": hop,
            "is_exchange": is_exchange
        }
        for from_addr, to_addr, value_eth, hop, is_exchange in edges
    ]

    return {
        "wallet": wallet_address,
        "total_edges": len(result),
        "edges": result
    }