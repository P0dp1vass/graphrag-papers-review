import json
from neo4j import GraphDatabase
from load_graph import URI, AUTH

def add_abstracts(tx, papers: list[dict]) -> int:
    result = tx.run(
        """
        UNWIND $papers AS paper
        MATCH (p:Paper {id: paper.id})
        SET p.abstract = paper.abstract
        RETURN count(p) AS updated
        """,
        papers=papers,
    ).single()
    return result["updated"]

if __name__ == "__main__":
    with open("data/papers.json", encoding="utf-8") as f:
        papers = json.load(f)
    with (
        GraphDatabase.driver(URI, auth=AUTH) as driver,
        driver.session() as session,
    ):
        updated = session.execute_write(add_abstracts, papers)
    print(f"Add abstracts: {updated}")