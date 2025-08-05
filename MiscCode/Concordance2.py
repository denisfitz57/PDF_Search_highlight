import pandas as pd
import re
import argparse
import os
from tqdm import tqdm
from collections import Counter
import matplotlib.pyplot as plt
import seaborn as sns
from nltk.corpus import stopwords
import nltk

# Download NLTK stopwords if not already downloaded
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

def clean_text(text):
    """Clean text by removing excess whitespace and normalizing"""
    if not isinstance(text, str):
        return ""
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', str(text))
    return text.strip()

def create_concordance_with_frequency(target_word, context_words=5, csv_file='big_text_with_position_may12.csv', 
                        output_file=None, case_sensitive=False, analyze_freq=True, 
                        exclude_stopwords=True, top_n=20, generate_charts=True):
    """
    Create a concordance for a target word and analyze word frequencies around it.
    
    Parameters:
    target_word (str): The word to search for
    context_words (int): Number of words to show on each side of the target word
    csv_file (str): Path to the CSV file containing the text data
    output_file (str): Path to save the concordance results
    case_sensitive (bool): Whether to perform case-sensitive search
    analyze_freq (bool): Whether to analyze word frequencies
    exclude_stopwords (bool): Whether to exclude common stopwords from frequency analysis
    top_n (int): Number of top frequency words to show
    generate_charts (bool): Whether to generate frequency charts
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
    
    # Lists to store words before and after for frequency analysis
    words_before = []
    words_after = []
    
    # Get stopwords if needed
    stop_words = set(stopwords.words('english')) if exclude_stopwords else set()
    
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
                context_before = words[start:pos]
                before_text = " ".join(context_before)
                
                # Get context words after
                end = min(len(words), pos + context_words + 1)
                context_after = words[pos+1:end]
                after_text = " ".join(context_after)
                
                # Format the concordance line
                concordance_line = f"{before_text} <{matched_word}> {after_text}"
                concordance_lines.append(concordance_line)
                
                # Save source information
                source_info.append(f"{date} | {filename} | Page {page}")
                
                # Store words for frequency analysis
                if analyze_freq:
                    # For words immediately before the target
                    if pos > 0:
                        word_before = words[pos-1].lower()
                        if word_before and (not exclude_stopwords or word_before not in stop_words):
                            # Remove punctuation
                            word_before = re.sub(r'[^\w\s]', '', word_before)
                            if word_before:
                                words_before.append(word_before)
                    
                    # For words immediately after the target
                    if pos < len(words) - 1:
                        word_after = words[pos+1].lower()
                        if word_after and (not exclude_stopwords or word_after not in stop_words):
                            # Remove punctuation
                            word_after = re.sub(r'[^\w\s]', '', word_after)
                            if word_after:
                                words_after.append(word_after)
                    
                    # Also capture words within context window
                    for word in context_before:
                        word = word.lower()
                        if word and (not exclude_stopwords or word not in stop_words):
                            word = re.sub(r'[^\w\s]', '', word)
                            if word:
                                words_before.append(word)
                    
                    for word in context_after:
                        word = word.lower()
                        if word and (not exclude_stopwords or word not in stop_words):
                            word = re.sub(r'[^\w\s]', '', word)
                            if word:
                                words_after.append(word)
    
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
    
    # Create base filename without extension
    if output_file is None:
        base_filename = f"concordance_{target_word.replace(' ', '_')}"
        output_file = f"{base_filename}.csv"
    else:
        base_filename = os.path.splitext(output_file)[0]
    
    # Save concordance to file
    results.to_csv(output_file, index=False)
    print(f"Found {len(concordance_lines)} occurrences of '{target_word}'")
    print(f"Concordance saved to {output_file}")
    
    # Word frequency analysis
    if analyze_freq and concordance_lines:
        # Count frequencies
        before_counter = Counter(words_before)
        after_counter = Counter(words_after)
        
        # Get top N words
        top_before = before_counter.most_common(top_n)
        top_after = after_counter.most_common(top_n)
        
        # Create frequency dataframes
        freq_before_df = pd.DataFrame(top_before, columns=['word', 'frequency'])
        freq_after_df = pd.DataFrame(top_after, columns=['word', 'frequency'])
        
        # Save frequency data
        freq_before_df.to_csv(f"{base_filename}_freq_before.csv", index=False)
        freq_after_df.to_csv(f"{base_filename}_freq_after.csv", index=False)
        
        print(f"\nWord frequency analysis:")
        print(f"Top {len(top_before)} words BEFORE '{target_word}':")
        for word, count in top_before:
            print(f"  {word}: {count}")
            
        print(f"\nTop {len(top_after)} words AFTER '{target_word}':")
        for word, count in top_after:
            print(f"  {word}: {count}")
            
        # Generate charts if requested
        if generate_charts and (top_before or top_after):
            try:
                plt.figure(figsize=(12, 10))
                
                # Plot word frequencies before target
                plt.subplot(2, 1, 1)
                sns.barplot(x='frequency', y='word', data=freq_before_df.head(15))
                plt.title(f"Top 15 Words BEFORE '{target_word}'")
                plt.tight_layout()
                
                # Plot word frequencies after target
                plt.subplot(2, 1, 2)
                sns.barplot(x='frequency', y='word', data=freq_after_df.head(15))
                plt.title(f"Top 15 Words AFTER '{target_word}'")
                plt.tight_layout()
                
                # Save chart
                chart_file = f"{base_filename}_frequency_chart.png"
                plt.savefig(chart_file)
                print(f"\nFrequency chart saved to {chart_file}")
                
                # Close the plot to free memory
                plt.close()
                
            except Exception as e:
                print(f"Error generating charts: {e}")
    
    # Display first few results
    if len(results) > 0:
        print("\nSample concordance lines:")
        for i, (concordance, source) in enumerate(zip(results['concordance'].head(5), results['source'].head(5))):
            print(f"{i+1}. {concordance}")
            print(f"   Source: {source}")
            print()
    
    # Return all results
    if analyze_freq:
        return results, before_counter, after_counter
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create a concordance and word frequency analysis from OCR text data')
    parser.add_argument('target_word', help='Word to create concordance for')
    parser.add_argument('--context', type=int, default=5, 
                        help='Number of context words on each side (default: 5)')
    parser.add_argument('--csv', default='big_text_with_position_may12.csv',
                        help='Input CSV file with text data')
    parser.add_argument('--output', help='Output file name (default: concordance_{word}.csv)')
    parser.add_argument('--case-sensitive', action='store_true',
                        help='Perform case-sensitive search')
    parser.add_argument('--no-frequency', action='store_true',
                        help='Skip word frequency analysis')
    parser.add_argument('--include-stopwords', action='store_true',
                        help='Include common stopwords in frequency analysis')
    parser.add_argument('--top', type=int, default=20,
                        help='Number of top frequency words to show (default: 20)')
    parser.add_argument('--no-charts', action='store_true',
                        help='Skip generating frequency charts')
    
    args = parser.parse_args()
    
    create_concordance_with_frequency(
        args.target_word,
        context_words=args.context,
        csv_file=args.csv,
        output_file=args.output,
        case_sensitive=args.case_sensitive,
        analyze_freq=not args.no_frequency,
        exclude_stopwords=not args.include_stopwords,
        top_n=args.top,
        generate_charts=not args.no_charts
    )