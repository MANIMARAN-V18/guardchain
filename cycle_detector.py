"""
Circular Fund Movement & Layering Cycle Detector for GuardChain
Identifies round-tripping, peel chains, and circular fund laundering loops.
"""

from collections import defaultdict


def detect_circular_patterns(edges):
    """
    Detects directed cycles and re-entrant wallet paths from a list of edges.
    
    edges: list of (from_addr, to_addr, value, hop, is_exchange, ...) or dicts.
    
    Returns:
      dict with:
        - circular_pattern_detected: bool
        - cycles: list of list of str (wallet paths forming cycles)
        - cycled_wallets: list of str (wallets involved in cycles)
        - summary: str
    """
    if not edges:
        return {
            "circular_pattern_detected": False,
            "cycles": [],
            "cycled_wallets": [],
            "summary": "No transactions analyzed."
        }

    # Normalize edges
    adj = defaultdict(list)
    for edge in edges:
        if isinstance(edge, dict):
            u = edge.get("from", "").lower()
            v = edge.get("to", "").lower()
        else:
            u = edge[0].lower()
            v = edge[1].lower()
        if u and v:
            adj[u].append(v)

    all_cycles = []
    visited = set()
    rec_stack = []

    def dfs(node):
        visited.add(node)
        rec_stack.append(node)

        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                # Cycle found! Extract cycle path
                idx = rec_stack.index(neighbor)
                cycle_path = rec_stack[idx:] + [neighbor]
                # Avoid duplicate representations of the same cycle
                norm_cycle = tuple(cycle_path[:-1])
                if not any(set(norm_cycle) == set(c[:-1]) for c in all_cycles):
                    all_cycles.append(cycle_path)

        rec_stack.pop()

    for start_node in list(adj.keys()):
        if start_node not in visited:
            dfs(start_node)

    cycled_wallets = list({w for cycle in all_cycles for w in cycle})

    if all_cycles:
        summary = (
            f"Circular laundering pattern detected! {len(all_cycles)} distinct cycle(s) "
            f"identified involving {len(cycled_wallets)} wallet(s). Funds were cycled back through prior addresses."
        )
    else:
        summary = "No circular fund movement detected. Funds flowed unidirectionally through the traced graph."

    return {
        "circular_pattern_detected": len(all_cycles) > 0,
        "cycles": all_cycles,
        "cycled_wallets": cycled_wallets,
        "summary": summary
    }
