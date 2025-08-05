def calculate_yearly_average(df, name_column='name', date_column='date', value_column='value'):
    """
    Calculate the yearly average occurrences of names in the DataFrame.

    Parameters:
    df (DataFrame): The pandas DataFrame containing the data
    name_column (str): The column name for names
    date_column (str): The column name for dates
    value_column (str): The column name for values to average

    Returns:
    DataFrame: A DataFrame with years as index and average values for each name
    """
    df[date_column] = pd.to_datetime(df[date_column])
    df['year'] = df[date_column].dt.year
    yearly_avg = df.groupby([name_column, 'year'])[value_column].mean().reset_index()
    return yearly_avg.pivot(index='year', columns=name_column, values=value_column)


def format_name(name):
    """
    Format the name for consistent usage.

    Parameters:
    name (str): The name to format

    Returns:
    str: The formatted name
    """
    return name.strip().title()  # Capitalize each word and strip whitespace


def validate_dataframe(df, required_columns):
    """
    Validate that the DataFrame contains the required columns.

    Parameters:
    df (DataFrame): The DataFrame to validate
    required_columns (list): A list of required column names

    Returns:
    bool: True if all required columns are present, False otherwise
    """
    return all(column in df.columns for column in required_columns)