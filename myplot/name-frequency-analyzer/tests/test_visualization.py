import pytest
import pandas as pd
from src.visualization import plot_yearly_average

def test_plot_yearly_average():
    data = {
        'date': pd.date_range(start='2020-01-01', periods=24, freq='M'),
        'name': ['Alice'] * 12 + ['Bob'] * 12,
        'count': [5, 3, 6, 7, 8, 5, 6, 7, 4, 5, 6, 7] + [2, 3, 4, 5, 6, 2, 3, 4, 5, 6, 7, 8]
    }
    df = pd.DataFrame(data)
    
    # Call the function to plot yearly averages
    fig = plot_yearly_average(df, ['Alice', 'Bob'])
    
    # Check if the figure is created
    assert fig is not None
    assert fig.get_axes()  # Ensure there are axes in the figure

    # Check if the title is set correctly
    assert fig.axes[0].get_title() == 'Yearly Average Counts for Names'

    # Check if the x-axis and y-axis labels are set
    assert fig.axes[0].get_xlabel() == 'Year'
    assert fig.axes[0].get_ylabel() == 'Average Count'