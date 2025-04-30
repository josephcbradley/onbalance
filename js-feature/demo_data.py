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
            
            # Check if CRS is set
            if gdf.crs is None:
                st.warning("CRS is missing! Assuming EPSG:4326.")
                gdf.set_crs("EPSG:4326", allow_override=True, inplace=True)
            else:
                # If CRS is not EPSG:4326, convert it to EPSG:4326
                if gdf.crs != "EPSG:4326":
                    st.warning(f"CRS is {gdf.crs}. Converting to EPSG:4326.")
                    gdf = gdf.to_crs("EPSG:4326")
            
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