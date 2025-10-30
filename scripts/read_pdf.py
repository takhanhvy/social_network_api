"""Utility to dump text content from a PDF file to stdout."""

from pathlib import Path

from PyPDF2 import PdfReader


def dump_pdf(path: Path) -> None:
    reader = PdfReader(path.open("rb"))
    print(f"pages {len(reader.pages)}")
    for index, page in enumerate(reader.pages, 1):
        print(f"--- page {index} ---")
        text = page.extract_text()
        if not text:
            print("[no text extracted]")
            continue
        # Replace frequent newlines to make the output easier to read.
        normalized = " ".join(text.split())
        print(normalized)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/read_pdf.py <pdf_path>")
    dump_pdf(Path(sys.argv[1]))
