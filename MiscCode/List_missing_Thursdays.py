import pandas as pd
import numpy as np
from datetime import datetime, timedelta

df = pd.read_csv('big_text_with_position_may16.csv')

# Make sure the date column is in datetime format
df['date'] = pd.to_datetime(df['date'])

# Get unique dates and sort them
unique_dates = df['date'].unique()
unique_dates = np.sort(unique_dates)  # Use np.sort() instead of .sort()

# Print the number of unique dates
print(f"Found {len(unique_dates)} unique dates in the dataset")

# Format and display the unique dates
print("\nList of all unique dates:")
for i, date in enumerate(unique_dates, 1):
    # Format date as YYYY-MM-DD
    formatted_date = pd.Timestamp(date).strftime('%Y-%m-%d')
    print(f"{i}. {formatted_date}")

# Optional: Save the unique dates to a CSV file
date_df = pd.DataFrame(unique_dates, columns=['date'])
date_df['formatted_date'] = date_df['date'].dt.strftime('%Y-%m-%d')
date_df.to_csv('unique_dates.csv', index=False)
print("\nUnique dates saved to 'unique_dates.csv'")


# Now let's generate all Thursdays between 1925 and 1986
start_date = pd.Timestamp('1925-01-01')
end_date = pd.Timestamp('1986-12-31')

# Generate all dates in range
all_dates = pd.date_range(start=start_date, end=end_date)

# Filter to get only Thursdays (where day of week is 3 in pandas, Monday=0)
all_thursdays = all_dates[all_dates.day_of_week == 3]

print(f"Generated {len(all_thursdays)} Thursdays between 1925 and 1986")

# Now compare with your existing dates
# Assuming unique_dates contains your dataset's dates
your_dates = pd.DatetimeIndex(unique_dates)

# Find missing Thursdays
missing_thursdays = all_thursdays.difference(your_dates)

# Find Thursdays that are in your dataset
present_thursdays = all_thursdays.intersection(your_dates)

# Calculate some statistics
total_thursdays = len(all_thursdays)
missing_count = len(missing_thursdays)
present_count = len(present_thursdays)
percentage_missing = (missing_count / total_thursdays) * 100

print(f"\nSummary:")
print(f"Total Thursdays in period: {total_thursdays}")
print(f"Thursdays present in your data: {present_count} ({100-percentage_missing:.2f}%)")
print(f"Missing Thursdays: {missing_count} ({percentage_missing:.2f}%)")

# Display the missing Thursdays (sorted by date)
missing_thursdays = sorted(missing_thursdays)
print(f"\nMissing Thursdays (first 20):")
for i, date in enumerate(missing_thursdays[:20], 1):
    print(f"{i}. {date.strftime('%Y-%m-%d')}")

# Optional: Save all missing Thursdays to CSV
missing_df = pd.DataFrame({'missing_date': missing_thursdays})
missing_df['formatted_date'] = missing_df['missing_date'].dt.strftime('%Y-%m-%d')
missing_df.to_csv('missing_thursdays.csv', index=False)
print(f"\nAll {missing_count} missing Thursdays saved to 'missing_thursdays.csv'")

# Check for patterns in the missing dates (e.g., by year)
if len(missing_thursdays) > 0:
    missing_by_year = pd.Series(missing_thursdays).dt.year.value_counts().sort_index()
    print("\nMissing Thursdays by year:")
    for year, count in missing_by_year.items():
        thursdays_in_year = all_thursdays[all_thursdays.year == year]
        percentage = (count / len(thursdays_in_year)) * 100
        print(f"{year}: {count} missing out of {len(thursdays_in_year)} ({percentage:.2f}%)")