import os
import re
import pymupdf 
import pandas as pd



folder_path =r"C:\Users\denis\Documents\WWRDownloading\PDFs"
# Prepare list to store rows
rows = []

# Pattern to extract metadata from filename
filename_pattern = re.compile(r"^(.*), Page(\d+), (\d{4}-\d{2}-\d{2})\.pdf$")

# Walk through all PDF files in the folder
for filename in os.listdir(folder_path):
    if filename.lower().endswith(".pdf"):
        match = filename_pattern.match(filename)
        if not match:
            print(f"Filename pattern not matched: {filename}")
            continue
        passcount = 0
        newspaper_name, page_number, date_str = match.groups()

        file_path = os.path.join(folder_path, filename)
        doc = pymupdf.open(file_path)
        # if page_number == 17:
        #     print("Break point")
        for page_number_in_doc, page in enumerate(doc, start=1):
            blocks = page.get_text("dict", flags=11)["blocks"]
            # If blocks is empty, add a default row for the empty page
            if not blocks:
                passcount += 1
                empty_page_row = {
                    "filename": filename,
                    "page_number": int(page_number),
                    "date": date_str,
                    "text": "[EMPTY PAGE]",
                    "size": 0,
                    "bbx0": 0,
                    "bby0": 0, 
                    "bbx1": 0,
                    "bby1": 0,
                    "page_number_in_pdf": page_number_in_doc
                }
                rows.append(empty_page_row)
                print(f"Empty page detected in {filename}, page {page_number_in_doc}")
                
            # Continue with existing code for non-empty pages

            for b in blocks:
                for l in b.get("lines", []):
                    for s in l.get("spans", []):
                        passcount += 1
                        # Hierarchy classification (tune thresholds as needed)
                        font_size = s["size"]
                        bbox_width = s["bbox"][2] - s["bbox"][0]

                        text_clean = s["text"].lower().strip()
                        # Add to row
                        row = {
                            "filename": filename,
                            "page_number": int(page_number),
                            "date": date_str,
                            "text": s["text"],
                            "size": font_size,
                            "bbx0": s["bbox"][0],
                            "bby0": s["bbox"][1],
                            "bbx1": s["bbox"][2],
                            "bby1": s["bbox"][3],
                            "page_number_in_pdf": page_number_in_doc
                        }
                        rows.append(row)
        doc.close()
        print(f"Processed {filename}")

                    


# Create DataFrame
df = pd.DataFrame(rows)

# Sort by multiple columns
# df = df.sort_values(by=['date','page_number', 'passcount'],ascending=[True, True, True])

# Preview first few rows
print(df.head())



df.to_csv("big_text_with_position.csv", index=False, float_format="%.4f")

