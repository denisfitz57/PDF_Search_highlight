import pandas as pd
import pymupdf  # PyMuPDF
import os
import sys
from pypdf import PdfWriter
import argparse
import glob
from rapidfuzz import fuzz, process  # pip install rapidfuzz

def search_and_highlight(search_term, base_folder, output_directory='.', similarity_threshold=80):
    """
    Searches for a term in CSV files with text positions and creates a highlighted PDF.
    
    Parameters:
    search_term (str): Term to search for
    base_folder (str): Base folder where PDF files are stored
    output_directory (str): Directory where to save output files
    similarity_threshold (int): Minimum similarity score (0-100) to consider a match
    """
    # Step 1: Get text position data
    try:
        df = pd.read_csv('big_text_with_position.csv')
    except FileNotFoundError:
        print("Error: big_text_with_position.csv not found")
        return
    
    # Step 2: Perform fuzzy search
    print(f"Searching for '{search_term}' with similarity threshold {similarity_threshold}%...")
    
    # Apply fuzzy matching to each text entry
    # First try exact substring search for efficiency
    exact_matches = df[df['text'].str.contains(search_term, case=False, na=False)]
    
    # Add similarity score of 100 for exact matches
    exact_matches['similarity'] = 100
    
    # For remaining entries, use fuzzy matching
    remaining_df = df.drop(exact_matches.index)
    
    # Apply fuzzy matching - this is computationally expensive for large datasets
    fuzzy_matches_chunks = []
    
    # Create chunks for processing to avoid memory issues
    chunk_size = 10000  # Adjust based on your system's memory
    total_chunks = (len(remaining_df) + chunk_size - 1) // chunk_size
    
    for i in range(0, len(remaining_df), chunk_size):
        chunk = remaining_df.iloc[i:i+chunk_size]
        
        # Calculate similarity scores for this chunk
        chunk['similarity'] = chunk['text'].apply(
            lambda x: fuzz.partial_ratio(search_term.lower(), str(x).lower())
        )
        chunk['text'].apply(lambda x: print(x))



        # Find matches above threshold
        chunk_matches = chunk[chunk['similarity'] >= similarity_threshold]
        fuzzy_matches_chunks.append(chunk_matches)
        
        print(f"Processed chunk {i//chunk_size + 1}/{total_chunks}...")
    
    # Combine all fuzzy matches from chunks
    fuzzy_matches = pd.concat(fuzzy_matches_chunks) if fuzzy_matches_chunks else pd.DataFrame()
    
    # Combine exact and fuzzy matches
    search_results = pd.concat([exact_matches, fuzzy_matches])
    
    if len(search_results) == 0:
        print(f"No results found for '{search_term}'")
        return
    
    print(f"Found {len(search_results)} occurrences - {len(exact_matches)} exact matches and {len(fuzzy_matches)} fuzzy matches")
    
    # Create output filename based on search term
    search_results_csv = f"search_results_{search_term.replace(' ', '_')}.csv"
    output_pdf_path = os.path.join(output_directory, f"highlighted_{search_term.replace(' ', '_')}.pdf")
    
    # Sort results by date and page number
    # Convert date to datetime for proper sorting if needed
    if 'date' in search_results.columns:
        # Handle different date formats by trying multiple approaches
        try:
            search_results['date'] = pd.to_datetime(search_results['date'])
        except:
            try:
                # Try with a specific format if automatic parsing fails
                search_results['date'] = pd.to_datetime(search_results['date'], format='%Y-%m-%d', errors='coerce')
            except:
                print("Warning: Could not convert date column to datetime for sorting")
    
    # Sort by date and page number (both ascending)
    if 'date' in search_results.columns and pd.api.types.is_datetime64_dtype(search_results['date']):
        search_results = search_results.sort_values(by=['date', 'page_number'], ascending=[True, True])
    elif 'page_number' in search_results.columns:
        # If date conversion failed, just sort by page number
        search_results = search_results.sort_values(by='page_number', ascending=True)
    
    # Convert back to string format for dates if needed
    if 'date' in search_results.columns and pd.api.types.is_datetime64_dtype(search_results['date']):
        search_results['date'] = search_results['date'].dt.strftime('%Y-%m-%d')
    
    # Save search results to CSV with similarity score included
    search_results.to_csv(search_results_csv, index=False)
    print(f"Saved search results to {search_results_csv}")
    
    # Step 3: Highlight and create PDF
    # Create a PDF writer for the output file
    pdf_writer = PdfWriter()
    
    # Keep track of processed files and temporary files
    processed_files = {}  # Changed to dict to store all hits for a page
    temp_files = []
    
    try:
        # Group search results by filename to process each page once with all highlights
        grouped_results = search_results.groupby('filename')
        
        for filename, group in grouped_results:
            pdf_path = os.path.join(base_folder, filename)
            
            # Check if the file exists
            if not os.path.exists(pdf_path):
                print(f"Warning: File not found: {pdf_path}")
                continue
            
            try:
                # Open the PDF
                doc = pymupdf.open(pdf_path)
                page = doc[0]  # Single-page PDFs
                
                # Apply all highlights for this page
                hits_count = 0
                for _, row in group.iterrows():
                    # Create a rectangle from the bounding box coordinates
                    rect = pymupdf.Rect(row['bbx0'], row['bby0'], row['bbx1'], row['bby1'])
                    
                    # Add highlight annotation
                    highlight = page.add_highlight_annot(rect)
                    hits_count += 1
                
                # Create a temporary highlighted PDF
                temp_path = f"_tmp_{filename.replace(' ', '_').replace(',', '').replace('.pdf', '')}.pdf"
                doc.save(temp_path, incremental=False)
                doc.close()
                
                # Track temp files
                temp_files.append(temp_path)
                
                # Add the temporary PDF to our output PDF
                pdf_writer.append(temp_path)
                
                # Store the number of hits for this file
                processed_files[filename] = hits_count
                
                print(f"Highlighted {hits_count} occurrences in {filename}")
                
            except Exception as e:
                print(f"Error processing {pdf_path}: {e}")
        
        # Save the final PDF if we have any pages
        if len(processed_files) > 0:
            pdf_writer.write(output_pdf_path)
            total_hits = sum(processed_files.values())
            print(f"Created PDF with {len(processed_files)} pages and {total_hits} highlighted terms at: {output_pdf_path}")
            
            # Open the result
            if sys.platform.startswith("darwin"):
                os.system(f"open '{output_pdf_path}'")
            elif os.name == "nt":
                os.startfile(output_pdf_path)
            else:
                os.system(f"xdg-open '{output_pdf_path}'")
        else:
            print("No pages were successfully processed. No output PDF created.")
            
    finally:
        # Clean up temporary files
        print("Cleaning up temporary files...")
        for temp_path in temp_files:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as e:
                    print(f"Failed to remove {temp_path}: {e}")
        
        # Catch any missed temporary files
        for temp_file in glob.glob("_tmp_*.pdf"):
            try:
                os.remove(temp_file)
            except Exception:
                pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Search for terms and create highlighted PDF')
    parser.add_argument('search_term', help='Term to search for')
    parser.add_argument('--base_folder', default=r"C:\Users\denis\Documents\WWRDownloading\PDFs",
                        help='Base folder where PDF files are stored')
    parser.add_argument('--output_dir', default='.', help='Directory where to save output files')
    parser.add_argument('--threshold', type=int, default=80,
                        help='Similarity threshold (0-100) for fuzzy matching')
    
    args = parser.parse_args()
    
    search_and_highlight(args.search_term, args.base_folder, args.output_dir, args.threshold)