"""Run the controlled ingestion and retrieval benchmark."""
import argparse
import csv
import hashlib
import json
import logging
import platform
from datetime import datetime
from importlib.metadata import version
from pathlib import Path
from statistics import mean, median
from time import perf_counter

from .chunking import by_paragraph, fixed_size
from .embeddings import LocalEmbedder
from .evaluation import evaluate_query, summarize
from .ingestion import load_corpus
from .store import ChromaStore

ROOT = Path(__file__).resolve().parents[2]


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_benchmark(path: Path, pages: list) -> list[dict]:
    questions = json.loads(path.read_text(encoding="utf-8"))
    if len({q["id"] for q in questions}) != len(questions):
        raise ValueError("Duplicate question ID")
    lookup = {(p.document_id, p.page): p for p in pages}
    volumes = {p.metadata["volume"] for p in pages}
    for question in questions:
        if question["split"] not in ("dev", "test") or not question["expected_answer"].strip():
            raise ValueError(f"Invalid split or answer: {question['id']}")
        for gold in [question, *question.get("alternative_gold", [])]:
            page = lookup[(gold["gold_source_id"], gold["gold_page"])]
            evidence = " ".join(gold["evidence_quote"].split())
            if not evidence or evidence not in " ".join(page.text.split()):
                raise ValueError(f"Gold evidence missing: {question['id']}")
        metadata_filter = question.get("filter")
        if metadata_filter and (
            set(metadata_filter) != {"volume"} or metadata_filter["volume"] not in volumes
            or not question.get("context")
        ):
            raise ValueError(f"Invalid source filter: {question['id']}")
    dev = [q for q in questions if q["split"] == "dev"]
    test = [q for q in questions if q["split"] == "test"]
    if len(dev) < 15 or len(test) < 5 or sum(bool(q.get("filter")) for q in questions) < 3:
        raise ValueError("Insufficient questions or filter cases")
    if not any(q.get("filter") for q in test):
        raise ValueError("Test split requires at least one filter question")
    return questions


def prepare_audit(pages, chunks_by_strategy, traces) -> dict:
    # Preselected positions: the middle character of each of the first ten chapters.
    coherence = []
    for page in pages[:10]:
        offset = len(page.text) // 2
        for strategy, chunks in chunks_by_strategy.items():
            candidates = [
                c for c in chunks if c.page == page.page
                and c.metadata["start"] <= offset < c.metadata["end"]
            ]
            if not candidates and page.text[offset].isspace():
                candidates = [
                    c for c in chunks if c.page == page.page
                    and c.metadata["start"] <= offset + 1 < c.metadata["end"]
                ]
            chosen = min(candidates, key=lambda c: c.metadata["start"])
            coherence.append({
                "strategy": strategy, "page": page.page, "offset": offset,
                "chunk_id": chosen.chunk_id, "text": chosen.text, "label": None, "reason": "",
            })

    metadata = []
    grounding = []
    for row in traces:
        question = row["benchmark"]
        if question["split"] != "test":
            continue
        for rank, hit in enumerate(row["hits"], 1):
            meta = hit["metadata"]
            source = pages[meta["page"] - 1]
            matches = (
                meta["document_id"] == source.document_id and meta["source"] == source.source
                and all(meta[k] == v for k, v in source.metadata.items())
                and hit["text"] == source.text[meta["start"]:meta["end"]]
            )
            metadata.append({
                "strategy": row["strategy"], "id": question["id"], "rank": rank,
                "chunk_id": hit["chunk_id"], "metadata": meta, "matched_snapshot": matches,
                "manual_valid": None, "reason": "",
            })
        grounding.append({
            "strategy": row["strategy"], "id": question["id"], "label": None, "reason": "",
        })
    return {"coherence": coherence, "metadata": metadata, "grounding": grounding}


def write_experiment_log(summary: dict, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            "strategy", "chunking", "chunk_size", "overlap", "metadata", "filter",
            "vectorizer", "hypothesis", "dev_hit1", "dev_hit3", "test_hit1", "test_hit3", "notes",
        ])
        for strategy, hypothesis in (
            ("A", "Overlap may preserve evidence around fixed boundaries."),
            ("B", "Paragraph and sentence boundaries may preserve context."),
            ("C", "Volume filter may reduce results from unrelated volumes."),
        ):
            ratios = [
                f"{summary[strategy][split][key]}/{summary[strategy][split]['questions']}"
                for split in ("dev", "test") for key in ("hit1", "hit3")
            ]
            writer.writerow([
                strategy, "fixed" if strategy == "A" else "paragraph", 500,
                50 if strategy == "A" else 0, "document_id source page volume chapter start end",
                "volume if supplied" if strategy == "C" else "", LocalEmbedder.model_name,
                hypothesis, *ratios, "Shares B index" if strategy == "C" else "",
            ])


