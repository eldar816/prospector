import pandas as pd
import json

# Define file paths to read
file_paths = [
    "data/Residential.json",
    "data/Miscellaneous.json",
    "data/Special.json",
    "data/Vacant.json",
    "data/Condos.json",
    "data/Commercial.json",
    "data/Coops.json"
]

borough_neighborhoods = {}

for file_path in file_paths:
    try:
        with open(file_path, "r") as file:
            content = file.read().strip()
            if not content.startswith("["):
                content = content.replace('}\n{', '},{')
                content = f'[{content}]'
            data = json.loads(content)
            df = pd.DataFrame(data)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON in {file_path}: {e}")
        continue

    if "BOROUGH" in df.columns and "NEIGHBORHOOD" in df.columns:
        df["BOROUGH"] = df["BOROUGH"].astype(str).str.strip()
        df["NEIGHBORHOOD"] = df["NEIGHBORHOOD"].astype(str).str.strip()

        for borough, neighborhood in zip(df["BOROUGH"], df["NEIGHBORHOOD"]):
            if borough not in borough_neighborhoods:
                borough_neighborhoods[borough] = set()
            borough_neighborhoods[borough].add(neighborhood)

# Convert sets to sorted lists
borough_neighborhoods = {borough: sorted(list(neighborhoods)) for borough, neighborhoods in borough_neighborhoods.items()}

# Save as JSON file
json_file = "borough_neighborhoods.json"
with open(json_file, "w") as f:
    json.dump(borough_neighborhoods, f, indent=4)

# Save as CSV file
csv_file = "borough_neighborhoods.csv"
df_output = pd.DataFrame([(b, n) for b, neighborhoods in borough_neighborhoods.items() for n in neighborhoods], columns=["Borough", "Neighborhood"])
df_output.to_csv(csv_file, index=False)

print(f"Data saved to {json_file} and {csv_file}")
