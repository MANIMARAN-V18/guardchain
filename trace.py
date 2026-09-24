import os
import time
import requests
from dotenv import load_dotenv
from exchange_detect import check_exchange

load_dotenv()
API_KEY = os.getenv("ETHERSCAN_API_KEY")

BASE_URL = "https://api.etherscan.io/v2/api"
MAX_HOPS = 4                # how deep we trace
TOP_N_TX_PER_WALLET = 2     # only follow the biggest N outgoing transactions


def get_transactions(address):
    """Fetch outgoing transactions for one wallet address from Etherscan."""
    params = {
        "chainid": 1,
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": 20,        # fetch a batch, we'll pick the top N ourselves
        "sort": "desc",
        "apikey": API_KEY
    }
    response = requests.get(BASE_URL, params=params)
    data = response.json()

    if data.get("status") != "1":
        return []

    return data.get("result", [])


def get_top_outgoing(address, n):
    """From all transactions, keep only ones SENT by this address,
    and return the top n by value (biggest amount moved)."""
    all_tx = get_transactions(address)
    outgoing = [tx for tx in all_tx if tx["from"].lower() == address.lower()]
    outgoing.sort(key=lambda tx: int(tx["value"]), reverse=True)
    return outgoing[:n]


def trace_wallet(start_address, max_hops=MAX_HOPS):
    """
    Follow money from start_address, hop by hop.
    Returns a list of edges: (from_address, to_address, value_eth, hop_number)
    """
    edges = []
    visited = set()
    current_layer = [start_address]

    for hop in range(1, max_hops + 1):
        next_layer = []
        print(f"\n--- Hop {hop} ---")

        for address in current_layer:
            if address in visited:
                continue
            visited.add(address)

            top_tx = get_top_outgoing(address, TOP_N_TX_PER_WALLET)

            for tx in top_tx:
                to_address = tx["to"]
                value_eth = int(tx["value"]) / 1e18   # convert Wei to ETH

                if not to_address:   # some contract creation tx have empty "to"
                    continue

                exchange_info = check_exchange(to_address)

                if exchange_info["is_exchange"]:
                    label = exchange_info.get("label", "Unknown Exchange")
                    print(f"{address[:8]}... -> {to_address[:8]}...  ({value_eth:.4f} ETH)  [EXCHANGE: {label}]")
                else:
                    print(f"{address[:8]}... -> {to_address[:8]}...  ({value_eth:.4f} ETH)")

                edges.append((address, to_address, value_eth, hop, exchange_info["is_exchange"]))

                # Only keep tracing further if this wallet is NOT an exchange
                if not exchange_info["is_exchange"]:
                    next_layer.append(to_address)

            time.sleep(0.25)   # be polite to the free-tier rate limit (5 calls/sec)

        current_layer = next_layer

        if not current_layer:
            print("No further transactions found. Stopping early.")
            break

    return edges


if __name__ == "__main__":
    from graph_store import GraphStore

    start_wallet = "0xDFd5293D8e347dFe59E90eFd55b2956a1343963d"
    result = trace_wallet(start_wallet)

    print(f"\n\nTotal edges traced: {len(result)}")

    store = GraphStore()
    store.save_all_edges(result)
    store.close()