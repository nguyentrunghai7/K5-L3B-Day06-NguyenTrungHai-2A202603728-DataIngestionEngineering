"""Build fixed-width and paragraph-aware chunks with exact source offsets."""
import re

from .models import Chunk, DocumentPage


def make_chunk(page: DocumentPage, start: int, end: int) -> Chunk:
    return Chunk(
        f"{page.document_id}:{page.page}:{start}:{end}",
        page.document_id, page.source, page.page, page.text[start:end],
        {**page.metadata, "start": start, "end": end},
    )


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    if not 0 <= overlap < size:
        raise ValueError("Expected 0 <= overlap < size")
    chunks = []
    for start in range(0, len(page.text), size - overlap):
        end = min(start + size, len(page.text))
        chunks.append(make_chunk(page, start, end))
        if end == len(page.text):
            break
    return chunks


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    if max_size < 1:
        raise ValueError("Expected a positive maximum chunk size")
    spans = []
    for paragraph in re.finditer(r"[^\n]+", page.text):
        start, end = paragraph.span()
        while end - start > max_size:
            limit = start + max_size
            # Prefer sentence boundaries within the latter half, then whitespace.
            sentences = list(re.finditer(r'[.!?][”"’]*\s', page.text[start:limit + 1]))
            sentence_end = start + sentences[-1].end() - 1 if sentences else start
            word_end = page.text.rfind(" ", start + 1, limit + 1)
            cut = sentence_end if sentence_end >= start + max_size / 2 else word_end
            cut = cut if cut > start else limit
            spans.append((start, cut))
            start = cut + int(page.text[cut] == " ")
        spans.append((start, end))

    groups = []
    for start, end in spans:
        if groups and end - groups[-1][0] <= max_size:
            groups[-1] = (groups[-1][0], end)
        else:
            groups.append((start, end))
    return [make_chunk(page, start, end) for start, end in groups]
