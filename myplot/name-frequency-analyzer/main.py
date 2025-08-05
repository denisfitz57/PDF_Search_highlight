import pandas as pd
import matplotlib.pyplot as plt
from src.data_processing import load_data, filter_data_by_year
from src.visualization import plot_yearly_average

def main():
    # Load the dataset
    df = load_data(r'C:\Users\denis\Documents\Highlighter\big_text_with_position_may16.csv')  # Adjust the path as necessary

    # Filter data for specific years
    filtered_df = filter_data_by_year(df, start_year=1900, end_year=2023)

    # List of names to analyze
    names_to_analyze = ['Kirchhoff', 'Rupp', 'Sheehan']

    # Plot yearly averages for the specified names
    plot_yearly_average(filtered_df, names_to_analyze)

if __name__ == "__main__":
    main()