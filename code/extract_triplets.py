import json
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:7b-instruct-q4_K_M"

SYSTEM_PROMPT = """You are a knowledge extractor. Extract entities and relationships from the text.
Respond ONLY with valid JSON, without any explanations or markdown formatting.
Format:
{
  "entities": ["NAME1", "NAME2"],
  "relations": [{"head": "NAME1", "relation": "VERB_IN_CAPS", "tail": "NAME2"}]
}
Rules:
- "head" and "tail" must be strings taken from "entities" (copy them exactly).
- "relation" must be in ALL CAPS and chosen from the following list: IMPROVES, USES, EVALUATED_ON, PROPOSED_BY, APPLIED_TO, RELATED_TO, EXTENDS.
- Entities should be short names (2–4 words), not full sentences or phrases."""

ALLOWED_RELATIONS = {
    "IMPROVES",
    "EXTENDS",
    "USES",
    "EVALUATED_ON",
    "PROPOSED_BY",
    "APPLIED_TO",
    "RELATED_TO"
}

def validate_triplets(data: dict) -> dict:
    entities = set(data.get("entities", []))
    relations = []
    for rel in data.get("relations", []):
        head, tail = rel.get("head"), rel.get("tail")
        relation = rel.get("relation")
        if not head or not tail or head not in entities or tail not in entities:
            continue
        if relation not in ALLOWED_RELATIONS:
            relation = "RELATED_TO"
        relations.append({"head": head, "relation": relation, "tail": tail})
    used = {r["head"] for r in relations} | {r["tail"] for r in relations}
    return {"entities": sorted(used), "relations": relations}

def extract_triplets(text: str) -> dict:
    payload = {
        "model": MODEL,
        "stream": False,
        "options": {"temperature": 0},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ]
    }
    for attempt in range(2):
        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=120)
            response.raise_for_status()
            answer = response.json()["message"]["content"]
            return validate_triplets(json.loads(answer))
        except (requests.RequestException, json.JSONDecodeError) as e:
            last_error = e
            continue
    raise SystemExit(last_error)
