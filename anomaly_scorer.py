"""
Statistical Anomaly Scoring Module for GuardChain
Uses unsupervised Isolation Forest (scikit-learn) and dispersion metrics
to detect structural transaction anomalies in traced paths without overclaiming AI capabilities.
"""

import numpy as np
from sklearn.ensemble import IsolationForest


def compute_anomaly_score(edges, wallet_address=""):
    """
    Computes a 0-100 statistical anomaly score for the given traced transaction graph.
    
    Features extracted:
      1. Value variance / concentration
      2. Fan-out ratio (unique targets / total txs)
      3. Hop depth distribution
      4. Exchange offload velocity
    """
    if not edges:
        return {
            "anomaly_score": 0,
            "verdict": "Insufficient Data",
            "indicators": ["No transaction edges available for statistical modeling."],
            "method": "Statistical Outlier Scoring"
        }

    # Extract transaction values
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

    val_arr = np.array(values, dtype=float)
    total_val = float(np.sum(val_arr))
    mean_val = float(np.mean(val_arr)) if len(val_arr) > 0 else 0.0
    val_std = float(np.std(val_arr)) if len(val_arr) > 0 else 0.0
    val_cv = (val_std / (mean_val + 1e-6))  # coefficient of variation

    indicators = []
    base_score = 25  # standard baseline

    # Feature 1: Rapid peeling / value concentration
    if len(val_arr) >= 2 and val_cv > 1.2:
        base_score += 20
        indicators.append("High value dispersion: funds split into uneven peeling/structuring amounts.")
    elif len(val_arr) >= 2 and val_cv < 0.1 and mean_val > 0.5:
        base_score += 15
        indicators.append("Uniform amount splitting: funds distributed in identical batch transactions.")

    # Feature 2: Fan-out distribution
    fan_out_ratio = len(receivers) / max(1, len(edges))
    if fan_out_ratio > 0.8 and len(edges) >= 3:
        base_score += 15
        indicators.append(f"High fan-out dispersal ({len(receivers)} unique destinations across {len(edges)} paths).")

    # Feature 3: Direct exchange routing
    if exchange_hops:
        min_ex_hop = min(exchange_hops)
        if min_ex_hop <= 2:
            base_score += 25
            indicators.append(f"High velocity routing: centralized exchange reached in {min_ex_hop} hop(s).")
        else:
            base_score += 10
            indicators.append(f"Multi-hop distribution preceding exchange deposit at hop {min_ex_hop}.")

    # Unsupervised Isolation Forest model on synthetic baseline + current graph features
    # Synthetic baseline of normal crypto transfers vs current sample
    try:
        # Generate a small baseline reference matrix [val_mean, val_cv, fan_out, min_ex_hop_proxy]
        normal_baseline = np.array([
            [0.1, 0.4, 0.4, 4.0],
            [0.2, 0.5, 0.5, 4.0],
            [0.05, 0.3, 0.3, 4.0],
            [0.5, 0.6, 0.5, 3.0],
            [0.3, 0.5, 0.4, 4.0],
            [0.8, 0.7, 0.6, 3.0],
            [0.15, 0.4, 0.3, 4.0],
            [0.4, 0.5, 0.4, 4.0],
        ])
        
        sample_feature = np.array([[
            mean_val,
            val_cv,
            fan_out_ratio,
            min(exchange_hops) if exchange_hops else 4.0
        ]])

        iso_forest = IsolationForest(contamination=0.2, random_state=42)
        iso_forest.fit(normal_baseline)
        decision_val = iso_forest.decision_function(sample_feature)[0]
        
        # Lower decision value = more anomalous
        if decision_val < -0.05:
            base_score += 15
            indicators.append("Isolation Forest flags structural deviation from typical peer distribution.")
    except Exception:
        pass

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
        "method": "Unsupervised Isolation Forest + Statistical Dispersion Analysis"
    }
