import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def plot_yearly_average(df, names, start_year=None, end_year=None):
    """
    Plot the yearly average occurrences of multiple names.

    Parameters:
    df (DataFrame): The pandas DataFrame containing the data with 'date' and 'text' columns.
    names (list): A list of names to search for within the text column.
    start_year (int): Optional start year for filtering the data.
    end_year (int): Optional end year for filtering the data.
    """
    # Create a copy to avoid SettingWithCopyWarning
    df = df.copy()
    
    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'])

    # Filter by year range if specified
    if start_year is not None:
        df = df[df['date'].dt.year >= start_year]
    if end_year is not None:
        df = df[df['date'].dt.year <= end_year]

    # Create a 'year' column
    df['year'] = df['date'].dt.year
    
    # Create a new column to indicate which name is found in each text
    df['found_name'] = None
    for name in names:
        mask = df['text'].str.contains(name, case=False, na=False)
        df.loc[mask, 'found_name'] = name
    
    # Filter rows where at least one name was found
    df_with_names = df[df['found_name'].notna()]
    
    if df_with_names.empty:
        print(f"No occurrences of the specified names found in the text column.")
        return
        
    # Calculate yearly occurrences for each name
    yearly_counts = df_with_names.groupby(['year', 'found_name']).size().reset_index(name='count')
    
    # Calculate the proportion of each name per year - fixing the structure
    total_counts = yearly_counts.groupby('year')['count'].sum().reset_index()
    total_counts.rename(columns={'count': 'total'}, inplace=True)
    yearly_props = pd.merge(yearly_counts, total_counts, on='year')
    yearly_props['proportion'] = yearly_props['count'] / yearly_props['total']

    # Plotting
    plt.figure(figsize=(12, 6))
    for name in names:
        name_data = yearly_props[yearly_props['found_name'] == name]  # Changed from 'name' to 'found_name'
        if not name_data.empty:
            plt.plot(name_data['year'], 
                     name_data['proportion'], 
                     marker='o', label=name)

    plt.title('Yearly Proportion of Name Occurrences')
    plt.xlabel('Year')
    plt.ylabel('Proportion of Occurrences')
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid()
    plt.tight_layout()
    plt.show()