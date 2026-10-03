from pathlib import Path
import fitz
from core.watermark import clean_pdf


def test_clean_sample():
    sample = Path(__file__).resolve().parent / "sample.pdf"
    if not sample.exists():
        return
    result = clean_pdf(sample)
    assert result.removed_blocks >= 1
    doc = fitz.open(result.output_path)
    for page in doc:
        for xref in page.get_contents() or []:
            data = doc.xref_stream(xref)
            assert b"/Subtype /Watermark" not in data
