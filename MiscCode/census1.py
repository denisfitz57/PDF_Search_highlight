import requests, pandas as pd

API_KEY = "5faf802650b82d77edfde0e779a92309d60eb269"
url = ("https://api.census.gov/data/2023/acs/acs5?"
       "get=NAME,B19013_001E"
       "&for=tract:*&in=state:31+county:025"
       f"&key={API_KEY}")

df = pd.DataFrame(requests.get(url).json()[1:],  # skip header row
                  columns=["name", "median_income", "state", "county", "tract"])
df["median_income"] = pd.to_numeric(df["median_income"])
print(df.head())
