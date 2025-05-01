import os
import geopandas as gpd
import streamlit as st
import numpy as np
from shapely.geometry import Polygon, Point
import pandas as pd

    
def load_geojson(geojson_path):
    if os.path.exists(geojson_path):
        try:
            # Read the GeoJSON file into a GeoDataFrame
            gdf = gpd.read_file(geojson_path)
            # Check if CRS is set to 3857
            if gdf.crs is None:
                st.warning("CRS is missing! Assuming EPSG:3857.")
                gdf.set_crs("EPSG:3857", allow_override=True, inplace=True)
            else:
                # If CRS is not EPSG:3857, convert it to EPSG:3857
                if gdf.crs != "EPSG:3857":
                    st.warning(f"CRS is {gdf.crs}. Converting to EPSG:3857.")
                    gdf = gdf.to_crs("EPSG:3857")

            return gdf
        except Exception as e:
            st.error(f"Error loading GeoJSON: {str(e)}")
            return None
    else:
        st.error(f"GeoJSON file not found at {geojson_path}")
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

@st.cache_data
def load_constraints():

    constraint_layers = {
        "High risk flood zone": {"path" : "./data/unified_geojson/Flood_Risk_Area_unified.geojson",},
        "Mid risk flood zone": {"path" : "./data/unified_geojson/Flood_Zone_2_unified.geojson",},
        "Low risk flood zone":{"path" :  "./data/unified_geojson/Flood_Zone_3_unified.geojson",},
        "Green Belt": {"path" : "./data/unified_geojson/Green_Belt_unified.geojson",},
        "Historic Park And Garden": {"path" : "./data/unified_geojson/Historic_Park_And_Garden_unified.geojson",},
        "Ancient Woodland": {"path" : "./data/unified_geojson/Ancient_Woodland_unified.geojson",},
        "Open Space": {"path" : "./data/unified_geojson/Open_Space_unified.geojson",},

    }

    for name, layer in constraint_layers.items():
        constraint_layers[name]["gdf"] = gpd.read_file(layer["path"])
        constraint_layers[name]["gdf"] = constraint_layers[name]["gdf"].to_crs(epsg=4326)

        # Fix timestamp errors by dropping the column
        # TypeError: Object of type Timestamp is not JSON serializable
        # # Fix all timestamp columns, not just ones called "timestamp"
        for col in constraint_layers[name]["gdf"].columns:
            # Check if column is a timestamp/datetime type
            if pd.api.types.is_datetime64_any_dtype(constraint_layers[name]["gdf"][col]):
                # Convert timestamps to strings
                constraint_layers[name]["gdf"][col] = constraint_layers[name]["gdf"][col].astype(str)
        # Set CRS to WGS84 if not set
        if constraint_layers[name]["gdf"].crs is None:
            constraint_layers[name]["gdf"].set_crs(epsg=4326, inplace=True)
        else:
            constraint_layers[name]["gdf"] = constraint_layers[name]["gdf"].to_crs(epsg=4326)
        # Check if the geometry is valid
        constraint_layers[name]["gdf"]["geometry"] = constraint_layers[name]["gdf"]["geometry"].apply(
            lambda geom: geom if geom.is_valid else geom.buffer(0)
        )
    
    return constraint_layers

shlaa_gdf = gpd.read_file("./data/London_SHLAA_2017_approvals_and_allocations/London_SHLAA_2017_approvals_and_allocations.geojson")

# Calculate area in square meters and hectares
shlaa_gdf = shlaa_gdf.to_crs(epsg=4326)  # Ensure it's in WGS84
shlaa_gdf['area_m2'] = shlaa_gdf.to_crs(epsg=3857).area
shlaa_gdf['area_ha'] = shlaa_gdf['area_m2'] / 10000


constraint_layers = load_constraints()