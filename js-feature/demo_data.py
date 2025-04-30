import os
import geopandas as gpd
import streamlit as st
import folium
from streamlit_folium import st_folium
import numpy as np
from shapely.geometry import Polygon, Point

# Function to load SHLAA shapefile
def load_shapefile(shapefile_path):
    if os.path.exists(shapefile_path):
        try:
            # Read the shapefile into a GeoDataFrame
            gdf = gpd.read_file(shapefile_path)
            return gdf
        except Exception as e:
            st.error(f"Error loading shapefile: {str(e)}")
            return None
    else:
        st.error(f"Shapefile not found at {shapefile_path}")
        return None

# Function to generate dummy data for constraints and housing demand
def generate_dummy_data():
    base_lon, base_lat = -0.1, 51.5

    # SHLAA housing data (already loaded from the shapefile)

    # Planning constraints data with random severity
    constraints_data = gpd.GeoDataFrame({
        "constraint_type": ["Flood Zone", "Green Belt", "Heritage Site"],
        "description": ["High risk area", "Protected green space", "Cultural value"],
        "severity": np.random.randint(50, 100, size=3),  # Random severity
        "geometry": [
            Polygon([(-0.12, 51.51), (-0.11, 51.51), (-0.11, 51.52), (-0.12, 51.52)]),
            Polygon([(-0.08, 51.49), (-0.07, 51.49), (-0.07, 51.5), (-0.08, 51.5)]),
            Polygon([(-0.13, 51.48), (-0.12, 51.48), (-0.12, 51.49), (-0.13, 51.49)])
        ]
    }, crs="EPSG:4326")

    # Housing demand forecast data (as points)
    housing_demand = gpd.GeoDataFrame({
        "ward_name": [f"Ward {i}" for i in range(1, 6)],
        "forecast_demand": np.random.randint(200, 1000, size=5),
        "geometry": [Point(base_lon + 0.015*i, base_lat + 0.008*i) for i in range(5)]
    }, crs="EPSG:4326")

    return constraints_data, housing_demand

# Setup for loading the SHLAA shapefile from the 'data' folder
shapefile_path = "data/londonshlaa.shp"  # Adjust to your actual path

# Streamlit UI
st.title("📍 SHLAA Sites Map")

# Load SHLAA data
shlaa_gdf = load_shapefile(shapefile_path)

if shlaa_gdf is not None:
    # Check if CRS exists, if not, set it to a common CRS (e.g., EPSG:4326)
    if shlaa_gdf.crs is None:
        shlaa_gdf.set_crs("EPSG:4326", inplace=True)

    # Create a folium map centered at London
    m = folium.Map(location=[51.5074, -0.1278], zoom_start=11)

    # Add the SHLAA data to the map as a GeoJSON layer
    folium.GeoJson(
        shlaa_gdf,
        name="SHLAA Sites",
        style_function=lambda x: {"color": "green", "fillOpacity": 0.5},
        tooltip=folium.GeoJsonTooltip(fields=[col for col in shlaa_gdf.columns if col != 'geometry']),
    ).add_to(m)

    # Generate dummy data for constraints and housing demand
    constraints_data, housing_demand_data = generate_dummy_data()

    # Add constraints to the map
    for ctype in constraints_data["constraint_type"].unique():
        subset = constraints_data[constraints_data["constraint_type"] == ctype]
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

    # Add housing demand to the map
    for _, row in housing_demand_data.iterrows():
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=6,
            color='orange',
            fill=True,
            fill_opacity=0.7,
            popup=f"Ward: {row['ward_name']}<br>Forecast: {row['forecast_demand']}",
        ).add_to(m)

    # Render the map in Streamlit
    st.subheader("🗺️ Interactive SHLAA Sites Map")
    st_folium(m, width=1000, height=600)
else:
    st.warning("Please upload or load the SHLAA shapefile.")