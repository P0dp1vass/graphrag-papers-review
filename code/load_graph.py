import json
import os
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", os.environ.get("NEO4J_PASSWORD", ""))

def _canonicalize_entity(name: str) -> str:
    return "ActGCG" if name == "ACTGCG" else name

def _add_paper(tx, pid: str, title: str) -> None:
    tx.run("MERGE (p:Paper {id: $pid}) SET p.title = $title",pid=pid,title=title)

def _add_entity(tx, name: str) -> None:
    tx.run("MERGE (e:Entity {name: $name})", name=name)

def _add_relation(tx, head: str, rel: str, tail: str, paper_id: str) -> None:
    tx.run(
        """
        MATCH (a:Entity {name: $head}), (b:Entity {name: $tail})
        MERGE (a)-[r:R {type: $rel}]->(b)
        SET r.source_ids =
            CASE
                WHEN $paper_id IN coalesce(r.source_ids, [])
                THEN r.source_ids
                ELSE coalesce(r.source_ids, []) + [$paper_id]
            END
        """,
        head=head,
        rel=rel,
        tail=tail,
        paper_id=paper_id
    ).consume()

def _mention(tx, pid: str, name: str) -> None:
    tx.run(
        """
        MATCH (p:Paper {id: $pid}), (e:Entity {name: $name})
        MERGE (p)-[:MENTIONS]->(e)
        """,
        pid=pid,
        name=name
    )

def create_constraints(driver) -> None:
    queries = [
        """
        CREATE CONSTRAINT paper_id_unique IF NOT EXISTS
        FOR (p:Paper) REQUIRE p.id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT entity_name_unique IF NOT EXISTS
        FOR (e:Entity) REQUIRE e.name IS UNIQUE
        """,
    ]
    with driver.session() as session:
        for query in queries:
            session.run(query).consume()

def load_triplets(driver) -> None:
    with open("data/triplets.jsonl") as f:
        records = [json.loads(line) for line in f if line.strip()]

    with driver.session() as session:
        for rec in records:
            session.execute_write(_add_paper, rec["paper_id"], rec["title"])
            for entity in rec["entities"]:
                name = _canonicalize_entity(entity)
                session.execute_write(_add_entity, name)
                session.execute_write(_mention, rec["paper_id"], name)
            for rel in rec["relations"]:
                session.execute_write(
                    _add_relation,
                    _canonicalize_entity(rel["head"]),
                    rel["relation"],
                    _canonicalize_entity(rel["tail"]),
                    rec["paper_id"]
                )

if __name__ == "__main__":
    driver = GraphDatabase.driver(URI, auth=AUTH)
    driver.verify_connectivity()
    create_constraints(driver)
    load_triplets(driver)
    with driver.session() as session:
        nodes = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        rels = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
        print(f"Nodes: {nodes}, edges: {rels}")
    driver.close()
