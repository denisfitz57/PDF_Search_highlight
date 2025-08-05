import os
import pandas as pd
import re
import math
from rapidfuzz import fuzz, process

def clean_text(text):
    """Replace non-alphabetic characters with spaces and normalize whitespace"""
    if not isinstance(text, str):
        return ""
    # Replace non-alphabetic characters with spaces
    text = re.sub(r'[^a-zA-Z\s]', ' ', text)
    # Normalize whitespace (replace multiple spaces with single space)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def word_level_similarity(search_term, text):
    """
    Compare search term against each word in text and return highest similarity.
    
    Args:
        search_term (str): Single word to search for
        text (str): Text that may contain multiple words
        
    Returns:
        int: Highest similarity score (0-100)
    """
    if not isinstance(text, str) or not isinstance(search_term, str):
        return 0
    
    # Clean search term and text
    clean_search = clean_text(search_term).lower()
    clean_text_str = clean_text(text).lower()
    
    # Exact match gets 100
    if clean_search in clean_text_str.split():
        return 100
    
    # Split text into words
    words = clean_text_str.split()
    
    if not words:  # Empty text
        return 0
        
    # Calculate similarity for each word and return the maximum
    scores = [round(fuzz.ratio(clean_search, word)) for word in words]
    return max(scores) if scores else 0

