# Streamlit App: Buildable Housing Supply Explorer
# ------------------------------------------------------------------
# This script loads SHLAA site data (shapefile), calculates site areas,
# fetches or loads boundary and constraint data, and renders an interactive map.
#
# Requirements:
#   pip install streamlit geopandas pandas folium streamlit-folium pyproj requests
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

# Allow shapefile restoration if missing .shx
os.environ['SHAPE_RESTORE_SHX'] = 'YES'
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

st.set_page_config(layout="wide", page_title="Buildable Supply Explorer")
st.title("📍 Buildable Housing Supply Explorer")

# 1. Load the SHP file for SHLAA Sites (from the 'data/London' folder)
st.sidebar.header("1. SHLAA Sites")
shp_files = glob.glob(os.path.join("data/London", "*.shp"))
if not shp_files:
    st.error("No .shp file found in 'data/London' folder.")
    st.stop()
shp_path = shp_files[0]

# Load SHLAA sites from the shapefile
shlaa_gdf = gpd.read_file(shp_path)

# Ensure CRS is set (assume EPSG:27700 if missing)
if shlaa_gdf.crs is None:
    shlaa_gdf.set_crs(epsg=27700, inplace=True)

# Calculate area in square meters and hectares
shlaa_gdf = shlaa_gdf.to_crs(epsg=27700)
shlaa_gdf['area_m2'] = shlaa_gdf.geometry.area
shlaa_gdf['area_ha'] = shlaa_gdf['area_m2'] / 10000
# Back to WGS84 for mapping
shlaa_gdf = shlaa_gdf.to_crs(epsg=4326)
st.sidebar.write(f"Loaded {len(shlaa_gdf)} SHLAA sites; computed areas.")

# 2. Fetch or load constraint data
st.sidebar.header("2. Constraint Data")
constraint_source = st.sidebar.selectbox(
    "Load constraints from:",
    options=["Local GeoJSON files", "Planning Data API"]
)
constraint_layers = {}
if constraint_source == "Local GeoJSON files":
    geojson_paths = glob.glob(os.path.join("data", "*.geojson"))
    for path in geojson_paths:
        name = os.path.splitext(os.path.basename(path))[0]
        gdf = gpd.read_file(path)
        if gdf.crs is None:
            gdf.set_crs(epsg=4326, inplace=True)
        else:
            gdf = gdf.to_crs(epsg=4326)
        constraint_layers[name] = gdf
elif constraint_source == "Planning Data API":
    # Example: fetch flood-risk-level
    datasets = ["flood-risk-level", "green-belt", "heritage-site"]
    base_url = "https://api.planning.data.gov.uk/entity.geojson"
    for ds in datasets:
        params = {"dataset": ds, "limit": 10000}
        resp = requests.get(base_url, params=params)
        if resp.status_code == 200:
            gdf = gpd.read_file(io.StringIO(resp.text))
            if gdf.crs is None:
                gdf.set_crs(epsg=4326, inplace=True)
            else:
                gdf = gdf.to_crs(epsg=4326)
            constraint_layers[ds] = gdf
        else:
            st.warning(f"Could not fetch {ds}: HTTP {resp.status_code}")

density= st.sidebar.slider(label = "density", min_value=20, max_value=100)

# Sidebar: select constraint layers to display
selected = st.sidebar.multiselect(
    "Constraint layers to show:", list(constraint_layers.keys()), default=list(constraint_layers.keys())
)

# 3. Base map
m = folium.Map(location=[shlaa_gdf.geometry.centroid.y.mean(), shlaa_gdf.geometry.centroid.x.mean()], zoom_start=11)

# 4. Overlay SHLAA sites
show_sites = st.sidebar.checkbox("Show SHLAA Sites", value=True)
if show_sites:
    folium.GeoJson(
        shlaa_gdf,
        name="SHLAA Sites",
        style_function=lambda feat: {"color": "blue", "weight": 1},
        tooltip=folium.GeoJsonTooltip(fields=["area_ha"], aliases=["Area (ha):"])  
    ).add_to(m)

# 5. Overlay constraints
colors = {name: col for name, col in zip(constraint_layers.keys(), ["red","green","purple","orange"])}
for name in selected:
    gdf = constraint_layers[name]
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
