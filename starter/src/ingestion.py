"""Read the pinned Gutenberg snapshot and preserve chapter boundaries."""
import hashlib
import json
import logging
import re
import unicodedata
from pathlib import Path
from urllib.request import urlretrieve

from .models import DocumentPage

SOURCE = "https://www.gutenberg.org/ebooks/158"
DOWNLOAD = "https://www.gutenberg.org/cache/epub/158/pg158.txt"
HEADINGS = re.compile(r"^(VOLUME|CHAPTER) ([IVX]+)[ \t]*$", re.MULTILINE)


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = re.split(r"\n[ \t]*\n", text.strip())
    return "\n\n".join(" ".join(p.split()) for p in paragraphs if p.strip())


def load_corpus(data_dir: Path) -> list[DocumentPage]:
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    path = data_dir / "raw" / "158.txt"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".download")
        urlretrieve(DOWNLOAD, temporary)
        if hashlib.sha256(temporary.read_bytes()).hexdigest() != manifest["sha256"]:
            raise ValueError("Downloaded Gutenberg snapshot differs from the manifest")
        temporary.replace(path)

    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest["sha256"]:
        raise ValueError("Local Gutenberg snapshot differs from the manifest")
    pages, units = parse_chapters(raw.decode("utf-8-sig"))
    if units != manifest["units"] or len(pages) < 30:
        raise ValueError("Chapter boundaries differ from the manifest or corpus is too small")
    logging.info("Loaded %d chapters. Excluded front matter, contents and Gutenberg footer.", len(pages))
    return pages


def parse_chapters(raw: str) -> tuple[list[DocumentPage], list[dict]]:
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    end = raw.index("*** END OF THE PROJECT GUTENBERG EBOOK")
    headings = list(HEADINGS.finditer(raw, 0, end))
    pages = []
    units = []
    volume = ""
    for index, heading in enumerate(headings):
        kind, number = heading.groups()
        if kind == "VOLUME":
            volume = number
            continue
        stop = headings[index + 1].start() if index + 1 < len(headings) else end
        text = normalize_text(raw[heading.end():stop])
        if len(text) < 1500 or not volume:
            raise ValueError(f"Unexpected chapter: volume {volume}, chapter {number}")
        page = len(pages) + 1
        metadata = {"volume": volume, "chapter": number}
        pages.append(DocumentPage("pg158", SOURCE, page, text, metadata))
        units.append({
            "page": page, **metadata,
            "heading_line": raw.count("\n", 0, heading.start()) + 1,
            "last_line_before_boundary": raw.count("\n", 0, stop),
            "normalized_characters": len(text),
        })
    return pages, units
