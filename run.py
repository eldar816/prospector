import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import json
import uuid
import re

# Function to load and clean data
def load_clean_data(file_path, zip_filter=None):
    try:
        with open(file_path, "r") as file:
            content = file.read().strip()
            
            # Ensure the JSON content is wrapped in an array
            if not content.startswith("["):
                content = f"[{content.replace('}\n{', '},{')}]"
            
            data = json.loads(content)
            
        df = pd.DataFrame(data)
    except json.JSONDecodeError as e:
        st.error(f"Error decoding JSON: {e}")
        return pd.DataFrame()
    
    # Standardize column names by stripping spaces and converting to uppercase
    df.columns = df.columns.str.strip().str.upper()
    
    # Ensure required columns exist
    required_columns = ['ADDRESS', 'BOROUGH', 'ZIP CODE', 'LATITUDE', 'LONGITUDE']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.warning(f"Dataset {file_path} is missing columns: {', '.join(missing_columns)}")
        return pd.DataFrame()  # Return empty DataFrame if required columns are missing
    
    # Convert numeric columns properly
    for col in ['LATITUDE', 'LONGITUDE', 'ZIP CODE', 'SALE PRICE', 'YEAR BUILT']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Drop rows where lat/lon is missing
    df = df.dropna(subset=['LATITUDE', 'LONGITUDE'], how='all')
    
    # Remove duplicate addresses to prevent multiple markers per address
    df = df.drop_duplicates(subset=['ADDRESS'])
    
    # Apply ZIP code filter if provided
    if zip_filter and zip_filter != "0":
        zip_codes = set()
        zip_pattern = re.compile(r'\b(\d{5})-(\d{5})\b|\b(\d{5})\b')
        matches = zip_pattern.findall(zip_filter)
        
        for match in matches:
            if match[0] and match[1]:  # Range of ZIP codes
                start, end = map(int, [match[0], match[1]])
                zip_codes.update(range(start, end + 1))
            elif match[2]:  # Single ZIP code
                zip_codes.add(int(match[2]))
        
        df = df[df['ZIP CODE'].isin(zip_codes)]
    
    return df

# Session state setup
if 'data' not in st.session_state:
    st.session_state['data'] = None
if 'notes' not in st.session_state:
    st.session_state['notes'] = {}
if 'contacted' not in st.session_state:
    st.session_state['contacted'] = {}

# File paths
files = {
    # Non existant in github version
    # "All":"data/all_filtered_data.json",
    "Residential": "data/Residential.json",
    "Miscellaneous": "data/Miscellaneous.json",
    "Special": "data/Special.json",
    "Vacant": "data/Vacant.json",
    "Condos": "data/Condos.json",
    "Commercial": "data/Commercial.json",
    "Co-Ops": "data/Coops.json"
}

# Sidebar selection
st.sidebar.title("Load Dataset")
for label, file_path in files.items():
    zip_filter = st.sidebar.text_input(f"Filter {label} by ZIP Code (e.g., 10001, 10005, 10007-10011, or 0 for all)")
    if st.sidebar.button(f"Load {label}"):
        st.session_state['data'] = load_clean_data(file_path, zip_filter)
        st.session_state['current_file'] = label

# Display Map
if st.session_state['data'] is not None and not st.session_state['data'].empty:
    st.title(f"{st.session_state['current_file']} Map & CRM")
    data = st.session_state['data']
    
    st.subheader("Interactive Map")
    
    # Create map
    m = folium.Map(location=[data['LATITUDE'].mean(), data['LONGITUDE'].mean()], zoom_start=12)
    
    for _, row in data.iterrows():
        folium.Marker(
            [row['LATITUDE'], row['LONGITUDE']],
            popup=f"{row.get('BOROUGH', 'Unknown')}: {row.get('ADDRESS', 'No Address')}"
        ).add_to(m)
    
    folium_static(m)
    
    # CRM Section
    st.subheader("CRM Notes & Contact Tracking")
    for i, row in data.iterrows():
        unique_id = f"{row.get('BOROUGH', 'Unknown')}-{row.get('ADDRESS', 'No Address')}-{i}"
        name = row.get('BOROUGH', 'Unknown')
        address = row.get('ADDRESS', 'No Address')
        
        st.markdown(f"### {name} - {address}")
        note = st.text_area(f"Notes for {name}", value=st.session_state['notes'].get(unique_id, ""), key=unique_id)
        if st.checkbox(f"Mark as Contacted {name}", value=st.session_state['contacted'].get(unique_id, False), key=f"contact_{unique_id}"):
            st.session_state['contacted'][unique_id] = True
        
        st.session_state['notes'][unique_id] = note
else:
    st.warning("No valid data available. Please check the dataset.")
