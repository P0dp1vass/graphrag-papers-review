import re

GENERIC_TERMS = {
    "ai",
    "api",
    "cpu",
    "gpu",
    "llm",
    "llms",
    "nlp",
    "rag",
    "what",
    "which",
    "how",
    "why",
    "when",
    "where",
    "does",
    "the",
    "retrieval-augmented",
    "fine-tuning",
    "post-training",
    "low-resource",
    "cross-modal",
    "state-of-the-art",
}

def extract_title_terms(question: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9]*(?:[._-][A-Za-z0-9]+)*", question)
    terms = []
    for word in words:
        name = word.lower()
        is_identifier = (
            sum(char.isupper() for char in word) >= 2 or "-" in word or "_" in word
        )
        if is_identifier and name not in GENERIC_TERMS and name not in terms:
            terms.append(name)
    return terms[:10]

def title_pattern(term: str) -> str:
    parts = re.split(r"[._-]+", term)
    return r"(?is).*\b" + r"[\W_]+".join(re.escape(part) for part in parts) + r"\b.*"

def rank_candidates(
    vector_hits: list[dict], title_hits: list[dict], k: int
) -> list[dict]:
    candidates = {row["id"]: {**row, "matched_names": []} for row in vector_hits}
    for row in title_hits:
        candidates[row["id"]] = dict(row)
    return sorted(
        candidates.values(),
        key=lambda row: (-len(row["matched_names"]), -row["score"], row["id"]),
    )[:k]

def retrieve_papers(
    session, vec: list[float], k: int, question: str = ""
) -> list[dict]:
    if k < 1:
        raise ValueError("k must be positive.")
    vector_hits = session.run(
        """
        CALL db.index.vector.queryNodes('paper_vec', $k, $vec)
        YIELD node, score
        RETURN node.id AS id, node.title AS title,
               node.abstract AS abstract, score
        ORDER BY score DESC, id
        """,
        k=k,
        vec=vec,
    ).data()
    terms = [
        {"name": name, "pattern": title_pattern(name)}
        for name in extract_title_terms(question)
    ]
    if not terms:
        return vector_hits
    title_hits = session.run(
        """
        MATCH (p:Paper)
        WHERE p.embedding IS NOT NULL
        WITH p, [term IN $terms WHERE p.title =~ term.pattern | term.name] AS matched_names
        WHERE size(matched_names) > 0
        RETURN p.id AS id, p.title AS title, p.abstract AS abstract,
               vector.similarity.cosine(p.embedding, $vec) AS score,
               matched_names
        ORDER BY size(matched_names) DESC, score DESC, id
        LIMIT $k
        """,
        terms=terms,
        vec=vec,
        k=k
    ).data()
    return rank_candidates(vector_hits, title_hits, k)