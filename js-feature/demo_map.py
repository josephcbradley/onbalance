import os
import warnings
import pandas as pd
import geopandas as gpd
import folium
import streamlit as st
from shapely.geometry import Point, Polygon
from streamlit_folium import st_folium
from demo_data import generate_dummy_data
from demo_data import load_shapefile

# Setup
os.environ['SHAPE_RESTORE_SHX'] = 'YES'
warnings.filterwarnings("ignore", message="Unverified HTTPS request")
st.set_page_config(layout="wide", page_title="Buildable Supply Explorer")
st.title("📍 OnBalance")

# Load demo data
if 'demo_data' not in st.session_state:
    st.session_state.demo_data = generate_dummy_data()
constraints_gdf, housing_demand_gdf = st.session_state.demo_data

# Load the SHP file for SHLAA Sites (from the 'data' folder)
shp_file_path = "data/londonshlaa.shp"  

# Load SHLAA sites from the shapefile
shlaa_gdf = load_shapefile(shp_file_path)

# Sidebar toggle controls
st.sidebar.header("🗺️ Toggle Map Layers")
show_shlaa = st.sidebar.checkbox("Show SHLAA sites (green)", value=True)
show_constraints = st.sidebar.checkbox("Show planning constraints (red)", value=True)
show_housing_demand = st.sidebar.checkbox("Show housing need points (orange)", value=True)

# Center map on London
m = folium.Map(location=[51.5, -0.1], zoom_start=11)


# Constraints Layer (with color scale based on severity)
if show_constraints:
    for ctype in constraints_gdf["constraint_type"].unique():
        subset = constraints_gdf[constraints_gdf["constraint_type"] == ctype]
        # Apply color scale based on severity
        folium.GeoJson(
            subset,
            name=f"Constraint: {ctype}",
            style_function=lambda x: {
                "color": "red",
                "fillOpacity": 0.3,
                "weight": 2
            },
            tooltip=folium.GeoJsonTooltip(fields=["constraint_type", "description", "severity"]),
        ).add_to(m)

# Housing demand points layer (with color scale)
if show_housing_demand:
    for _, row in housing_demand_gdf.iterrows():
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=6,
            color='orange',
            fill=True,
            fill_opacity=0.7,
            popup=f"Ward: {row['ward_name']}<br>Forecast: {row['forecast_demand']}",
        ).add_to(m)

if show_shlaa and shlaa_gdf is not None:
    folium.GeoJson(
        shlaa_gdf,
        name="SHLAA Sites",  # Optional name for the layer
        style_function=lambda x: {'fillOpacity': 0.5, 'color': 'black'}  # Optional style for borders and opacity
    ).add_to(m)


# Final map setup
folium.LayerControl().add_to(m)

# Display the map in Streamlit
st.subheader("🗺️ Buildable Supply Map")
st_folium(m, width=1000, height=600)

st.subheader("📋 Capacity by Area")
# Display a table showing constraints with severity for user reference
st.dataframe(constraints_gdf[["constraint_type", "severity"]].sort_values("severity", ascending=False))