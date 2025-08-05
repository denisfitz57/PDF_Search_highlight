import os
import pymupdf  # PyMuPDF
from pypdf import PdfWriter, PdfReader
import pandas as pd
import shutil
import time
import uuid

def merge_highlighted_pdfs(csv_file, base_path, output_path="highlighted_merged_output.pdf"):
    """
    Merge PDFs with highlighted text based on search results.
    
    Parameters:
    csv_file (str): Path to CSV file with search results
    base_path (str): Base directory containing PDFs
    output_path (str): Path for output merged PDF
    
    Returns:
    tuple: (success_count, failed_pdfs, temp_directory)
    """
    # Create a temporary directory with a unique name
    temp_dir = f"temp_highlight_pdfs_{uuid.uuid4().hex[:8]}"
    os.makedirs(temp_dir, exist_ok=True)
    print(f"Created temporary directory: {temp_dir}")
    
    # Read the data
    df = pd.read_csv(csv_file)
    df_original = df.copy()
    
    # Filter and sort data
    columns_to_keep = ['filename', 'date', 'page_number']
    df = df[columns_to_keep]
    df = df.drop_duplicates()
    df = df.sort_values(by=['date', 'page_number'])
    
    # Save deduplicated results
    deduped_csv = "regex_search_results_deduped.csv"
    df.to_csv(deduped_csv, index=False)
    print(f"Saved deduplicated results to {deduped_csv}")
    
    # Get unique filenames sorted by date and page number
    pdf_files = df['filename'].unique()
    print(f"Found {len(pdf_files)} PDF files to process and merge")
    
    # For the final merged PDF
    merger = PdfWriter()
    
    # Track successful and failed operations
    successful = 0
    failed = []
    
    # Process each PDF file
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"Processing {i}/{len(pdf_files)}: {pdf_file}")
        
        try:
            full_path = os.path.join(base_path, pdf_file)
            
            if not os.path.exists(full_path):
                print(f"  File not found: {full_path}")
                failed.append(pdf_file)
                continue
                
            # Find all matching rows for this PDF in the original dataframe
            matches = df_original[df_original['filename'] == pdf_file]
            
            # Sanitize filename for temp file
            safe_name = pdf_file.replace(" ", "_").replace("/", "_").replace("\\", "_")
            temp_pdf_path = os.path.join(temp_dir, f"temp_{safe_name}")
            
            if matches.empty:
                print(f"  No highlight data found for {pdf_file}, adding without highlights")
                # For files without highlights, we'll still copy to our temp directory for consistency
                shutil.copy2(full_path, temp_pdf_path)
            else:
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
                        try:
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
                        except Exception as e:
                            print(f"  Error highlighting: {str(e)}")
                
                # Save the highlighted PDF to our temp directory
                doc.save(temp_pdf_path)
                doc.close()
                
                if highlights_added:
                    print(f"  Added {pdf_file} with highlights")
                else:
                    print(f"  Added {pdf_file} (no highlights were applied)")
            
            # Add the file to the merger
            merger.append(temp_pdf_path)
            successful += 1
                
        except Exception as e:
            print(f"  Error processing {pdf_file}: {str(e)}")
            failed.append(pdf_file)
    
    # Write the merged PDF to a file
    if successful > 0:
        try:
            merger.write(output_path)
            merger.close()
            print(f"\nSuccessfully merged {successful} PDFs into {output_path}")
        except Exception as e:
            print(f"Error writing merged PDF: {str(e)}")
    else:
        print("No PDFs were successfully merged")
    
    # Report any failed files
    if failed:
        print(f"\nFailed to process {len(failed)} files:")
        for fail in failed:
            print(f"- {fail}")
    
    # Return information for later cleanup
    return successful, failed, temp_dir

def cleanup_temp_directory(temp_dir):
    """
    Clean up the temporary directory.
    
    Parameters:
    temp_dir (str): Path to temporary directory
    
    Returns:
    bool: True if cleanup was successful
    """
    print(f"Cleaning up temporary directory: {temp_dir}")
    
    if not os.path.exists(temp_dir):
        print("Directory doesn't exist.")
        return True
    
    try:
        shutil.rmtree(temp_dir)
        print(f"Successfully removed temporary directory: {temp_dir}")
        return True
    except Exception as e:
        print(f"Error cleaning up directory: {str(e)}")
        print("You may need to manually delete this directory.")
        return False

# Main execution
if __name__ == "__main__":
    # Read the data
    csv_file = 'regex_search_results.csv'
    base_path = r"C:\Users\denis\Documents\WWRDownloading\PDFs\\"
    output_path = "highlighted_merged_output.pdf"
    
    print("Starting PDF processing and merging...")
    successful, failed, temp_dir = merge_highlighted_pdfs(csv_file, base_path, output_path)
    
    # Ask user if they want to clean up now
    if os.path.exists(temp_dir):
        print("\nTemporary files are stored in:", temp_dir)
        user_input = input("Do you want to clean up temporary files now? (y/n): ")
        
        if user_input.lower() in ['y', 'yes']:
            cleanup_temp_dir = cleanup_temp_directory(temp_dir)
            if not cleanup_temp_dir:
                print(f"To clean up later, run: cleanup_temp_directory('{temp_dir}')")
        else:
            print("Temporary files were kept.")
            print(f"To clean up later, run: cleanup_temp_directory('{temp_dir}')")
    
    print("Process complete.")