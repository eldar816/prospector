import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import json
import os

# File paths (Ensuring all datasets remain available)
files = {
    "Residential": "data/Residential.json",
    "Miscellaneous": "data/Miscellaneous.json",
    "Special": "data/Special.json",
    "Vacant": "data/Vacant.json",
    "Condos": "data/Condos.json",
    "Commercial": "data/Commercial.json",
    "Co-Ops": "data/Coops.json",
    "Mixed-Use": "data/Mixed-Use.json",
}

borough_neighborhoods_file = "borough_neighborhoods.json"

# Borough number-to-name mapping
borough_map = {
    "1": "Manhattan",
    "2": "Bronx",
    "3": "Brooklyn",
    "4": "Queens",
    "5": "Staten Island"
}

# Function to extract borough-neighborhood mapping and save to JSON
def extract_borough_neighborhoods(file_paths):
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
            st.error(f"Error decoding JSON in {file_path}: {e}")
            continue

        if "BOROUGH" in df.columns and "NEIGHBORHOOD" in df.columns:
            df["BOROUGH"] = df["BOROUGH"].astype(str).str.strip()

            # Convert borough numbers to names but store both for lookup
            df["BOROUGH"] = df["BOROUGH"].replace(borough_map)

            df["NEIGHBORHOOD"] = df["NEIGHBORHOOD"].astype(str).str.strip().str.title()

            for borough, neighborhood in zip(df["BOROUGH"], df["NEIGHBORHOOD"]):
                if borough not in borough_neighborhoods:
                    borough_neighborhoods[borough] = set()
                borough_neighborhoods[borough].add(neighborhood)

    borough_neighborhoods = {borough: sorted(list(neighborhoods)) for borough, neighborhoods in borough_neighborhoods.items()}

    with open(borough_neighborhoods_file, "w") as f:
        json.dump(borough_neighborhoods, f, indent=4)

    return borough_neighborhoods

# Load or generate borough-neighborhood data
if not os.path.exists(borough_neighborhoods_file):
    borough_neighborhoods = extract_borough_neighborhoods(files.values())
else:
    with open(borough_neighborhoods_file, "r") as f:
        borough_neighborhoods = json.load(f)

# Function to load and clean data
def load_clean_data(file_paths, filters):
    df_list = []

    for file_path in file_paths:
        building_type = next((key for key, value in files.items() if value == file_path), "Unknown")  # Assign building type

        try:
            with open(file_path, "r") as file:
                content = file.read().strip()
                if not content.startswith("["):
                    content = content.replace('}\n{', '},{')
                    content = f'[{content}]'
                data = json.loads(content)
                df = pd.DataFrame(data)
        except json.JSONDecodeError as e:
            st.error(f"Error decoding JSON in {file_path}: {e}")
            continue

        df.columns = df.columns.str.strip().str.upper()

        if "BOROUGH" in df.columns:
            df["BOROUGH"] = df["BOROUGH"].astype(str).str.strip()
            df["BOROUGH"] = df["BOROUGH"].replace(borough_map)

        for col in ['LATITUDE', 'LONGITUDE', 'ZIP CODE', 'SALE PRICE', 'YEAR BUILT']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        df = df.dropna(subset=['LATITUDE', 'LONGITUDE'], how='all')
        df = df.drop_duplicates(subset=['ADDRESS'])

        df["BUILDING TYPE"] = building_type  # Add building type to the DataFrame

        for key, value in filters.items():
            if key == "BOROUGH" and value:
                matching_boroughs = [b for b, name in borough_map.items() if name in value]
                matching_boroughs += value  # Include both name and number
                df = df[df["BOROUGH"].astype(str).isin(matching_boroughs)]
            elif value:
                df = df[df[key].astype(str).str.contains(value, case=False, na=False)]

        df_list.append(df)

    return pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()

# Session state setup
if 'data' not in st.session_state:
    st.session_state['data'] = None

# Sidebar UI
st.sidebar.title("Search")

# Building Type Selection
selected_files = st.sidebar.multiselect("Select Building Type", list(files.keys()))