def calculate_distance(x1, y1, x2, y2):
    """Calculate Euclidean distance between two points"""
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def search_documents(search_term, csv_file='big_text_with_position_may12.csv', similarity_threshold=80, 
                   negation_terms=None, negation_distance=100, start_date=None, end_date=None):
    """
    Searches for a term in CSV files with text positions.
    
    Parameters:
    search_term (str): Term to search for
    csv_file (str): CSV file with text position data
    similarity_threshold (int): Minimum similarity score (0-100) to consider a match
    negation_terms (list or str): Term(s) that negate the search if found nearby
    negation_distance (float): Maximum distance to consider for negation
    start_date (str): Start date in YYYY-MM-DD format to filter results
    end_date (str): End date in YYYY-MM-DD format to filter results
    
    Returns:
    DataFrame: Search results with position data
    str: Message with search statistics
    """
    # Convert single negation term to list for consistent handling
    if negation_terms and not isinstance(negation_terms, list):
        negation_terms = [negation_terms]
    
    # Step 1: Get text position data
    try:
        df = pd.read_csv(csv_file)
        search_stats = f"Loaded {len(df)} text entries from CSV file"
    except FileNotFoundError:
        return None, f"Error: {csv_file} not found"
    
    # Step 2: Perform fuzzy search
    search_stats += f"\nSearching for '{search_term}' with similarity threshold {similarity_threshold}%..."
    if negation_terms and len(negation_terms) > 0:
        search_stats += f"\nWill exclude results where any of these terms appears within {negation_distance} units: {', '.join(negation_terms)}"
    
    if start_date or end_date:
        date_filter_msg = "\nFiltering results by date: "
        if start_date and end_date:
            date_filter_msg += f"from {start_date} to {end_date}"
        elif start_date:
            date_filter_msg += f"from {start_date}"
        elif end_date:
            date_filter_msg += f"until {end_date}"
        search_stats += date_filter_msg
    
    # First try exact substring search for efficiency
    exact_matches = df[df['text'].str.contains(search_term, case=False, na=False)].copy()
    search_stats += f"\nFound {len(exact_matches)} exact matches"
    
    # Add similarity score of 100 for exact matches
    exact_matches['similarity'] = 100
    
    # For remaining entries, use fuzzy matching
    remaining_df = df.drop(exact_matches.index)
    search_stats += f"\nPerforming fuzzy matching on {len(remaining_df)} remaining entries..."
    
    # Apply fuzzy matching - this is computationally expensive for large datasets
    fuzzy_matches_chunks = []
    
    # Create chunks for processing to avoid memory issues
    chunk_size = 10000  # Adjust based on your system's memory
    total_chunks = (len(remaining_df) + chunk_size - 1) // chunk_size
    
    for i in range(0, len(remaining_df), chunk_size):
        chunk = remaining_df.iloc[i:i+chunk_size].copy()
        
        # Calculate word-level similarity scores for this chunk
        chunk['similarity'] = chunk['text'].apply(
            lambda x: word_level_similarity(search_term, x)
        )
        
        # Find matches above threshold
        chunk_matches = chunk[chunk['similarity'] >= similarity_threshold]
        fuzzy_matches_chunks.append(chunk_matches)
        
        search_stats += f"\nProcessed chunk {i//chunk_size + 1}/{total_chunks} - found {len(chunk_matches)} matches"
    
    # Combine all fuzzy matches from chunks
    fuzzy_matches = pd.concat(fuzzy_matches_chunks) if fuzzy_matches_chunks else pd.DataFrame()
    
    # Combine exact and fuzzy matches
    search_results = pd.concat([exact_matches, fuzzy_matches]).drop_duplicates()
    
    # Apply negation filtering if negation terms are provided
    if negation_terms and len(negation_terms) > 0 and len(search_results) > 0:
        search_stats += f"\nChecking for negation terms near matches..."
        
        # Create a dictionary to track negation matches by term
        negation_matches_dict = {}
        total_negation_matches = 0
        
        # Find occurrences of each negation term
        for term in negation_terms:
            if 'text' in df.columns:
                # Use word boundaries to match whole words only
                pattern = r'\b' + re.escape(term) + r'\b'
                term_matches = df[df['text'].str.contains(pattern, case=False, na=False, regex=True)].copy()
                negation_matches_dict[term] = term_matches
                total_negation_matches += len(term_matches)
                search_stats += f"\n  - Found {len(term_matches)} occurrences of negation term '{term}'"
        
        if total_negation_matches > 0:
            search_stats += f"\nFound {total_negation_matches} total occurrences of all negation terms"
            
            # For each search result, check if any negation term is nearby
            results_to_keep = []
            excluded_by_term = {term: 0 for term in negation_terms}
            
            for idx, row in search_results.iterrows():
                filename = row['filename']
                x1, y1 = row['bbx0'], row['bby0']
                
                # Check if any negation term is too close
                has_nearby_negation = False
                excluding_term = None
                min_distance = float('inf')
                
                # Process each negation term separately
                for term, term_matches in negation_matches_dict.items():
                    # Filter negation matches to the same file
                    file_negations = term_matches[term_matches['filename'] == filename]
                    
                    # Look at each negation instance
                    for neg_idx, neg_row in file_negations.iterrows():
                        x2, y2 = neg_row['bbx0'], neg_row['bby0']
                        distance = calculate_distance(x1, y1, x2, y2)
                        
                        # If this negation is close enough to exclude the match
                        if distance <= negation_distance and distance < min_distance:
                            has_nearby_negation = True
                            excluding_term = term
                            min_distance = distance
                            # Don't break - we want to find the closest negation term
                    
                # After checking all terms, record which term excluded this match
                if not has_nearby_negation:
                    results_to_keep.append(idx)
                elif excluding_term:
                    excluded_by_term[excluding_term] += 1
            
            # Keep only results without nearby negation terms
            search_results = search_results.loc[results_to_keep]
            search_stats += f"\nAfter negation filtering: {len(search_results)} matches remain"
            
            # Print negation term statistics
            for term, count in excluded_by_term.items():
                if count > 0:
                    search_stats += f"\n  - Term '{term}' excluded {count} matches"
    
    if len(search_results) == 0:
        return None, f"No results found for '{search_term}'"
    
    search_stats += f"\nFound total of {len(search_results)} occurrences - {len(exact_matches.index.intersection(search_results.index))} exact matches and {len(fuzzy_matches.index.intersection(search_results.index))} fuzzy matches"
    
    # Ensure we have date and page_number columns for sorting
    # If they don't exist, try to extract them from filename
    if 'date' not in search_results.columns:
        # Try to extract date from filename
        search_results['date'] = search_results['filename'].str.extract(r'(\d{4}-\d{2}-\d{2})')
    
    # Convert date to datetime for proper sorting and filtering
    if 'date' in search_results.columns:
        try:
            search_results['date'] = pd.to_datetime(search_results['date'])
            
            # Apply date filtering if specified
            original_count = len(search_results)
            
            if start_date:
                start_dt = pd.to_datetime(start_date)
                search_results = search_results[search_results['date'] >= start_dt]
                
            if end_date:
                end_dt = pd.to_datetime(end_date)
                search_results = search_results[search_results['date'] <= end_dt]
                
            if (start_date or end_date) and len(search_results) < original_count:
                search_stats += f"\nDate filtering removed {original_count - len(search_results)} results"
                search_stats += f"\nRemaining after date filtering: {len(search_results)} results"
                
        except:
            try:
                search_results['date'] = pd.to_datetime(search_results['date'], format='%Y-%m-%d', errors='coerce')
                
                # Apply date filtering if specified
                original_count = len(search_results)
                
                if start_date:
                    start_dt = pd.to_datetime(start_date)
                    search_results = search_results[search_results['date'] >= start_dt]
                    
                if end_date:
                    end_dt = pd.to_datetime(end_date)
                    search_results = search_results[search_results['date'] <= end_dt]
                    
                if (start_date or end_date) and len(search_results) < original_count:
                    search_stats += f"\nDate filtering removed {original_count - len(search_results)} results"
                    search_stats += f"\nRemaining after date filtering: {len(search_results)} results"
                    
            except:
                search_stats += "\nWarning: Could not convert date column to datetime for filtering"
    
    # If we have no results after date filtering, return None
    if len(search_results) == 0:
        return None, f"No results found for '{search_term}' in the specified date range"
    
    # Ensure we have page numbers
    if 'page_number' not in search_results.columns:
        # Try to extract page number from filename
        search_results['page_number'] = search_results['filename'].str.extract(r'Page(\d+)').astype(int, errors='ignore')
    
    # Sort by date and page number for final ordering
    if 'date' in search_results.columns and pd.api.types.is_datetime64_dtype(search_results['date']):
        search_results = search_results.sort_values(
            by=['date', 'page_number'], 
            ascending=[True, True]
        )
    else:
        # If date conversion failed, sort by page number
        if 'page_number' in search_results.columns:
            search_results = search_results.sort_values(
                by=['page_number'], 
                ascending=[True]
            )
    
    # Convert back to string format for dates 
    if 'date' in search_results.columns and pd.api.types.is_datetime64_dtype(search_results['date']):
        search_results['date'] = search_results['date'].dt.strftime('%Y-%m-%d')
    
    return search_results, search_stats

