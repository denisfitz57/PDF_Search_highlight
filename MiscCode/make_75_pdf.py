import os
import pymupdf  # PyMuPDF
from pypdf import PdfWriter, PdfReader
import pandas as pd
import tempfile
import time
import platform
import atexit

# At the top of your script
def cleanup_on_exit():
    # Only try to clean up on Windows - this helps avoid permission errors
    if platform.system() != 'Windows':
        return
        
    # Wait a moment for resources to be released
    time.sleep(3)
    
    for temp_file in temp_files:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except:
            pass
            
# Register the cleanup function
atexit.register(cleanup_on_exit)

# Read the data
df = pd.read_csv('regex_search_results.csv')
df_original = df.copy()
columns_to_keep = ['filename', 'date', 'page_number']
df = df[columns_to_keep]
df = df.drop_duplicates()
df = df.sort_values(by=['date', 'page_number'])
df.to_csv('regex_search_results_deduped.csv', index=False)

# Path where your PDF files are stored
base_path = r"C:\Users\denis\Documents\WWRDownloading\PDFs\\"

# Get unique filenames sorted by date and page number
pdf_files = df['filename'].unique()
print(f"Found {len(pdf_files)} PDF files to process and merge")

# For the final merged PDF
merger = PdfWriter()

# Track successful and failed operations
successful = 0
failed = []
temp_files = []  # Keep track of temp files to clean up later

# Process each PDF file
for pdf_file in pdf_files:
    print(f"Processing: {pdf_file}")
    
    try:
        full_path = os.path.join(base_path, pdf_file)
        
        if not os.path.exists(full_path):
            print(f"File not found: {full_path}")
            failed.append(pdf_file)
            continue
            
        # Find all matching rows for this PDF in the original dataframe
        matches = df_original[df_original['filename'] == pdf_file]
        
        if matches.empty:
            print(f"No highlight data found for {pdf_file}, adding without highlights")
            merger.append(full_path)
            successful += 1
            continue
            
        # Open the PDF with PyMuPDF for highlighting
        doc = pymupdf.open(full_path)
        
        # Since each PDF is a single page, we just work with page 0
        page = doc[0]
        
        # Track if we made any changes
        highlights_added = False
        
        # Process each match for this file
        for _, row in matches.iterrows():
            # Check if the necessary columns exist for highlighting
            if all(col in row.index for col in ['bbx0', 'bby0', 'bbx1', 'bby1']):
                # Extract bounding box coordinates
                rect = pymupdf.Rect(
                    float(row['bbx0']), 
                    float(row['bby0']), 
                    float(row['bbx1']), 
                    float(row['bby1'])
                )
                
                # Add highlight annotation
                highlight = page.add_highlight_annot(rect)
                highlight.set_colors({"stroke": (1, 1, 0)})  # Yellow highlight
                highlight.update()
                highlights_added = True
        
        # Create a temporary file for the highlighted PDF
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_files.append(temp_file.name)
        doc.save(temp_file.name)
        doc.close()
        temp_file.close()
        
        # Add the highlighted PDF to the merger
        merger.append(temp_file.name)
        successful += 1
        
        if highlights_added:
            print(f"Added {pdf_file} with highlights")
        else:
            print(f"Added {pdf_file} (no highlights were applied)")
            
    except Exception as e:
        print(f"Error processing {pdf_file}: {str(e)}")
        failed.append(pdf_file)

# Write the merged PDF to a file
if successful > 0:
    output_path = "highlighted_merged_output.pdf"
    merger.write(output_path)
    merger.close()
    print(f"\nSuccessfully merged {successful} PDFs into {output_path}")
else:
    print("No PDFs were successfully merged")

# Report any failed files
if failed:
    print(f"\nFailed to process {len(failed)} files:")
    for fail in failed:
        print(f"- {fail}")

# Clean up temporary files
if platform.system() == 'Windows':
    print("Note: Temporary files will be cleaned up when the program exits")
else:
    # Clean up temporary files immediately on non-Windows platforms
    for temp_file in temp_files:
        try:
            os.unlink(temp_file)
        except Exception as e:
            print(f"Could not clean up {temp_file}: {e}")