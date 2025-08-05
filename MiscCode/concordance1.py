import pandas as pd
import re
import argparse
import os
from tqdm import tqdm  # For progress bar, install with: pip install tqdm

def clean_text(text):
    """Clean text by removing excess whitespace and normalizing"""
    if not isinstance(text, str):
        return ""
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', str(text))
    return text.strip()

def create_concordance(target_word, context_words=5, csv_file='big_text_with_position_may12.csv', 
                      output_file=None, case_sensitive=False):
    """
    Create a concordance for a target word showing context from surrounding text.
    
    Parameters:
    target_word (str): The word to search for
    context_words (int): Number of words to show on each side of the target word
    csv_file (str): Path to the CSV file containing the text data
    output_file (str): Path to save the concordance results
    case_sensitive (bool): Whether to perform case-sensitive search
    """
    # Load the CSV file
    try:
        print(f"Loading data from {csv_file}...")
        df = pd.read_csv(csv_file)
        print(f"Loaded {len(df)} text entries")
    except FileNotFoundError:
        print(f"Error: File {csv_file} not found")
        return
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        return
    
    # Prepare search pattern
    search_pattern = r'\b' + re.escape(target_word) + r'\b'
    search_flags = 0 if case_sensitive else re.IGNORECASE
    
    # Lists to store concordance results
    concordance_lines = []
    source_info = []
    
    print(f"Searching for '{target_word}' and creating concordance...")
    
    # Process each text entry
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing"):
        text = row.get('text', '')
        
        if not isinstance(text, str) or not text.strip():
            continue
            
        # Clean the text
        text = clean_text(text)
        
        # Search for the target word
        matches = list(re.finditer(search_pattern, text, search_flags))
        
        if not matches:
            continue
            
        # Get source information
        date = row.get('date', 'Unknown date')
        filename = row.get('filename', 'Unknown file')
        page = row.get('page_number', 'Unknown page')
        
        # Process each match in this text
        for match in matches:
            # Get the matched word with original case
            matched_word = text[match.start():match.end()]
            
            # Split the text into words
            words = text.split()
            
            # Find the position of the matched word in the word list
            word_positions = []
            for i, word in enumerate(words):
                # Check if this word contains our match
                if re.search(search_pattern, word, search_flags):
                    word_positions.append(i)
            
            # Process each position where the word appears
            for pos in word_positions:
                # Get context words before
                start = max(0, pos - context_words)
                before = " ".join(words[start:pos])
                
                # Get context words after
                end = min(len(words), pos + context_words + 1)
                after = " ".join(words[pos+1:end])
                
                # Format the concordance line
                concordance_line = f"{before} <{matched_word}> {after}"
                concordance_lines.append(concordance_line)
                
                # Save source information
                source_info.append(f"{date} | {filename} | Page {page}")
    
    # Create results dataframe
    results = pd.DataFrame({
        'concordance': concordance_lines,
        'source': source_info
    })
    
    # Sort by date if possible
    if 'source' in results.columns and results['source'].str.contains(r'\d{4}-\d{2}-\d{2}').any():
        # Extract dates from source column
        results['date'] = results['source'].str.extract(r'(\d{4}-\d{2}-\d{2})')
        results = results.sort_values('date')
        results = results.drop('date', axis=1)  # Remove temporary date column
    
    # Save to file if specified
    if output_file is None:
        output_file = f"concordance_{target_word.replace(' ', '_')}.csv"
    
    results.to_csv(output_file, index=False)
    print(f"Found {len(concordance_lines)} occurrences of '{target_word}'")
    print(f"Concordance saved to {output_file}")
    
    # Display first few results
    if len(results) > 0:
        print("\nSample concordance lines:")
        for i, (concordance, source) in enumerate(zip(results['concordance'].head(5), results['source'].head(5))):
            print(f"{i+1}. {concordance}")
            print(f"   Source: {source}")
            print()
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create a concordance from OCR text data')
    parser.add_argument('target_word', help='Word to create concordance for')
    parser.add_argument('--context', type=int, default=5, 
                        help='Number of context words on each side (default: 5)')
    parser.add_argument('--csv', default='big_text_with_position_may12.csv',
                        help='Input CSV file with text data')
    parser.add_argument('--output', help='Output file name (default: concordance_{word}.csv)')
    parser.add_argument('--case-sensitive', action='store_true',
                        help='Perform case-sensitive search')
    
    args = parser.parse_args()
    
    create_concordance(
        args.target_word,
        context_words=args.context,
        csv_file=args.csv,
        output_file=args.output,
        case_sensitive=args.case_sensitive
    )