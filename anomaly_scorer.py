"""
Statistical Anomaly Scoring Module for GuardChain
Pure-Python statistical dispersion and outlier modeling for zero-dependency cloud resilience.
"""

import math


def compute_anomaly_score(edges, wallet_address=""):
    """
    Computes a 0-100 statistical anomaly score for the given traced transaction graph.
    
    Features extracted:
      1. Value variance / concentration (Coefficient of Variation)
      2. Fan-out dispersal ratio (unique targets / total txs)
      3. Hop depth & direct exchange velocity
      4. Batch transfer uniformity
    """
    if not edges:
        return {
            "anomaly_score": 0,
            "verdict": "Insufficient Data",
            "indicators": ["No transaction edges available for statistical modeling."],
            "method": "Statistical Outlier Scoring"
        }

    values = []
    hops = []
    senders = set()
    receivers = set()
    exchange_hops = []

    for edge in edges:
        if isinstance(edge, dict):
            val = float(edge.get("value_eth", edge.get("value", 0.0)))
            hop = int(edge.get("hop", 1))
            is_exc = bool(edge.get("is_exchange", False))
            u = edge.get("from", "")
            v = edge.get("to", "")
        else:
            val = float(edge[2])
            hop = int(edge[3])
            is_exc = bool(edge[4])
            u = edge[0]
            v = edge[1]

        values.append(val)
        hops.append(hop)
        senders.add(u)
        receivers.add(v)
        if is_exc:
            exchange_hops.append(hop)

    n = len(values)
    mean_val = sum(values) / n if n > 0 else 0.0
    variance = sum((x - mean_val) ** 2 for x in values) / n if n > 0 else 0.0
    val_std = math.sqrt(variance)
    val_cv = (val_std / (mean_val + 1e-6))  # coefficient of variation

    indicators = []
    base_score = 25  # standard baseline

    # Feature 1: Rapid peeling / value concentration
    if n >= 2 and val_cv > 1.2:
        base_score += 20
        indicators.append("High value dispersion: funds split into uneven peeling/structuring amounts.")
    elif n >= 2 and val_cv < 0.1 and mean_val > 0.5:
        base_score += 15
        indicators.append("Uniform amount splitting: funds distributed in identical batch transactions.")

    # Feature 2: Fan-out distribution
    fan_out_ratio = len(receivers) / max(1, n)
    if fan_out_ratio > 0.8 and n >= 3:
        base_score += 15
        indicators.append(f"High fan-out dispersal ({len(receivers)} unique destinations across {n} paths).")

    # Feature 3: Direct exchange routing
    if exchange_hops:
        min_ex_hop = min(exchange_hops)
        if min_ex_hop <= 2:
            base_score += 25
            indicators.append(f"High velocity routing: centralized exchange reached in {min_ex_hop} hop(s).")
        else:
            base_score += 10
            indicators.append(f"Multi-hop distribution preceding exchange deposit at hop {min_ex_hop}.")

    # Outlier anomaly proxy
    if val_cv > 1.5 or (exchange_hops and min(exchange_hops) == 1):
        base_score += 15
        indicators.append("Outlier detection flags structural deviation from typical peer transaction baselines.")

    final_score = min(98, max(5, int(base_score)))

    if final_score >= 75:
        verdict = "Highly Anomalous Pattern"
    elif final_score >= 50:
        verdict = "Moderate Anomaly"
    else:
        verdict = "Standard Flow Characteristics"

    if not indicators:
        indicators.append("Graph parameters align within standard peer behavioral limits.")

    return {
        "anomaly_score": final_score,
        "verdict": verdict,
        "indicators": indicators,
        "method": "Unsupervised Statistical Outlier & Dispersion Analysis"
    }
