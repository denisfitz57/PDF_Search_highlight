import pandas as pd
def load_data(file_path):
    try:
        df = pd.read_csv(file_path)
        return df
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
        return None

def filter_data_by_year(df, start_year, end_year):
    if 'date' not in df.columns:
        print("Error: The DataFrame does not contain a 'date' column.")
        return None
    
    df['date'] = pd.to_datetime(df['date'])
    filtered_df = df[(df['date'].dt.year >= start_year) & (df['date'].dt.year <= end_year)]
    return filtered_df

def calculate_yearly_average(df, name_column, value_column):
    if name_column not in df.columns or value_column not in df.columns:
        print("Error: The DataFrame does not contain the specified columns.")
        return None
    
    df_grouped = df.groupby(df['date'].dt.year).agg({value_column: 'mean'}).reset_index()
    df_grouped.rename(columns={'date': 'year'}, inplace=True)
    return df_grouped

def plot_yearly_average(df, name, value_column):
    import matplotlib.pyplot as plt
    
    plt.figure(figsize=(10, 5))
    plt.plot(df['year'], df[value_column], marker='o', label=name)
    plt.title(f'Yearly Average of {name}')
    plt.xlabel('Year')
    plt.ylabel('Average')
    plt.grid()
    plt.legend()
    plt.show()