def save_search_results(search_results, search_term, negation_terms=None, output_directory='.', date_range_str=""):
    """
    Save search results to a CSV file
    
    Parameters:
    search_results (DataFrame): Search results dataframe
    search_term (str): The term that was searched
    negation_terms (list or str): Term(s) that negated the search if any
    output_directory (str): Directory where to save the CSV file
    date_range_str (str): String representing date range for filename
    
    Returns:
    str: Path to the CSV file
    """
    # Convert single negation term to list for consistent handling
    if negation_terms and not isinstance(negation_terms, list):
        negation_terms = [negation_terms]
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_directory):
        try:
            os.makedirs(output_directory)
            print(f"Created output directory: {output_directory}")
        except Exception as e:
            print(f"Warning: Failed to create output directory {output_directory}: {e}")
            # Fall back to current directory if creation fails
            output_directory = '.'
    
    search_term_filename = search_term.replace(' ', '_')
    if negation_terms and len(negation_terms) > 0:
        negation_str = "_not_" + "_".join([term.replace(' ', '_') for term in negation_terms])
        search_term_filename += negation_str
    
    # Add date range to filename if provided
    search_term_filename += date_range_str
    
    search_results_csv = os.path.join(output_directory, f"search_results_{search_term_filename}.csv")
    
    # Save search results to CSV
    search_results.to_csv(search_results_csv, index=False)
    
    return search_results_csv