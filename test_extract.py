from __future__ import annotations

import sys
import pandas as pd

from extractor import DOC_TYPE_HIGH, DOC_TYPE_LOW, headers_for_doc_type, parse_pdf


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python test_extract.py <ofn|po> <path-to-pdf>")
        raise SystemExit(2)
    doc_type = DOC_TYPE_HIGH if sys.argv[1].lower() == "ofn" else DOC_TYPE_LOW
    with open(sys.argv[2], "rb") as fh:
        rows = parse_pdf(fh.read(), doc_type)
    df = pd.DataFrame(rows, columns=headers_for_doc_type(doc_type))
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
