"""
Graph Storage and Case Clustering Engine for GuardChain
Manages Neo4j Aura Graph Database queries, Case node tracking,
and cross-investigation syndicate cluster detection with local fallback.
"""

import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# Local fallback cache path
LOCAL_CASES_FILE = os.path.join(os.path.dirname(__file__), "cases_cache.json")


def _read_local_cache():
    if os.path.exists(LOCAL_CASES_FILE):
        try:
            with open(LOCAL_CASES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _write_local_cache(data):
    try:
        with open(LOCAL_CASES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


class GraphStore:
    def __init__(self):
        self.driver = None
        if NEO4J_URI and NEO4J_USER and NEO4J_PASSWORD:
            try:
                from neo4j import GraphDatabase
                self.driver = GraphDatabase.driver(
                    NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
                )
            except Exception as e:
                print(f"[GraphStore] Warning: Could not connect to Neo4j ({e}). Using local fallback.")

    def close(self):
        if self.driver:
            try:
                self.driver.close()
            except Exception:
                pass

    def save_edge(self, from_addr, to_addr, value, hop, is_exchange, chain="Ethereum"):
        """Saves a single transaction edge with chain awareness."""
        if not self.driver:
            return

        query = """
        MERGE (a:Wallet {address: $from_addr, chain: $chain})
        MERGE (b:Wallet {address: $to_addr, chain: $chain})
        SET b.is_exchange = $is_exchange
        MERGE (a)-[r:SENT_TO {hop: $hop, chain: $chain}]->(b)
        SET r.value = $value
        """
        try:
            with self.driver.session() as session:
                session.run(
                    query,
                    from_addr=from_addr,
                    to_addr=to_addr,
                    value=value,
                    hop=hop,
                    is_exchange=is_exchange,
                    chain=chain
                )
        except Exception as e:
            print(f"[GraphStore] Neo4j save_edge error: {e}")

    def save_case_and_edges(self, root_wallet, chain, freeze_score, edges, case_id=None):
        """
        Saves all traced edges AND registers/updates a Case node.
        Reuses deterministic case IDs per (chain, root_wallet) to prevent duplicate self-clusters.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        root_clean = root_wallet.strip()
        chain_clean = chain.strip().capitalize()
        
        # Deterministic Case ID per (Chain, Root Wallet) ensures idempotent updates
        if not case_id:
            case_id = f"CASE-{chain_clean[:3].upper()}-{root_clean.lower()}"

        # 1. Update local cache
        cache = _read_local_cache()
        wallets_in_trace = list({e[0] for e in edges} | {e[1] for e in edges}) if edges else [root_clean]
        exchanges_in_trace = [e[1] for e in edges if (e[4] if len(e) > 4 else False)]

        # Remove duplicate case if exists for this case_id or root_wallet on same chain
        cache = [c for c in cache if not (c.get("case_id") == case_id or (c.get("root_wallet", "").lower() == root_clean.lower() and c.get("chain", "").lower() == chain_clean.lower()))]
        cache.append({
            "case_id": case_id,
            "root_wallet": root_clean,
            "chain": chain_clean,
            "freeze_score": freeze_score,
            "timestamp": timestamp,
            "wallets": wallets_in_trace,
            "exchanges": exchanges_in_trace,
            "edge_count": len(edges)
        })
        _write_local_cache(cache)

        # 2. Save to Neo4j if available
        if not self.driver:
            return case_id

        try:
            # Save edges
            for edge in edges:
                f_addr = edge[0]
                t_addr = edge[1]
                val = edge[2]
                hop = edge[3]
                is_ex = edge[4] if len(edge) > 4 else False
                self.save_edge(f_addr, t_addr, val, hop, is_ex, chain=chain_clean)

            # Create/Update Case node and link
            case_query = """
            MERGE (c:Case {case_id: $case_id})
            SET c.root_wallet = $root_wallet,
                c.chain = $chain,
                c.freeze_score = $freeze_score,
                c.timestamp = $timestamp
            WITH c
            OPTIONAL MATCH (c)-[old_r:INVOLVES]->()
            DELETE old_r
            WITH c
            UNWIND $wallets AS w_addr
            MERGE (w:Wallet {address: w_addr, chain: $chain})
            MERGE (c)-[:INVOLVES]->(w)
            """
            with self.driver.session() as session:
                session.run(
                    case_query,
                    case_id=case_id,
                    root_wallet=root_clean,
                    chain=chain_clean,
                    freeze_score=freeze_score,
                    timestamp=timestamp,
                    wallets=wallets_in_trace
                )
        except Exception as e:
            print(f"[GraphStore] Neo4j save_case error: {e}")

        return case_id

    def save_all_edges(self, edges, chain="Ethereum"):
        """Backward-compatible helper."""
        for edge in edges:
            f = edge[0]
            t = edge[1]
            val = edge[2]
            hop = edge[3]
            is_ex = edge[4] if len(edge) > 4 else False
            self.save_edge(f, t, val, hop, is_ex, chain=chain)

    def get_clusters(self):
        """
        Detects overlapping cases that share common downstream wallets or exchanges,
        identifying multi-suspect fraud syndicates.
        Strictly excludes matches where case_1 root wallet == case_2 root wallet.
        """
        # Try Neo4j first
        if self.driver:
            try:
                cluster_query = """
                MATCH (c1:Case)-[:INVOLVES]->(w:Wallet)<-[:INVOLVES]-(c2:Case)
                WHERE c1.root_wallet <> c2.root_wallet AND c1.case_id < c2.case_id
                RETURN c1.case_id AS case1, c1.root_wallet AS root1, c1.chain AS chain1,
                       c2.case_id AS case2, c2.root_wallet AS root2, c2.chain AS chain2,
                       collect(DISTINCT w.address) AS shared_wallets,
                       collect(DISTINCT CASE WHEN w.is_exchange = true THEN w.address ELSE null END) AS shared_exchanges
                """
                with self.driver.session() as session:
                    result = session.run(cluster_query)
                    records = []
                    for r in result:
                        shared_w = [w for w in r["shared_wallets"] if w]
                        shared_e = [e for e in r["shared_exchanges"] if e]
                        records.append({
                            "case_1": r["case1"],
                            "root_1": r["root1"],
                            "chain_1": r["chain1"],
                            "case_2": r["case2"],
                            "root_2": r["root2"],
                            "chain_2": r["chain2"],
                            "shared_wallets": shared_w,
                            "shared_exchanges": shared_e,
                            "overlap_count": len(shared_w)
                        })
                    return {
                        "clusters_detected": len(records),
                        "syndicate_linkages": records,
                        "source": "Neo4j Graph Database"
                    }
            except Exception as e:
                print(f"[GraphStore] Neo4j cluster query error: {e}. Falling back to cache.")

        # Local cache clustering
        cache = _read_local_cache()
        linkages = []
        for i in range(len(cache)):
            for j in range(i + 1, len(cache)):
                c1 = cache[i]
                c2 = cache[j]
                
                # Exclude cases that have the exact same root wallet (repeated queries)
                if c1.get("root_wallet", "").lower() == c2.get("root_wallet", "").lower():
                    continue

                w1 = set(c1.get("wallets", []))
                w2 = set(c2.get("wallets", []))
                shared = list(w1.intersection(w2))
                
                ex1 = set(c1.get("exchanges", []))
                ex2 = set(c2.get("exchanges", []))
                shared_ex = list(ex1.intersection(ex2))

                if shared:
                    linkages.append({
                        "case_1": c1.get("case_id"),
                        "root_1": c1.get("root_wallet"),
                        "chain_1": c1.get("chain"),
                        "case_2": c2.get("case_id"),
                        "root_2": c2.get("root_wallet"),
                        "chain_2": c2.get("chain"),
                        "shared_wallets": shared,
                        "shared_exchanges": shared_ex,
                        "overlap_count": len(shared)
                    })

        return {
            "clusters_detected": len(linkages),
            "syndicate_linkages": linkages,
            "total_cases_tracked": len(cache),
            "source": "Local Forensic Knowledge Store"
        }