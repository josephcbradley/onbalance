# Streamlit App: Buildable Housing Supply Explorer
# ------------------------------------------------------------------
# This script loads SHLAA site data (shapefile), calculates site areas,
# fetches or loads boundary and constraint data, and renders an interactive map.
#
# Requirements:
#   pip install -r requirements.txt
#
# Usage:
#   streamlit run demo_map.py

import os
import glob
import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import folium
from streamlit_folium import st_folium
import requests
import io
import warnings
import tempfile
from streamlit_sortables import sort_items
from load_data import shlaa_gdf, constraint_layers 

# Allow shapefile restoration if missing .shx
os.environ['SHAPE_RESTORE_SHX'] = 'YES'
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

st.set_page_config(layout="wide", page_title="Buildable Supply Explorer")
st.title("📍 Buildable Housing Supply Explorer")

# 1. Load the SHP file for SHLAA Sites (from the 'data/London' folder)
st.sidebar.header("1. SHLAA Sites")

# Load SHLAA sites from the shapefile

# Back to WGS84 for mapping

st.sidebar.write(f"Loaded {len(shlaa_gdf)} SHLAA sites; computed areas.")

# 2. Fetch or load constraint data
st.sidebar.header("2. Constraint Data")

constraint_source = st.sidebar.selectbox(
    "Load constraints from:",
    options=["Local GeoJSON files", "Planning Data API"]
)


density= st.sidebar.slider(label = "density", min_value=20, max_value=120)

# Sidebar: select constraint layers to display
selected = st.sidebar.multiselect(
    "Constraint layers to show:", list(constraint_layers.keys()), default=list(constraint_layers.keys())
)

# 3. Base map
m = folium.Map(location=[shlaa_gdf.geometry.centroid.y.mean(), shlaa_gdf.geometry.centroid.x.mean()], zoom_start=11)

# 4. Overlay SHLAA sites
#show_sites = st.sidebar.checkbox("Show SHLAA Sites", value=True)
#if show_sites:
folium.GeoJson(
    shlaa_gdf,
    name="SHLAA Sites",
    style_function=lambda feat: {"color": "blue", "weight": 1},
    tooltip=folium.GeoJsonTooltip(fields=["area_ha"], aliases=["Area (ha):"])  
).add_to(m)

# 5. Overlay constraints
colors = {name: col for name, col in zip(constraint_layers.keys(), ["red","green","purple","orange"])}
for name in selected:
    
    gdf = constraint_layers[name]["gdf"]
    folium.GeoJson(
        gdf,
        name=name,
        style_function=lambda feat, color=colors.get(name, 'red'): {"color": color, "fillOpacity": 0.2},
        tooltip=folium.GeoJsonTooltip(fields=[f for f in gdf.columns if gdf.dtypes[f] != 'geometry'])
    ).add_to(m)

# 6. Layer control and display
folium.LayerControl().add_to(m)
st.subheader("🗺️ Buildable Supply Map with Constraints")

area_ha = shlaa_gdf.to_crs(epsg=3857).area.sum() / 10000
st.write(shlaa_gdf.crs, area_ha)
st.write(density)
st.write(area_ha)
st.write(area_ha*density) # Number of dwellings
st_folium(m, width=1000, height=600)

# 7. Show SHLAA area summary
st.subheader("📋 SHLAA Site Areas")
st.dataframe(shlaa_gdf[["area_m2","area_ha"]].describe())


# Display the map in Streamlit
# Layout: Split into two columns (map on left, controls on right) - removed the left col
left_col, right_col = st.columns([2, 1])

with right_col:
    st.subheader("📊 Rank Constraints")
    st.markdown("Drag and drop to rank constraints from most to least important.")

    # Unique constraints as list
    unique_constraints = list(constraint_layers.keys())

    # Initialize state if not present
    if "constraint_order" not in st.session_state:
        st.session_state.constraint_order = unique_constraints

    # Drag-and-drop sorting
    sorted_constraints = sort_items(st.session_state.constraint_order, direction="vertical")
    st.session_state.constraint_order = sorted_constraints

    # Display rankings in a table
    rankings_df = pd.DataFrame({
        "Constraint Type": sorted_constraints,
        "Rank (1 = Most Important)": list(range(1, len(sorted_constraints) + 1))
    })

    right_col.markdown("### 📋 Your Rankings")
    right_col.dataframe(rankings_df, use_container_width=True)