from __future__ import annotations

import re
from pathlib import Path
from dataclasses import dataclass
import fitz  # PyMuPDF


@dataclass
class CleanResult:
    input_path: Path
    output_path: Path
    pages: int
    removed_blocks: int
    watermark_annotations_removed: int


# Matches the common PDF marked-content form used for watermarks, e.g.
# /Artifact <</Subtype /Watermark /Type /Pagination >> BDC ... EMC
# The scanner below is deliberately small and conservative: it only removes
# marked-content blocks whose BDC prefix explicitly contains /Subtype /Watermark.
TOKEN_RE = re.compile(rb"(?<![A-Za-z0-9_])(?:BDC|BMC|EMC)(?![A-Za-z0-9_])")


def _find_dict_before_bdc(data: bytes, bdc_start: int) -> tuple[int, bytes] | None:
    """Return (block_start, prefix) for a BDC operator if its property dict is nearby.

    We search back to the nearest '/' tag before the <<...>> dictionary. This is
    intentionally conservative and targets the standard Artifact/Watermark form.
    """
    # Limit backward search so a malformed stream cannot cause huge scans.
    left = max(0, bdc_start - 4096)
    window = data[left:bdc_start]
    dict_end_rel = window.rfind(b">>")
    if dict_end_rel < 0:
        return None
    dict_start_rel = window.rfind(b"<<", 0, dict_end_rel)
    if dict_start_rel < 0:
        return None
    prop_dict = window[dict_start_rel:dict_end_rel + 2]
    if not re.search(rb"/Subtype\s*/Watermark\b", prop_dict):
        return None

    # Find the tag name immediately preceding the dictionary, usually /Artifact.
    before = window[:dict_start_rel]
    m = re.search(rb"/[A-Za-z0-9_.+-]+\s*$", before)
    if not m:
        return None
    block_start_rel = m.start()
    block_start = left + block_start_rel
    prefix = data[block_start:bdc_start]
    return block_start, prefix


def strip_watermark_marked_content(data: bytes) -> tuple[bytes, int]:
    """Remove explicit /Subtype /Watermark marked-content blocks from a stream."""
    tokens = list(TOKEN_RE.finditer(data))
    if not tokens:
        return data, 0

    stack: list[dict] = []
    removals: list[tuple[int, int]] = []

    for tok in tokens:
        op = tok.group(0)
        if op == b"BDC":
            info = _find_dict_before_bdc(data, tok.start())
            if info:
                block_start, _ = info
                stack.append({"watermark": True, "start": block_start})
            else:
                stack.append({"watermark": False, "start": tok.start()})
        elif op == b"BMC":
            # BMC has no property dictionary. We do not remove it automatically.
            stack.append({"watermark": False, "start": tok.start()})
        elif op == b"EMC":
            if stack:
                opened = stack.pop()
                if opened["watermark"]:
                    removals.append((opened["start"], tok.end()))

    if not removals:
        return data, 0

    # Remove from end to beginning to keep offsets stable.
    out = bytearray(data)
    for start, end in sorted(removals, reverse=True):
        # Preserve token separation with one space to avoid accidental concatenation.
        out[start:end] = b" "
    return bytes(out), len(removals)


def _unique_output_path(input_path: Path, suffix: str = "_clean") -> Path:
    candidate = input_path.with_name(f"{input_path.stem}{suffix}{input_path.suffix}")
    i = 2
    while candidate.exists():
        candidate = input_path.with_name(f"{input_path.stem}{suffix}_{i}{input_path.suffix}")
        i += 1
    return candidate


def _count_pages(path: Path) -> int:
    d = fitz.open(path)
    try:
        return len(d)
    finally:
        d.close()


def clean_pdf(input_path: str | Path, output_path: str | Path | None = None) -> CleanResult:
    input_path = Path(input_path).expanduser().resolve()
    if input_path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    output_path = Path(output_path).expanduser().resolve() if output_path else _unique_output_path(input_path)

    doc = fitz.open(input_path)
    removed_blocks = 0
    removed_annots = 0

    try:
        for page in doc:
            # Remove explicit PDF watermark annotations when present.
            annot = page.first_annot
            while annot:
                nxt = annot.next
                try:
                    # PDF annotation subtype "Watermark" is type number 25 in many readers,
                    # but compare the human-readable name to avoid relying on the number.
                    atype = annot.type
                    if atype and len(atype) > 1 and str(atype[1]).lower() == "watermark":
                        page.delete_annot(annot)
                        removed_annots += 1
                except Exception:
                    pass
                annot = nxt

            # Rewrite each page content stream, removing only explicit Watermark artifacts.
            for xref in page.get_contents() or []:
                try:
                    data = doc.xref_stream(xref)
                except Exception:
                    continue
                cleaned, count = strip_watermark_marked_content(data)
                if count:
                    doc.update_stream(xref, cleaned)
                    removed_blocks += count

        # garbage=4 removes now-unreferenced watermark Form/Image objects.
        doc.save(output_path, garbage=4, deflate=True, clean=True)
    finally:
        doc.close()

    return CleanResult(
        input_path=input_path,
        output_path=output_path,
        pages=_count_pages(output_path),
        removed_blocks=removed_blocks,
        watermark_annotations_removed=removed_annots,
    )
