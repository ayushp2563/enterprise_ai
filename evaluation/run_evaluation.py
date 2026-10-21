#!/usr/bin/env python3
"""Run a transparent heuristic RAG evaluation against a live API."""

import argparse
import json
import re
import statistics
import time
from pathlib import Path

import httpx


ABSTENTION_PHRASES = (
    "don't have enough information",
    "do not have enough information",
    "insufficient information",
)


def load_cases(path: Path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def evaluate_case(case, response, latency_seconds):
    answer = response["answer"]
    sources = response.get("sources", [])
    source_titles = {source["title"] for source in sources}
    expected_documents = set(case["expected_documents"])
    markers = {
        int(value)
        for value in re.findall(r"\[Source\s+(\d+)\]", answer, re.IGNORECASE)
    }
    valid_ids = {source.get("citation_id") for source in sources}
    abstained = any(phrase in answer.lower() for phrase in ABSTENTION_PHRASES)

    return {
        "id": case["id"],
        "retrieval_relevant": expected_documents.issubset(source_titles),
        "answer_terms_present": all(
            term.lower() in answer.lower() for term in case["expected_terms"]
        ),
        "citation_markers_valid": markers.issubset(valid_ids),
        "abstention_correct": abstained == case["should_abstain"],
        "latency_seconds": latency_seconds,
        "retrieved_documents": sorted(source_titles),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--token", required=True)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path(__file__).with_name("rag_cases.jsonl"),
    )
    args = parser.parse_args()

    results = []
    with httpx.Client(
        base_url=args.base_url,
        headers={"Authorization": f"Bearer {args.token}"},
        timeout=60,
    ) as client:
        for case in load_cases(args.dataset):
            started = time.perf_counter()
            response = client.post(
                "/api/query/",
                json={"question": case["question"], "top_k": 5},
            )
            response.raise_for_status()
            latency = time.perf_counter() - started
            results.append(evaluate_case(case, response.json(), latency))

    summary = {
        "case_count": len(results),
        "retrieval_relevance_rate": statistics.mean(
            item["retrieval_relevant"] for item in results
        ),
        "answer_term_rate": statistics.mean(
            item["answer_terms_present"] for item in results
        ),
        "citation_validity_rate": statistics.mean(
            item["citation_markers_valid"] for item in results
        ),
        "abstention_accuracy": statistics.mean(
            item["abstention_correct"] for item in results
        ),
        "latency_seconds": {
            "median": statistics.median(
                item["latency_seconds"] for item in results
            ),
            "maximum": max(item["latency_seconds"] for item in results),
        },
        "methodology": (
            "Deterministic expected-document and expected-term checks; "
            "not an objective measure of answer correctness."
        ),
    }
    print(json.dumps({"summary": summary, "cases": results}, indent=2))


if __name__ == "__main__":
    main()
