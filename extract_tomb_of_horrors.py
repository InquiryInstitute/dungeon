#!/usr/bin/env python3
"""
Extract text and map images from Tomb of Horrors PDF and encode as JSON.
"""
import fitz  # PyMuPDF
import json
import base64
import os
from pathlib import Path

PDF_PATH = Path(__file__).parent / "tsr09022b - S1 - Tomb of Horrors (green cover).pdf"
OUTPUT_JSON = Path(__file__).parent / "tomb_of_horrors.json"
MAPS_DIR = Path(__file__).parent / "tomb_of_horrors_maps"


def extract_pdf():
    doc = fitz.open(PDF_PATH)
    pages_text = []
    maps = []  # list of {page, name, base64_data, width, height}

    for page_num in range(len(doc)):
        page = doc[page_num]
        # Extract text
        text = page.get_text()
        pages_text.append({
            "page": page_num + 1,
            "text": text.strip(),
        })

        # Extract images from this page
        image_list = page.get_images(full=True)
        for img_index, img_info in enumerate(image_list):
            xref = img_info[0]
            base_image = doc.extract_image(xref)
            img_bytes = base_image["image"]
            ext = base_image["ext"]
            width = base_image["width"]
            height = base_image["height"]

            # Consider larger images as likely maps (e.g. > 200px on a side)
            is_likely_map = width >= 200 or height >= 200
            name = f"page{page_num + 1}_img{img_index}"
            b64 = base64.standard_b64encode(img_bytes).decode("ascii")

            maps.append({
                "page": page_num + 1,
                "name": name,
                "width": width,
                "height": height,
                "format": ext,
                "base64": b64,
                "likely_map": is_likely_map,
            })

    doc.close()

    result = {
        "source": PDF_PATH.name,
        "pages": pages_text,
        "maps": maps,
    }
    return result


def main():
    if not PDF_PATH.exists():
        raise SystemExit(f"PDF not found: {PDF_PATH}")
    data = extract_pdf()
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Wrote {OUTPUT_JSON} ({len(data['pages'])} pages, {len(data['maps'])} images)")


if __name__ == "__main__":
    main()
