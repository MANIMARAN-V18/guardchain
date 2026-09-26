"""
Bitcoin (BTC) Tracing Module for GuardChain
Queries public Blockchain.info & Blockchair free API endpoints to trace Bitcoin transaction flows,
UTXO peeling chains, and centralized exchange deposit wallets.
"""

import time
import requests

MAX_HOPS = 4
TOP_N_TX_PER_WALLET = 2

# Known Bitcoin exchange deposit clusters and cold storage
KNOWN_BTC_EXCHANGES = {
    "1P5ZEDWTKTFGxQjZphgWPQUpe554WKDfHQ": "Binance Cold Storage",
    "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo": "Binance Hot Wallet",
    "35hK24tcChxbpnTbEgcGngdE2MtMeMVGJP": "Coinbase Prime",
    "1FzWLWTHRmsYrBtCiUCq7SfPT2KEC2SuZu": "Bitfinex",
    "bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h": "Binance Bech32",
    "1AnwDVbwsLBNo1G4bNxkP7w2L4J7T4P5fB": "Kraken",
    "3D2oetdNuZUqQHPJmcMDDHYoqkyNVsFDe9": "OKX Exchange",
}


def is_known_btc_exchange(address):
    if not address:
        return None
    return KNOWN_BTC_EXCHANGES.get(address)


def check_btc_exchange(address):
    label = is_known_btc_exchange(address)
    if label:
        return {"is_exchange": True, "method": "known_label", "label": label}
    return {"is_exchange": False, "method": "heuristic", "label": None}


def get_btc_outgoing(address):
    """
    Fetches outgoing transactions for a Bitcoin address using Blockchain.info public free API.
    """
    url = f"https://blockchain.info/rawaddr/{address}?limit=15"
    try:
        r = requests.get(url, headers={"User-Agent": "GuardChain-Forensics/1.0"}, timeout=8)
        if r.status_code != 200:
            return []
        data = r.json()
        txs = data.get("txs", [])
        
        outgoing = []
        for tx in txs:
            inputs = [inp.get("prev_out", {}).get("addr") for inp in tx.get("inputs", []) if inp.get("prev_out")]
            if address in inputs:
                # Find downstream outputs not returning to self
                for out in tx.get("out", []):
                    dest_addr = out.get("addr")
                    val_sat = out.get("value", 0)
                    val_btc = val_sat / 1e8
                    
                    if dest_addr and dest_addr != address and val_btc > 0.0001:
                        outgoing.append({
                            "from": address,
                            "to": dest_addr,
                            "value": val_btc,
                            "tx_hash": tx.get("hash", "")
                        })
                        
        outgoing.sort(key=lambda x: x["value"], reverse=True)
        return outgoing
    except Exception as e:
        print(f"[btc_trace] Error fetching Bitcoin transactions: {e}")
        return []


def trace_btc_wallet(start_address, max_hops=MAX_HOPS):
    """
    Traces Bitcoin UTXO hops recursively.
    Returns: (from_address, to_address, value_btc, hop, is_exchange, exchange_label)
    """
    edges = []
    visited = set()
    current_layer = [start_address]

    for hop in range(1, max_hops + 1):
        next_layer = []
        for address in current_layer:
            if address in visited:
                continue
            visited.add(address)

            outgoing = get_btc_outgoing(address)
            top_tx = outgoing[:TOP_N_TX_PER_WALLET]

            for tx in top_tx:
                to_addr = tx["to"]
                val = tx["value"]
                ex_info = check_btc_exchange(to_addr)
                is_ex = ex_info["is_exchange"]
                label = ex_info.get("label", "Exchange" if is_ex else None)

                edges.append((address, to_addr, val, hop, is_ex, label))

                if not is_ex:
                    next_layer.append(to_addr)

            time.sleep(0.3)

        current_layer = next_layer
        if not current_layer:
            break

    return edges
