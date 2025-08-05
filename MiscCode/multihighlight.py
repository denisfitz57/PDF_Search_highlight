import pandas as pd
import pymupdf  # PyMuPDF
import os
import sys
from pypdf import PdfWriter

def highlight_search_results(search_results_csv, output_pdf_path, base_folder):
    """
    Takes search results from a CSV file and creates a PDF with highlighted search terms.
    
    Parameters:
    search_results_csv (str): Path to CSV file with search results
    output_pdf_path (str): Path where to save the output PDF
    base_folder (str): Base folder where PDF files are stored
    """
    # Read search results
    df = pd.read_csv(search_results_csv)
    
    # Sort by date and page number for a logical order
    df = df.sort_values(by=['date', 'page_number'])
    
    # Create a PDF writer for the output file
    pdf_writer = PdfWriter()
    
    # Keep track of processed files to avoid duplicates
    processed_files = set()
    
    # Process each row in the search results
    for index, row in df.iterrows():
        pdf_path = os.path.join(base_folder, row['filename'])
        
        # Check if the file exists
        if not os.path.exists(pdf_path):
            print(f"Warning: File not found: {pdf_path}")
            continue
        
        # Create a unique identifier for this page
        file_id = (pdf_path, 0)  # Assuming single-page PDFs; page number is always 0
        
        # Skip if we've already processed this page
        if file_id in processed_files:
            continue
        
        try:
            # Open the PDF and highlight the text
            doc = pymupdf.open(pdf_path)
            page = doc[0]  # Single-page PDFs
            
            # Create a rectangle from the bounding box coordinates
            rect = pymupdf.Rect(row['bbx0'], row['bby0'], row['bbx1'], row['bby1'])
            
            # Add highlight annotation
            highlight = page.add_highlight_annot(rect)
            
            # Create a temporary highlighted PDF
            temp_path = f"_tmp_{index}.pdf"
            doc.save(temp_path, incremental=False)
            doc.close()
            
            # Add the temporary PDF to our output PDF
            pdf_writer.append(temp_path)
            
            # Mark this page as processed
            processed_files.add(file_id)
            
            print(f"Highlighted text in {row['filename']} at position {rect}")
            
        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")
    
    # Save the final PDF
    pdf_writer.write(output_pdf_path)
    
    # Clean up temporary files
    for index in range(len(df)):
        temp_path = f"_tmp_{index}.pdf"
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    print(f"Created PDF with {len(processed_files)} highlighted pages at: {output_pdf_path}")
    
    # Open the result
    # if sys.platform.startswith("darwin"):
    #     os.system(f"open '{output_pdf_path}'")
    # elif os.name == "nt":
    #     os.startfile(output_pdf_path)
    # else:
    #     os.system(f"xdg-open '{output_pdf_path}'")

if __name__ == "__main__":
    # Example usage
    search_results_csv = "search_results_Fitzpatrick.csv"
    output_pdf = "highlighted_search_results.pdf"
    base_folder = r"C:\Users\denis\Documents\searchWWR\WWR1968"
    
    highlight_search_results(search_results_csv, output_pdf, base_folder)