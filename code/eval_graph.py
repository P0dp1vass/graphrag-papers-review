import json
import re
from pathlib import Path
from statistics import mean
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
from qa import (
    AUTH,
    GENERATION_OPTIONS,
    LLM,
    MODEL_NAME,
    URI,
    build_prompt,
    generate_answer,
    prepare_context
)

ROOT = Path(__file__).resolve().parents[1]
MODES = ("retrieval_only", "graph_enriched")
CASES = [
    {
        "id": "rag_fgo",
        "question": "What does RAG-FGO optimize, and how does its memory pool help?",
        "expected_source_ids": ["http://arxiv.org/abs/2611.17788v1"],
        "expect_abstention": False,
        "reference_facts": [
            "Optimizes generative retrieval/query-rewriting strategies, including prompts and decoding parameters.",
            "The elite-preserving memory pool accumulates high-quality strategies and mitigates noisy feedback.",
        ],
    },
    {
        "id": "bioformer",
        "question": "How does Bioformer-RetroMAE compare with PubMedBERT on biomedical retrieval?",
        "expected_source_ids": ["http://arxiv.org/abs/2611.19862v1"],
        "expect_abstention": False,
        "reference_facts": [
            "Relative to PubMedBERT, biomedical retrieval MAP improves by 37.0% and Recall@100 by 29.1%.",
            "These are retrieval results, not a demonstrated improvement in end-to-end RAG generation.",
        ],
    },
    {
        "id": "textsphere",
        "question": "How does TextSphere add text conditioning to Sphere Encoder?",
        "expected_source_ids": ["http://arxiv.org/abs/2611.23155v1"],
        "expect_abstention": False,
        "reference_facts": [
            "Pretrained CLIP text embeddings are incorporated through adaptive layer normalization (AdaLN).",
            "The original spherical sampling mechanism is retained; SSAU addresses cross-modal alignment and uniformity.",
        ],
    },
    {
        "id": "actgcg",
        "question": "How does ActGCG reproduce activation steering without white-box access at generation time?",
        "expected_source_ids": ["http://arxiv.org/abs/2611.17481v1"],
        "expect_abstention": False,
        "reference_facts": [
            "ActGCG modifies Greedy Coordinate Gradient to optimize an input suffix matching steering-induced target activations.",
            "Inference uses the suffix rather than modifying hidden states; white-box access is not claimed unnecessary during optimization.",
            "Steering equivalence depends on the behavior; anti-refusal results are weaker than German-language steering.",
        ],
    },
    {
        "id": "out_of_scope",
        "question": "What is the current retail price of an NVIDIA RTX 4060 Ti?",
        "expected_source_ids": [],
        "expect_abstention": True,
        "reference_facts": [
            "The retrieved research abstracts do not establish a current retail price; abstain rather than invent a price.",
        ],
    },
]

def arxiv_ids(text: str) -> set[str]:
    return set(re.findall(r"https?://arxiv\.org/abs/(\d{4}\.\d{4,5}(?:v\d+)?)", text))

def citation_diagnostics(answer: str, papers: list[dict]) -> dict:
    allowed = set()
    for paper in papers:
        allowed.update(arxiv_ids(paper["id"]))
    cited = arxiv_ids(answer)
    allowed.update(re.sub(r"v\d+$", "", value) for value in allowed.copy())
    return {
        "cited_arxiv_ids": sorted(cited),
        "retrieved_source_cited": bool(cited & allowed),
        "unretrieved_arxiv_ids": sorted(cited - allowed)
    }

def summarize(results: list[dict]) -> dict:
    positives = [row for row in results if row["expected_source_ids"]]
    summary = {
        "cases_prepared": len(results),
        "retrieval_hit_at_3": (
            sum(row["retrieval_hit"] for row in positives) / len(positives)
            if positives
            else None
        ),
        "modes": {},
        "quality_conclusion": "Pending review; URL checks and successful requests do not establish answer quality."
    }
    for mode in MODES:
        entries = [row["answers"][mode] for row in results if mode in row["answers"]]
        completed = [entry for entry in entries if "error" not in entry]
        summary["modes"][mode] = {
            "completed": len(completed),
            "errors": sum("error" in entry for entry in entries),
            "truncated": sum(entry["truncated"] for entry in completed),
            "answers_with_retrieved_source_url": sum(entry["citations"]["retrieved_source_cited"] for entry in completed),
            "answers_with_unretrieved_arxiv_url": sum(bool(entry["citations"]["unretrieved_arxiv_ids"]) for entry in completed),
            "mean_generation_wall_seconds": (
                mean(entry["wall_seconds"] for entry in completed)
                if completed
                else None
            ),
            "quality_reviews_completed": sum(entry["review"]["correctness"] is not None for entry in completed)
        }
    return summary

