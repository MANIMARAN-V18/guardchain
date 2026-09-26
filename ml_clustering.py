"""
Machine Learning Wallet Behavior Clustering Module for GuardChain
Pure-Python K-Means feature clustering for resilient, lightweight execution on free-tier cloud environments.
"""

import math


def _euclidean_dist(v1, v2):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))


def _kmeans_cluster(features, k, max_iters=25):
    """
    Pure Python K-Means implementation (Lloyd's algorithm).
    """
    n = len(features)
    if n <= k:
        return list(range(n))

    # Initialize centroids deterministically
    step = n // k
    centroids = [list(features[i * step]) for i in range(k)]
    labels = [0] * n

    for _ in range(max_iters):
        # Assign points to nearest centroid
        new_labels = []
        for point in features:
            dists = [_euclidean_dist(point, c) for c in centroids]
            min_idx = dists.index(min(dists))
            new_labels.append(min_idx)

        if new_labels == labels:
            break
        labels = new_labels

        # Recompute centroids
        for c_idx in range(k):
            members = [features[i] for i, lbl in enumerate(labels) if lbl == c_idx]
            if members:
                dim = len(members[0])
                centroids[c_idx] = [sum(m[d] for m in members) / len(members) for d in range(dim)]

    return labels


def cluster_traced_wallets(edges, n_clusters=3):
    """
    Extracts feature vectors for all distinct wallets in the trace graph
    and applies K-Means clustering to partition them into behavioral categories:
      - Cluster 0: Core Dispatcher / Primary Suspect
      - Cluster 1: Layering Intermediary Mule
      - Cluster 2: Off-Ramp Liquidation Node
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
            wallet_stats[u] = {"sent_vol": 0.0, "recv_vol": 0.0, "tx_count": 0, "max_hop": hop, "is_ex": 0}
        if v not in wallet_stats:
            wallet_stats[v] = {"sent_vol": 0.0, "recv_vol": 0.0, "tx_count": 0, "max_hop": hop, "is_ex": 1 if is_ex else 0}

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
            float(st["tx_count"]),
            float(st["max_hop"]),
            float(st["is_ex"] * 5.0)
        ])

    k = min(n_clusters, len(wallets))
    if k < 2:
        cluster_labels = [0] * len(wallets)
    else:
        cluster_labels = _kmeans_cluster(features, k)

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
        "method": "Unsupervised K-Means Behavioral Clustering",
        "cluster_count": len(set(cluster_labels))
    }
