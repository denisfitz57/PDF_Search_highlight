import pandas as pd
import pytest
from src.data_processing import load_data, filter_data_by_year, calculate_yearly_average

@pytest.fixture
def sample_data():
    data = {
        'date': pd.date_range(start='1/1/2000', periods=5, freq='Y'),
        'name': ['Alice', 'Bob', 'Alice', 'Bob', 'Alice'],
        'count': [10, 20, 15, 25, 30]
    }
    return pd.DataFrame(data)

def test_load_data():
    df = load_data('data/sample_data.csv')
    assert not df.empty
    assert 'date' in df.columns
    assert 'name' in df.columns
    assert 'count' in df.columns

def test_filter_data_by_year(sample_data):
    filtered_data = filter_data_by_year(sample_data, 2001, 2003)
    assert len(filtered_data) == 2
    assert all(filtered_data['date'].dt.year.isin([2001, 2002, 2003]))

def test_calculate_yearly_average(sample_data):
    averages = calculate_yearly_average(sample_data)
    assert len(averages) == 3  # Expecting averages for 2000, 2001, 2002
    assert 'Alice' in averages.columns
    assert 'Bob' in averages.columns
    assert averages['Alice'].mean() == pytest.approx(18.33, rel=1e-2)  # Average for Alice
    assert averages['Bob'].mean() == pytest.approx(22.5, rel=1e-2)  # Average for Bob