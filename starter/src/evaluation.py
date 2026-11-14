"""Score exact normalized evidence and retain all retrieval results."""


def has_evidence(hit: dict, gold: dict) -> bool:
    metadata = hit["metadata"]
    return (
        metadata["document_id"] == gold["gold_source_id"]
        and metadata["page"] == gold["gold_page"]
        and " ".join(gold["evidence_quote"].split()) in " ".join(hit["text"].split())
    )


def evaluate_query(question: dict, hits: list[dict]) -> dict:
    golds = [question, *question.get("alternative_gold", [])]
    for hit in hits:
        hit["evidence_hit"] = any(has_evidence(hit, gold) for gold in golds)
    return {
        "benchmark": question, "hits": hits,
        "hit1": bool(hits and hits[0]["evidence_hit"]),
        "hit3": any(hit["evidence_hit"] for hit in hits),
    }


def summarize(traces: list[dict]) -> dict:
    summary = {}
    for strategy in ("A", "B", "C"):
        summary[strategy] = {}
        for split in ("dev", "test"):
            rows = [r for r in traces if r["strategy"] == strategy and r["benchmark"]["split"] == split]
            filtered = [r for r in rows if r["benchmark"].get("filter")]
            summary[strategy][split] = {
                "questions": len(rows),
                "hit1": sum(r["hit1"] for r in rows),
                "hit3": sum(r["hit3"] for r in rows),
                "filter_questions": len(filtered),
                "filter_compliant": sum(
                    bool(r["hits"]) and all(
                        all(h["metadata"].get(k) == v for k, v in r["benchmark"]["filter"].items())
                        for h in r["hits"]
                    )
                    for r in filtered
                ),
            }
    return summary
