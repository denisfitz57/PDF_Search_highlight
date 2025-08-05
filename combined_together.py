import os
import argparse
import datetime
from search_function import search_documents, save_search_results
from pdf_highlighter import highlight_search_results

def search_and_highlight(search_term, base_folder, output_directory='.', similarity_threshold=80,
                         negation_terms=None, negation_distance=100, 
                         start_date=None, end_date=None, add_watermarks=True, add_bookmarks=True,
                         csv_filename=None, pdf_filename=None):
    """
    Combines search and highlight functionality in one call
    
    Parameters:
    search_term (str): Term to search for
    base_folder (str): Base folder where PDF files are stored
    output_directory (str): Directory where to save output files
    similarity_threshold (int): Minimum similarity score (0-100) for fuzzy matching
    negation_terms (list): Terms that negate the search if found nearby
    negation_distance (float): Maximum distance for negation terms to affect match
    start_date (str): Start date in YYYY-MM-DD format to filter results
    end_date (str): End date in YYYY-MM-DD format to filter results
    add_watermarks (bool): Whether to add semi-transparent filename watermarks to each page
    add_bookmarks (bool): Whether to add bookmarks for each file in the PDF outline
    csv_filename (str): Custom CSV filename (optional)
    pdf_filename (str): Custom PDF filename (optional)
    """
    # Step 1: Search for the term and get results
    print(f"Searching for '{search_term}'...")
    search_results, search_stats = search_documents(
        search_term, 
        'big_text_with_position_june4.csv', 
        similarity_threshold,
        negation_terms, 
        negation_distance,
        start_date,
        end_date
    )
    
    print(search_stats)
    
    if search_results is None:
        return
    
    # Step 2: Save search results to CSV
    if csv_filename:
        # Use custom CSV filename
        csv_path = os.path.join(output_directory, csv_filename)
        if not csv_filename.endswith('.csv'):
            csv_path += '.csv'
        
        # Save with custom filename
        search_results.to_csv(csv_path, index=False)
        print(f"Saved search results to custom file: {csv_path}")
    else:
        # Use default filename generation
        date_range_str = ""
        if start_date and end_date:
            date_range_str = f"_{start_date}_to_{end_date}"
        elif start_date:
            date_range_str = f"_from_{start_date}"
        elif end_date:
            date_range_str = f"_until_{end_date}"
            
        csv_path = save_search_results(
            search_results, 
            search_term, 
            negation_terms, 
            output_directory,
            date_range_str
        )
        print(f"Saved search results to {csv_path}")
    
    # Step 3: Create highlighted PDF
    print("Creating highlighted PDF...")
    
    # Modify pdf_highlighter call to accept custom filename
    if pdf_filename:
        # Pass custom PDF filename to highlighter
        pdf_path, status, pages, highlights = highlight_search_results(
            csv_path, 
            base_folder, 
            output_directory,
            add_watermarks=add_watermarks,
            add_bookmarks=add_bookmarks,
            custom_pdf_name=pdf_filename
        )
    else:
        pdf_path, status, pages, highlights = highlight_search_results(
            csv_path, 
            base_folder, 
            output_directory,
            add_watermarks=add_watermarks,
            add_bookmarks=add_bookmarks
        )
    
    if pdf_path:
        print(f"{status} at: {pdf_path}")
    else:
        print(status)
    
    return pdf_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Search for terms and create highlighted PDF with word-level fuzzy matching')
    parser.add_argument('search_term', help='Term to search for')
    parser.add_argument('--base_folder', default=r"C:\Users\denis\Documents\WWRDownloading\PDFs",
                        help='Base folder where PDF files are stored')
    parser.add_argument('--output_dir', default='.', help='Directory where to save output files')
    parser.add_argument('--threshold', type=int, default=80,
                        help='Similarity threshold (0-100) for fuzzy matching')
    parser.add_argument('--negation', action='append', dest='negation_terms',
                        help='Term that negates the match if found nearby (can be used multiple times)')
    parser.add_argument('--negation_distance', type=float, default=100.0,
                        help='Maximum distance for negation term to affect match')
    parser.add_argument('--start_date', help='Start date in YYYY-MM-DD format (e.g., 2020-01-01)')
    parser.add_argument('--end_date', help='End date in YYYY-MM-DD format (e.g., 2020-12-31)')
    parser.add_argument('--watermarks', action='store_true', 
                      help='Add semi-transparent filename watermarks to each page')
    parser.add_argument('--bookmarks', action='store_true', 
                      help='Add bookmarks for each file in the PDF outline')
    
    # NEW: Custom output file arguments
    parser.add_argument('--csv_output', dest='csv_filename',
                        help='Custom CSV output filename (e.g., "my_search_results.csv")')
    parser.add_argument('--pdf_output', dest='pdf_filename',
                        help='Custom PDF output filename (e.g., "highlighted_results.pdf")')
    
    args = parser.parse_args()
    
    # Validate date formats if provided
    if args.start_date:
        try:
            datetime.datetime.strptime(args.start_date, '%Y-%m-%d')
        except ValueError:
            print(f"Error: Start date must be in YYYY-MM-DD format. Got: {args.start_date}")
            exit(1)
            
    if args.end_date:
        try:
            datetime.datetime.strptime(args.end_date, '%Y-%m-%d')
        except ValueError:
            print(f"Error: End date must be in YYYY-MM-DD format. Got: {args.end_date}")
            exit(1)
    
    search_and_highlight(
        args.search_term, 
        args.base_folder, 
        args.output_dir, 
        args.threshold, 
        args.negation_terms, 
        args.negation_distance,
        args.start_date,
        args.end_date,
        add_watermarks=args.watermarks,
        add_bookmarks=args.bookmarks,
        csv_filename=args.csv_filename,  # NEW: Pass custom CSV filename
        pdf_filename=args.pdf_filename   # NEW: Pass custom PDF filename
    )