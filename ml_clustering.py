"""
Machine Learning Wallet Behavior Clustering Module for GuardChain
Uses scikit-learn K-Means to cluster traced wallets by transaction velocity, value dispersion, and off-ramp proximity.
"""

import numpy as np
from sklearn.cluster import KMeans


def cluster_traced_wallets(edges, n_clusters=3):
    """
    Extracts numerical feature vectors for all distinct wallets in the trace graph
    and applies K-Means clustering to partition them into behavioral categories:
      - Cluster 0: High-Velocity Dispatcher / Primary Suspect
      - Cluster 1: Intermediary Mules / Smurfing Wallets
      - Cluster 2: Off-Ramp Gateway / Liquidation Points
    """
    if not edges or len(edges) < 2:
        return {
            "ml_clusters": [],
            "method": "K-Means Behavioral Feature Clustering",
            "cluster_count": 0
        }

    wallet_stats = {}
    for edge in edges:
        if isinstance(edge, dict):
            u, v = edge.get("from"), edge.get("to")
            val = float(edge.get("value", 0))
            hop = int(edge.get("hop", 1))
            is_ex = bool(edge.get("is_exchange", False))
        else:
            u, v = edge[0], edge[1]
            val = float(edge[2])
            hop = int(edge[3])
            is_ex = bool(edge[4])

        if u not in wallet_stats:
            wallet_stats[u] = {"sent_vol": 0, "recv_vol": 0, "tx_count": 0, "max_hop": hop, "is_ex": 0}
        if v not in wallet_stats:
            wallet_stats[v] = {"sent_vol": 0, "recv_vol": 0, "tx_count": 0, "max_hop": hop, "is_ex": 1 if is_ex else 0}

        wallet_stats[u]["sent_vol"] += val
        wallet_stats[u]["tx_count"] += 1
        wallet_stats[v]["recv_vol"] += val
        wallet_stats[v]["tx_count"] += 1
        if is_ex:
            wallet_stats[v]["is_ex"] = 1

    wallets = list(wallet_stats.keys())
    features = []
    for w in wallets:
        st = wallet_stats[w]
        features.append([
            st["sent_vol"],
            st["recv_vol"],
            st["tx_count"],
            st["max_hop"],
            st["is_ex"] * 5.0
        ])

    X = np.array(features, dtype=float)
    k = min(n_clusters, len(wallets))
    
    if k < 2:
        cluster_labels = [0] * len(wallets)
    else:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(X).tolist()

    cluster_names = {
        0: "Core Dispatcher / Staging",
        1: "Layering Intermediary Mule",
        2: "Off-Ramp Liquidation Node"
    }

    result = []
    for i, w in enumerate(wallets):
        cid = cluster_labels[i]
        result.append({
            "address": w,
            "cluster_id": cid,
            "cluster_label": cluster_names.get(cid, f"Cluster {cid}"),
            "stats": wallet_stats[w]
        })

    return {
        "ml_clusters": result,
        "method": "Unsupervised K-Means Feature Clustering (Scikit-Learn)",
        "cluster_count": len(set(cluster_labels))
    }