def save_report(path: Path, report: dict) -> None:
    report["summary"] = summarize(report["results"])
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)

def prepare_cases(driver, model) -> list[dict]:
    results = []
    for case in CASES:
        context = prepare_context(case["question"], driver, model)
        found = {paper["id"] for paper in context["papers"]}
        results.append(
            {
                **case,
                "context": context,
                "retrieval_hit": (
                    bool(set(case["expected_source_ids"]) & found)
                    if case["expected_source_ids"]
                    else None
                ),
                "answers": {},
                "comparison": None,
                "comparison_notes": ""
            }
        )
    return results

def run_answers(report: dict, output: Path) -> None:
    for i, row in enumerate(report["results"]):
        order = MODES if i % 2 == 0 else tuple(reversed(MODES))
        row["generation_order"] = list(order)
        for mode in order:
            if mode in row["answers"]:
                continue
            facts = row["context"]["facts"] if mode == "graph_enriched" else []
            prompt = build_prompt(row["question"], row["context"]["papers"], facts)
            print(f"[{i + 1}/{len(report['results'])}] {row['id']} / {mode}", flush=True)
            try:
                generated = generate_answer(prompt)
                generated["citations"] = citation_diagnostics(
                    generated["answer"], row["context"]["papers"]
                )
                generated["review"] = {
                    "correctness": None,
                    "groundedness": None,
                    "citation_support": None,
                    "notes": ""
                }
                row["answers"][mode] = {"prompt": prompt, **generated}
                print(generated["answer"], flush=True)
            except Exception as error:
                row["answers"][mode] = {
                    "prompt": prompt,
                    "error": f"{type(error).__name__}: {error}"
                }
                print(row["answers"][mode]["error"], flush=True)
            save_report(output, report)

def main(*, output: Path | None = None, resume: Path | None = None) -> None:
    if output is not None and resume is not None:
        raise ValueError("Specify either an output path or a report to resume.")
    if resume is not None:
        output = resume.resolve()
        report = json.loads(output.read_text(encoding="utf-8"))
        if (
            report["llm"] != LLM
            or report["generation_options"] != GENERATION_OPTIONS
            or report["embedding_model"] != MODEL_NAME
        ):
            raise ValueError("Model settings changed; start a new evaluation.")
    else:
        output = (
            output or ROOT / "data" / "evaluations" / "graph_eval.json"
        )
        if output.exists():
            raise FileExistsError(f"Report already exists: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        model = SentenceTransformer(MODEL_NAME, device="cpu")
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            driver.verify_connectivity()
            results = prepare_cases(driver, model)
        report = {
            "evaluation_type": "Small English development ablation, not a held-out benchmark.",
            "reference_annotation": "AI-assisted reference notes from corpus abstracts; needs human review.",
            "retrieval": "Same frozen title-aware/vector top-3 in both arms.",
            "llm": LLM,
            "embedding_model": MODEL_NAME,
            "generation_options": dict(GENERATION_OPTIONS),
            "limitations": [
                "Five development questions, some already used for debugging.",
                "No automatic semantic grading; manual review fields start empty.",
                "Citation diagnostics check URL membership, not factual support.",
                "Latency includes caching and model loading effects.",
                "The graph adds extracted facts, not additional documents.",
                "Temperature zero and a fixed seed do not guarantee bitwise determinism.",
            ],
            "review_rubric": {
                "correctness": "0 incorrect or unsupported answer/refusal; 1 partly correct; 2 correct answer or justified abstention.",
                "groundedness": "0 unsupported central claims; 1 mixed; 2 factual claims supported by the retrieved abstracts.",
                "citation_support": "0 missing/incorrect required citations; 1 partial; 2 adequate supporting citations. Null/not applicable for pure abstentions.",
                "comparison": "retrieval_only, graph_enriched, tie, or inconclusive. Base this on content, not answer length.",
            },
            "results": results,
        }
        save_report(output, report)
    print(f"Report: {output}", flush=True)
    run_answers(report, output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2), flush=True)

if __name__ == "__main__":
    main()