# **Fix: Ensure boroughs are properly formatted**
valid_boroughs = sorted(set(borough_map.values()))

borough_filter = st.sidebar.multiselect("Select Borough(s)", options=valid_boroughs)

# **Fix: Ensure neighborhoods are retrieved correctly**
selected_neighborhoods = []
if borough_filter:
    st.sidebar.markdown("### Neighborhoods by Borough:")
    
    for borough in borough_filter:
        matching_boroughs = [code for code, name in borough_map.items() if name == borough] + [borough]
        neighborhoods = set()

        # Collect neighborhoods from all matching borough names/numbers
        for b in matching_boroughs:
            if b in borough_neighborhoods:
                neighborhoods.update(borough_neighborhoods[b])

        neighborhoods = sorted(neighborhoods)

        if neighborhoods:
            selected = st.sidebar.multiselect(f"{borough} Neighborhoods", options=neighborhoods)
            selected_neighborhoods.extend(selected)

# Address & ZIP Code Filters
address_filter = st.sidebar.text_input("Search by Address", key="address_filter")
zip_filter = st.sidebar.text_input("Filter by ZIP Code (e.g., 10001, 10002, 10003-10010)", key="zip_filter")

# -- SEARCH BUTTON --
if st.sidebar.button("Search"):
    filters = {
        'BOROUGH': borough_filter,  # Boroughs now match both names and numbers
        'NEIGHBORHOOD': '|'.join(selected_neighborhoods) if selected_neighborhoods else None,
        'ADDRESS': address_filter,
        'ZIP CODE': zip_filter
    }

    file_paths = [files[label] for label in selected_files] if selected_files else files.values()
    st.session_state['data'] = load_clean_data(file_paths, filters)

# Display Search Results
if st.session_state['data'] is None or st.session_state['data'].empty:
    st.session_state['data'] = pd.DataFrame(columns=['LATITUDE', 'LONGITUDE'])
    st.warning("No valid data available. Displaying default map.")
    folium_static(folium.Map(location=[40.7128, -74.0060], zoom_start=12))

# Define distinct colors for different building types
building_type_colors = {
    "Residential": ("#4CAF50", "green"),  # Green label and icon
    "Miscellaneous": ("#9C27B0", "purple"),  # Purple label and icon
    "Special": ("#FF5722", "orange"),  # Orange label and icon
    "Vacant": ("#795548", "brown"),  # Brown label and icon
    "Condos": ("#3F51B5", "blue"),  # Blue label and icon
    "Commercial": ("#E91E63", "pink"),  # Pink label and icon
    "Co-Ops": ("#009688", "teal"),  # Teal label and icon
    "Mixed-Use": ("#FFC107", "cadetblue")  # Yellow label and cadetblue icon
}

# Display Search Results with updated colors
if not st.session_state['data'].empty:
    st.title("CRM Map & Data")
    data = st.session_state['data']

    st.subheader("Interactive Map")
    m = folium.Map(location=[data['LATITUDE'].mean(), data['LONGITUDE'].mean()], zoom_start=12)

    for _, row in data.iterrows():
        address = row.get('ADDRESS', 'No Address')
        lat, lon = row['LATITUDE'], row['LONGITUDE']
        building_type = row.get("BUILDING TYPE", "Unknown")

        # Assign colors dynamically
        label_color, icon_color = building_type_colors.get(building_type, ("#607D8B", "gray"))  # Default: Gray

        google_maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

        popup_content = f"""
        <div style="font-size:14px; padding:5px; width:280px;">
            <strong>Address:</strong> <a href="{google_maps_url}" target="_blank">{address}</a><br>
            <strong>Building Type:</strong> 
            <span style="background:{label_color}; color:white; padding:3px 6px; border-radius:4px; font-weight:bold;">{building_type}</span>
        </div>
        """

        folium.Marker(
            [lat, lon],
            popup=folium.Popup(popup_content, max_width=320),
            icon=folium.Icon(color=icon_color, icon="info-sign")
        ).add_to(m)

    folium_static(m)