import pandas as pd
import re

# Read the CSV file
df = pd.read_csv('text_with_position.csv')

# Function to search and display results
def search_dataframe(df, column, search_term, case_sensitive=False, regex=False):
    """
    Search a DataFrame column for matching text and return matching rows.
    
    Parameters:
    df (DataFrame): The DataFrame to search
    column (str): The column name to search in
    search_term (str): The text to search for
    case_sensitive (bool): Whether the search should be case sensitive
    regex (bool): Whether to interpret search_term as a regular expression
    
    Returns:
    DataFrame: Rows containing matches
    """
    if regex:
        # Use regex pattern
        if not case_sensitive:
            pattern = re.compile(search_term, re.IGNORECASE)
        else:
            pattern = re.compile(search_term)
        matches = df[df[column].str.contains(pattern, na=False)]
    else:
        # Simple string matching
        matches = df[df[column].str.contains(search_term, case=case_sensitive, na=False)]
    
    return matches

# Example usage
search_term = "Fitzpatrick"
result = search_dataframe(df, 'text', search_term, case_sensitive=False)

print(f"Found {len(result)} rows containing '{search_term}'")
print(result.head())

# Save results
result.to_csv(f"search_results_{search_term}.csv", index=False)