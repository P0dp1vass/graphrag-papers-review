import json
import os
from extract_triplets import extract_triplets

PAPERS_FILE = "data/papers.json"
OUT_FILE = "data/triplets.jsonl"

def load_done_ids() -> set[str]:
    if not os.path.exists(OUT_FILE):
        return set()
    done = set()
    with open(OUT_FILE) as f:
        for line in f:
            if line.strip():
                done.add(json.loads(line)["paper_id"])
    return done

def main() -> None:
    with open(PAPERS_FILE) as f:
        papers = json.load(f)
    done = load_done_ids()

    for i, paper in enumerate(papers):
        if paper["id"] in done:
            continue
        try:
            triplets = extract_triplets(paper["abstract"])
        except SystemExit as e:
            print(f"[{i}] Failed {paper['id']}: {e}")
            continue
        record = {"paper_id": paper["id"], "title": paper["title"], **triplets}
        with open(OUT_FILE, "a") as out:
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
        if i % 10 == 0:
            print(f"[{i}/{len(papers)}] {paper['title'][:50]}")

if __name__ == "__main__":
    main()