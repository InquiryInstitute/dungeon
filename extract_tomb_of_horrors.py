#!/usr/bin/env python3
"""
Extract text and map images from Tomb of Horrors PDF and encode as JSON.
Use --ocr to re-OCR each page with Tesseract for improved text (requires tesseract installed).
"""
import argparse
import fitz  # PyMuPDF
import json
import base64
import io
from pathlib import Path

try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

PDF_PATH = Path(__file__).parent / "tsr09022b - S1 - Tomb of Horrors (green cover).pdf"
OUTPUT_JSON = Path(__file__).parent / "tomb_of_horrors.json"
MAPS_DIR = Path(__file__).parent / "tomb_of_horrors_maps"

# DPI for page render when using OCR (higher = better quality, slower)
OCR_DPI = 300

# Tesseract: PSM 6 = uniform block of text, OEM 3 = LSTM only (better accuracy)
TESSERACT_CONFIG = "--psm 6 --oem 3"


def preprocess_for_ocr(img: "Image.Image") -> "Image.Image":
    """Grayscale, sharpen, and enhance contrast to improve Tesseract accuracy."""
    img = img.convert("L")  # grayscale
    img = ImageEnhance.Contrast(img).enhance(1.3)
    img = ImageEnhance.Sharpness(img).enhance(1.2)
    return img


def postprocess_ocr_text(text: str) -> str:
    """Fix common OCR errors in extracted text."""
    import re
    # Run-together words (split)
    fixes = [
        (r"\bthetop\b", "the top"),
        (r"\bthetopofthehill\b", "the top of the hill"),
        (r"\borso\b", "or so"),
        (r"\bfromo\b", "from a"),
        (r"\bitwill\b", "it will"),
        (r"\bbeseen\b", "be seen"),
        (r"\bthatthewhole\b", "that the whole"),
        (r"\bthemiddleofthewhole\b", "the middle of the whole"),
        (r"\buglyweeds\b", "ugly weeds"),
        (r"\bsond\b", "sand"),
        (r"\beost\b", "east"),
        (r"\bentronce\b", "entrance"),
        (r"\bentronces\b", "entrances"),
        (r"\bond\b", "and"),
        (r"\bmoun\b", "mound"),
        (r"\bcon\s+be\b", "can be"),
        (r"\bon\s+entrance\b", "an entrance"),
        (r"\bo\s+passage\b", "a passage"),
        # Common digit/letter confusions: IO' -> 10', l0 -> 10, 6 0 -> 60
        (r"\bIO'", "10'"),
        (r"\bl0\b", "10"),
        (r"(\d)\s+0\s+high", r"\g<1>0 high"),  # "6 0 high" -> "60 high"
    ]
    for pattern, repl in fixes:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    return text


def ocr_page(page) -> str:
    """Render a single page to an image and run Tesseract OCR."""
    if not OCR_AVAILABLE:
        raise RuntimeError("Install pytesseract and Pillow for OCR (pip install pytesseract Pillow)")
    # Render at OCR_DPI for readable text
    mat = fitz.Matrix(OCR_DPI / 72, OCR_DPI / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    png_bytes = pix.tobytes("png")
    img = Image.open(io.BytesIO(png_bytes))
    img = preprocess_for_ocr(img)
    text = pytesseract.image_to_string(img, lang="eng", config=TESSERACT_CONFIG)
    return postprocess_ocr_text(text).strip()


def extract_pdf(use_ocr: bool = False):
    doc = fitz.open(PDF_PATH)
    pages_text = []
    maps = []  # list of {page, name, base64_data, width, height}

    for page_num in range(len(doc)):
        page = doc[page_num]
        # Extract text (embedded or OCR)
        if use_ocr:
            try:
                text = ocr_page(page)
            except Exception as e:
                text = page.get_text().strip()
                print(f"  Page {page_num + 1}: OCR failed ({e}), using embedded text")
        else:
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
    parser = argparse.ArgumentParser(description="Extract Tomb of Horrors PDF to JSON")
    parser.add_argument(
        "--ocr",
        action="store_true",
        help="Re-OCR each page with Tesseract for improved text (requires tesseract installed)",
    )
    args = parser.parse_args()
    if not PDF_PATH.exists():
        raise SystemExit(f"PDF not found: {PDF_PATH}")
    if args.ocr:
        if not OCR_AVAILABLE:
            raise SystemExit("OCR requires: pip install pytesseract Pillow and system tesseract (e.g. brew install tesseract)")
        print("Re-OCRing pages with Tesseract (this may take a few minutes)...")
    data = extract_pdf(use_ocr=args.ocr)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Wrote {OUTPUT_JSON} ({len(data['pages'])} pages, {len(data['maps'])} images)")


if __name__ == "__main__":
    main()
