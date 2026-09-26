"""
Freeze Window Scoring Module for GuardChain
Calculates law enforcement urgency (0-100) and actionable time window
based on proximity of funds to centralized crypto exchanges (off-ramps).
"""

def calculate_freeze_score(edges):
    """
    Analyzes traced transaction edges and computes the Freeze Window Urgency Score.
    
    edges can be:
      - list of tuples: (from_addr, to_addr, value_eth, hop, is_exchange) or
      - list of dicts with keys: 'from', 'to', 'value_eth' (or 'value'), 'hop', 'is_exchange'
    
    Returns:
      dict with keys:
        - score: int (0-100)
        - level: str ("Critical" | "High" | "Moderate" | "Low/Unknown")
        - reason: str (Human-readable intelligence summary)
        - min_hop_to_exchange: int or None
        - recommended_action_window: str
        - target_exchanges: list of str
    """
    if not edges:
        return {
            "score": 0,
            "level": "Low/Unknown",
            "reason": "No outgoing transactions identified in trace path.",
            "min_hop_to_exchange": None,
            "recommended_action_window": "N/A",
            "target_exchanges": []
        }

    # Normalize edges to tuple format if passed as dicts
    normalized_edges = []
    for edge in edges:
        if isinstance(edge, dict):
            normalized_edges.append((
                edge.get("from"),
                edge.get("to"),
                edge.get("value_eth", edge.get("value", 0.0)),
                edge.get("hop", 1),
                edge.get("is_exchange", False),
                edge.get("exchange_label", None)
            ))
        elif isinstance(edge, (list, tuple)):
            if len(edge) >= 5:
                label = edge[5] if len(edge) > 5 else None
                normalized_edges.append((edge[0], edge[1], edge[2], edge[3], edge[4], label))
            else:
                normalized_edges.append((edge[0], edge[1], edge[2], edge[3], False, None))

    # Find all exchange hits
    exchange_hits = [e for e in normalized_edges if e[4]]

    if not exchange_hits:
        return {
            "score": 15,
            "level": "Low/Unknown",
            "reason": "No centralized exchange deposit detected within trace depth. Funds are currently resting in unhosted private wallets or DeFi contracts.",
            "min_hop_to_exchange": None,
            "recommended_action_window": "> 72 Hours (Standard Investigation)",
            "target_exchanges": []
        }

    # Find earliest hop to an exchange
    min_hop = min(e[3] for e in exchange_hits)
    earliest_hits = [e for e in exchange_hits if e[3] == min_hop]
    
    # Collect unique exchange addresses / labels
    exchanges_found = list({e[1] for e in earliest_hits})
    total_val_to_exchange = sum(e[2] for e in exchange_hits)

    if min_hop == 1:
        score = 95
        level = "Critical"
        action_window = "0 - 4 Hours (Immediate Freeze Order Required)"
        reason = (
            f"Direct transfer to exchange detected at Hop 1 ({len(earliest_hits)} tx, ~{total_val_to_exchange:.4f} crypto units). "
            f"High probability of active fiat liquidation or off-ramping. Immediate statutory freeze notice required."
        )
    elif min_hop == 2:
        score = 75
        level = "High"
        action_window = "4 - 24 Hours (Urgent Notice to Exchange)"
        reason = (
            f"Exchange deposit identified at Hop 2 via single intermediary wallet. "
            f"Launderer is rapidly staging funds for withdrawal. Priority request to exchange compliance required."
        )
    elif min_hop == 3:
        score = 45
        level = "Moderate"
        action_window = "24 - 48 Hours (Expedited Notice)"
        reason = (
            f"Funds reached centralized exchange at Hop 3 through multi-layer forwarding. "
            f"Action window open before secondary mixing or cross-chain bridge hops occur."
        )
    else:  # hop >= 4
        score = 30
        level = "Moderate"
        action_window = "48 - 72 Hours (Standard Notice)"
        reason = (
            f"Extended chain detected reaching exchange at Hop {min_hop}. "
            f"Trace indicates complex peeling chain or multi-hop distribution before exchange deposit."
        )

    return {
        "score": score,
        "level": level,
        "reason": reason,
        "min_hop_to_exchange": min_hop,
        "recommended_action_window": action_window,
        "target_exchanges": exchanges_found
    }
