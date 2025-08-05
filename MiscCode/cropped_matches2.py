import os
import pandas as pd
import fitz  # PyMuPDF

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIGURATION (edit these)
# 1) PATH_TO_CSV:    path to your OCR‐output CSV
# 2) PDF_FOLDER:     folder containing all single‐page PDFs
# 3) OUTPUT_FOLDER:  where cropped images will be saved
# 4) SEARCH_TERM:    what string to search in the 'text' column
# 5) PADDING:        extra margin (in PDF points) around each bbox
# 6) MIN_WIDTH:      minimum width (in PDF points) of every crop
# 7) MIN_HEIGHT:     minimum height (in PDF points) of every crop
#
# Make sure OUTPUT_FOLDER exists (or let script create it).
# ─────────────────────────────────────────────────────────────────────────────
PATH_TO_CSV   = r"C:\path\to\ocr_output.csv"
PDF_FOLDER    = r"C:\path\to\pdf_folder"
OUTPUT_FOLDER = r"C:\path\to\output_crops"
SEARCH_TERM   = "Lincoln"   # <-- replace with your term
PADDING       = 5           # in PDF points (≈1/72 inch)
MIN_WIDTH     = 50          # minimum crop width (points)
MIN_HEIGHT    = 20          # minimum crop height (points)
# ─────────────────────────────────────────────────────────────────────────────


def ensure_dir(path):
    """Create directory if it doesn't exist."""
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)


def increment_key(counter_dict, key):
    """Increment a counter in a dict and return its new value."""
    counter_dict[key] = counter_dict.get(key, 0) + 1
    return counter_dict[key]


def expand_rect_to_minimum(rect, min_w, min_h, page_width, page_height):
    """
    Given a fitz.Rect 'rect', ensure it has at least width=min_w and height=min_h.
    If smaller, expand as evenly as possible around center, but clamp to [0,page_width] x [0,page_height].
    Returns a new fitz.Rect.
    """
    x0, y0, x1, y1 = rect.x0, rect.y0, rect.x1, rect.y1
    curr_w = x1 - x0
    curr_h = y1 - y0

    # If width is too small, expand equally on left/right
    if curr_w < min_w:
        extra = (min_w - curr_w) / 2.0
        x0 -= extra
        x1 += extra

    # If height is too small, expand equally on top/bottom
    if curr_h < min_h:
        extra = (min_h - curr_h) / 2.0
        y0 -= extra
        y1 += extra

    # Now clamp to page boundaries, adjusting the opposite side if one side is clamped
    # Clamp left edge
    if x0 < 0:
        shift = -x0
        x0 = 0
        x1 = min(x1 + shift, page_width)  # push right if space remains
    # Clamp right edge
    if x1 > page_width:
        shift = x1 - page_width
        x1 = page_width
        x0 = max(x0 - shift, 0)

    # Clamp top edge
    if y0 < 0:
        shift = -y0
        y0 = 0
        y1 = min(y1 + shift, page_height)
    # Clamp bottom edge
    if y1 > page_height:
        shift = y1 - page_height
        y1 = page_height
        y0 = max(y0 - shift, 0)

    return fitz.Rect(x0, y0, x1, y1)


def main():
    # 1) Load CSV
    df = pd.read_csv(
        PATH_TO_CSV,
        dtype={
            "filename": str,
            "page_number": str,
            "date": str,
            "text": str,
            "bbx0": float,
            "bby0": float,
            "bbx1": float,
            "bby1": float
        }
    )

    # 2) Filter rows where 'text' contains SEARCH_TERM (case‐insensitive)
    mask = df["text"].str.contains(SEARCH_TERM, case=False, na=False)
    matches = df[mask].copy()
    if matches.empty:
        print(f"No occurrences of '{SEARCH_TERM}' found in the CSV.")
        return

    # 3) Counter for (date, page_number) to handle multiple hits per page
    counter = {}

    ensure_dir(OUTPUT_FOLDER)

    for idx, row in matches.iterrows():
        pdf_name   = row["filename"]
        page_num   = str(row["page_number"])
        the_date   = row["date"]
        bbx0       = float(row["bbx0"])
        bby0       = float(row["bby0"])
        bbx1       = float(row["bbx1"])
        bby1       = float(row["bby1"])

        # 3.a) Build key and increment
        key = (the_date, page_num)
        count = increment_key(counter, key)

        # 3.b) Open the single‐page PDF
        pdf_path = os.path.join(PDF_FOLDER, pdf_name)
        if not os.path.isfile(pdf_path):
            print(f"Warning: PDF not found: {pdf_path} (skipping)")
            continue

        doc = fitz.open(pdf_path)
        page = doc.load_page(0)

        # 3.c) Compute padded rectangle
        x0 = bbx0 - PADDING
        y0 = bby0 - PADDING
        x1 = bbx1 + PADDING
        y1 = bby1 + PADDING

        # Clamp initial padded rect to page dimensions
        x0 = max(x0, 0)
        y0 = max(y0, 0)
        x1 = min(x1, page.rect.width)
        y1 = min(y1, page.rect.height)
        padded_rect = fitz.Rect(x0, y0, x1, y1)

        # 3.d) Expand to minimum size if needed
        final_rect = expand_rect_to_minimum(
            padded_rect,
            min_w=MIN_WIDTH,
            min_h=MIN_HEIGHT,
            page_width=page.rect.width,
            page_height=page.rect.height
        )

        # 3.e) Render that rectangle to an image
        pix = page.get_pixmap(clip=final_rect)

        # 3.f) Build output filename
        safe_term = SEARCH_TERM.replace(" ", "_")
        out_name = f"{safe_term}_{the_date}_p{page_num}_{count:02d}.png"
        out_path = os.path.join(OUTPUT_FOLDER, out_name)

        # 3.g) Save the cropped image
        pix.save(out_path)
        print(f"Saved crop: {out_path}")

        doc.close()

    print("Done. All matching regions have been cropped and saved.")


if __name__ == "__main__":
    main()
