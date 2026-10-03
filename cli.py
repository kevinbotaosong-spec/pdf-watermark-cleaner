from __future__ import annotations
import argparse
from core.watermark import clean_pdf


def main():
    ap = argparse.ArgumentParser(description="Remove standard PDF Watermark artifacts locally.")
    ap.add_argument("pdf", nargs="+", help="PDF file(s) to clean")
    args = ap.parse_args()
    for p in args.pdf:
        r = clean_pdf(p)
        print(f"{r.input_path.name} -> {r.output_path} (removed {r.removed_blocks + r.watermark_annotations_removed})")

if __name__ == "__main__":
    main()
