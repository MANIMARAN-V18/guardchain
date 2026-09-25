import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")



class GraphStore:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

    def close(self):
        self.driver.close()

    def save_edge(self, from_addr, to_addr, value_eth, hop, is_exchange):
        """
        Creates (or reuses) two Wallet nodes and connects them
        with a SENT_TO relationship carrying the amount and hop number.
        Marks the destination node as an exchange if flagged.
        """
        query = """
        MERGE (a:Wallet {address: $from_addr})
        MERGE (b:Wallet {address: $to_addr})
        SET b.is_exchange = $is_exchange
        MERGE (a)-[r:SENT_TO {hop: $hop}]->(b)
        SET r.value_eth = $value_eth
        """
        with self.driver.session() as session:
            session.run(
                query,
                from_addr=from_addr,
                to_addr=to_addr,
                value_eth=value_eth,
                hop=hop,
                is_exchange=is_exchange
            )

    def save_all_edges(self, edges):
        """edges = list of (from_address, to_address, value_eth, hop, is_exchange)"""
        for from_addr, to_addr, value_eth, hop, is_exchange in edges:
            self.save_edge(from_addr, to_addr, value_eth, hop, is_exchange)
        print(f"Saved {len(edges)} edges to Neo4j.")