import os
import re
import pymupdf 
import pandas as pd
import traceback
from datetime import datetime

# Create error log file
log_filename = f"pdf_processing_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
error_log_path = os.path.join(os.path.dirname(__file__), log_filename)

def log_error(filename, error_message):
    """Write error to log file"""
    with open(error_log_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error processing: {filename}\n")
        log_file.write(f"Error details: {error_message}\n")
        log_file.write("-" * 80 + "\n")

folder_path = r"C:\Users\denis\Documents\WWRDownloading\PDFs"
# Prepare list to store rows
rows = []

# Pattern to extract metadata from filename
filename_pattern = re.compile(r"^(.*), Page(\d+), (\d{4}-\d{2}-\d{2})\.pdf$")

# Stats for reporting
total_files = 0
processed_files = 0
error_files = 0

# Walk through all PDF files in the folder
pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]
total_files = len(pdf_files)

for filename in pdf_files:
    try:
        match = filename_pattern.match(filename)
        if not match:
            print(f"Filename pattern not matched: {filename}")
            log_error(filename, "Filename pattern not matched")
            error_files += 1
            continue
            
        newspaper_name, page_number, date_str = match.groups()
        passcount = 0
        file_path = os.path.join(folder_path, filename)
        
        try:
            doc = pymupdf.open(file_path)
        except Exception as e:
            error_message = f"Failed to open PDF: {str(e)}\n{traceback.format_exc()}"
            print(f"Error opening {filename}: {str(e)}")
            log_error(filename, error_message)
            error_files += 1
            continue
            
        try:
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
            processed_files += 1
            print(f"Processed {filename} ({processed_files}/{total_files})")
            
        except Exception as e:
            error_message = f"Error processing PDF content: {str(e)}\n{traceback.format_exc()}"
            print(f"Error processing content in {filename}: {str(e)}")
            log_error(filename, error_message)
            error_files += 1
            try:
                doc.close()
            except:
                pass
            
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
        print(f"Unexpected error with {filename}: {str(e)}")
        log_error(filename, error_message)
        error_files += 1

# Create DataFrame
if rows:
    df = pd.DataFrame(rows)
    
    # Preview unsorted first few rows
    print("Preview of unsorted data:")
    print(df.head())
    
    # Convert date to datetime for proper sorting
    df['date'] = pd.to_datetime(df['date'])
    
    # Sort by date (oldest to newest) and page_number (smallest to largest)
    df = df.sort_values(by=[ 'page_number','date'], ascending=[True, True])
    
    # Preview sorted data
    print("\nPreview of sorted data:")
    print(df.head())
    
    # Save to CSV - convert back to string format for date
    df['date'] = df['date'].dt.strftime('%Y-%m-%d')
    df.to_csv("big_text_with_position_June4.csv", index=False, float_format="%.4f")
    
    print(f"\nProcessing complete:")
    print(f"Total files: {total_files}")
    print(f"Successfully processed: {processed_files}")
    print(f"Files with errors: {error_files}")
    print(f"Error log saved to: {error_log_path}")
else:
    print("No data was processed successfully. Check the error log.")