def run(state: Path, results: Path) -> None:
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    pages = load_corpus(ROOT / "data")
    benchmark_path = ROOT / "benchmark" / "questions.json"
    questions = load_benchmark(benchmark_path, pages)
    benchmark_hash = hashlib.sha256(benchmark_path.read_bytes()).hexdigest()
    embedder = LocalEmbedder(state / "models")
    store = ChromaStore(state / "chroma")
    chunks_by_strategy = {}
    indexes = {}
    stats = {}
    for strategy, chunk_page in (
        ("A", lambda page: fixed_size(page, 500, 50)),
        ("B", lambda page: by_paragraph(page, 500)),
    ):
        tick = perf_counter()
        chunks = [chunk for page in pages for chunk in chunk_page(page)]
        collection, reused = store.prepare(strategy, chunks, embedder)
        ingest = round(perf_counter() - tick, 4)
        reloaded, reload_reused = store.prepare(strategy, chunks, embedder)
        if reloaded.count() != len(chunks) or not reload_reused:
            raise RuntimeError(f"Reload check failed for {strategy}")
        lengths = [len(c.text) for c in chunks]
        stats[strategy] = {
            "chunks": len(chunks), "min_chars": min(lengths), "max_chars": max(lengths),
            "median_chars": median(lengths), "mean_chars": round(mean(lengths), 2),
            "total_chars": sum(lengths), "ingest_seconds": ingest, "usd": 0,
            "index": collection.name, "reused": reused, "reload_chunks": reloaded.count(),
        }
        indexes[strategy] = collection
        chunks_by_strategy[strategy] = chunks
        logging.info("%s: %d chunks, ingest %.2fs, reused=%s", strategy, len(chunks), ingest, reused)
    indexes["C"] = indexes["B"]
    chunks_by_strategy["C"] = chunks_by_strategy["B"]
    stats["C"] = {**stats["B"], "ingest_seconds": 0, "shared_index": "B"}

    traces = []
    winner = None
    for split in ("dev", "test"):
        split_questions = [q for q in questions if q["split"] == split]
        vectors = embedder.embed_queries([q["question"] for q in split_questions])
        for strategy in ("A", "B", "C"):
            for question, vector in zip(split_questions, vectors, strict=True):
                tick = perf_counter()
                where = question.get("filter") if strategy == "C" else None
                hits = store.search(indexes[strategy], vector, where)
                row = evaluate_query(question, hits)
                traces.append({
                    "strategy": strategy, "applied_filter": where,
                    "search_ms": round((perf_counter() - tick) * 1000, 3), **row,
                })
        if split == "dev":
            dev_summary = summarize(traces)
            winner = max(
                ("A", "B", "C"),
                key=lambda s: (dev_summary[s]["dev"]["hit3"], dev_summary[s]["dev"]["hit1"]),
            )
            logging.info("Selected on dev before running test: %s", winner)

    summary = summarize(traces)
    write_json(results / "summary.json", {
        "run_at": started, "python": platform.python_version(), "model": embedder.model_name,
        "dimensions": embedder.dimensions, "model_revision": embedder.revision,
        "fastembed": version("fastembed"),
        "onnxruntime": version("onnxruntime"), "chromadb": version("chromadb"),
        "metric": "cosine", "index_type": "HNSW", "cost_usd": 0, "selected_on_dev": winner,
        "benchmark_sha256": benchmark_hash,
        "stats": stats, "metrics": summary,
    })
    write_json(results / "traces.json", traces)
    audit_path = results / "audit-review.json"
    audit = prepare_audit(pages, chunks_by_strategy, traces)
    if audit_path.exists():
        audit_path = results / "audit-generated.json"
        logging.info("Preserved existing audit review; fresh samples are in %s", audit_path)
    write_json(audit_path, audit)
    experiment_log = ROOT / "artifacts" if results.resolve() == ROOT / "results" else results
    write_experiment_log(summary, experiment_log / "experiment_log.csv")
    logging.info("Saved %d search traces to %s", len(traces), results)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=ROOT / "results")
    parser.add_argument("--state", type=Path, default=ROOT / ".lab06")
    args = parser.parse_args()
    args.results.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(args.results / "run.log", mode="w", encoding="utf-8"),
        ],
    )
    try:
        run(args.state, args.results)
    except Exception:
        logging.exception("Lab benchmark failed")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
