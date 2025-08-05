import os
import pandas as pd
import fitz  # PyMuPDF

# ─────────────────────────────────────────────────────────────────────────────
# ───  CONFIGURE THESE THREE VARIABLES  ────────────────────────────────────────
#
# 1) PATH_TO_CSV:         where your CSV file lives (OCR output)
# 2) PDF_FOLDER:          folder containing all the single‐page PDFs
# 3) OUTPUT_FOLDER:       folder where cropped images will be saved
#
# 4) SEARCH_TERM:         the string you want to look for (case‐insensitive by default)
# 5) PADDING:             how many PDF‐points of margin to add around each bbox (e.g. 5 or 10)
#
# Make sure OUTPUT_FOLDER exists before running.
# ─────────────────────────────────────────────────────────────────────────────
PATH_TO_CSV   = r'big_text_with_position_june2.csv'
PDF_FOLDER    = r"C:\Users\denis\Documents\WWRDownloading\PDFs"
OUTPUT_FOLDER = r"C:\Users\denis\Documents\Highlighter\Fitzpatrick\cropped_images\Fitzpatrick"
SEARCH_TERM   = "Fitzpatrick"    # <-- replace with whatever you’re searching for
PADDINGX       = 10            # in PDF points (≈ 1/14 inch). Adjust as needed.
PADDINGY       = 50            # in PDF points (≈ 1/14 inch). Adjust as needed.
# ─────────────────────────────────────────────────────────────────────────────


def ensure_dir(path):
    """Create the directory if it doesn’t exist."""
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)


def increment_key(counter_dict, key):
    """Increment a counter in a dict and return the new value."""
    counter_dict[key] = counter_dict.get(key, 0) + 1
    return counter_dict[key]


def main():
    # 1) Read the CSV into a DataFrame
    df = pd.read_csv(PATH_TO_CSV, dtype={
        "filename": str,
        "page_number": str,
        "date": str,
        "text": str,
        "bbx0": float,
        "bby0": float,
        "bbx1": float,
        "bby1": float
    })

    # 2) Filter rows where 'text' contains the SEARCH_TERM (case‐insensitive)
    mask = df["text"].str.contains(SEARCH_TERM, case=False, na=False)
    matches = df[mask].copy()
    if matches.empty:
        print(f"No occurrences of '{SEARCH_TERM}' found in the CSV.")
        return

    # 3) Prepare to count how many hits per (date, page_number)
    counter = {}  # keys = (date, page_number), value = int

    ensure_dir(OUTPUT_FOLDER)

    for idx, row in matches.iterrows():
        pdf_name    = row["filename"]
        page_num    = str(row["page_number"])
        the_date    = row["date"]
        bbx0, bby0  = float(row["bbx0"]), float(row["bby0"])
        bbx1, bby1  = float(row["bbx1"]), float(row["bby1"])
        
        # 3.a) Build a unique key for counting
        key = (the_date, page_num)
        count = increment_key(counter, key)

        # 3.b) Open the single‐page PDF
        pdf_path = os.path.join(PDF_FOLDER, pdf_name)
        if not os.path.isfile(pdf_path):
            print(f"Warning: PDF not found: {pdf_path} (skipping)")
            continue

        doc = fitz.open(pdf_path)
        # Since these are single‐page PDFs, page index is 0
        page = doc.load_page(0)

        # 3.c) Compute a rectangle with padding, clamped to page bounds
        #     fitz.Rect takes (x0, y0, x1, y1). Origin = top‐left; y grows downward.
        x0 = max(bbx0 - PADDINGX, 0)
        y0 = max(bby0 - PADDINGY, 0)
        x1 = min(bbx1 + PADDINGX, page.rect.width)
        y1 = min(bby1 + PADDINGY, page.rect.height)
        clip_rect = fitz.Rect(x0, y0, x1, y1)

        # 3.d) Render that rectangle to a pixmap (image)
        pix = page.get_pixmap(clip=clip_rect)

        # 3.e) Build an output filename:
        #      {search}_{date}_{page}_{n}.png
        safe_term = SEARCH_TERM.replace(" ", "_")
        out_name = f"{safe_term}_{the_date}_p{page_num}_{count:02d}.png"
        out_path = os.path.join(OUTPUT_FOLDER, out_name)

        # 3.f) Save the cropped image
        pix.save(out_path)
        print(f"Saved crop: {out_path}")

        doc.close()

    print("Done. All matching regions have been cropped and saved.")


if __name__ == "__main__":
    main()
