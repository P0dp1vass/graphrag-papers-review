import json
import xml.etree.ElementTree as ET
import requests

def fetch_papers(limit: int) -> list[dict]:
    url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": "cat:cs.CL",
        "max_results": limit,
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(response.text)
    entries = root.findall("a:entry", ns)
    papers = []
    for entry in entries:
        title = " ".join(entry.find("a:title", ns).text.split())
        abstract = " ".join(entry.find("a:summary", ns).text.split())
        paper_id = entry.find("a:id", ns).text
        if len(abstract) >= 300:
            papers.append({"id": paper_id, "title": title, "abstract": abstract})
    return papers

if __name__ == "__main__":
    papers = fetch_papers(limit=500)
    print(f"Download: {len(papers)}")
    import os
    os.makedirs("data", exist_ok=True)
    with open("data/papers.json", "w") as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)