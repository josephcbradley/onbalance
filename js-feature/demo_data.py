
import pandas as pd
import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon, Point

def generate_dummy_data():
    # Dummy SHLAA housing data
    shlaa_data = gpd.GeoDataFrame({
        "site_id": range(1, 6),
        "site_name": [f"Site {i}" for i in range(1, 6)],
        "capacity": np.random.randint(50, 300, size=5),
        "geometry": [Polygon([
            (0.1*i, 0.1*i),
            (0.1*i+0.05, 0.1*i),
            (0.1*i+0.05, 0.1*i+0.05),
            (0.1*i, 0.1*i+0.05)
        ]) for i in range(5)]
    }, crs="EPSG:4326")

    # Dummy planning constraints (e.g. flood zones, green belt)
    constraints_data = gpd.GeoDataFrame({
        "constraint_type": ["Flood Zone", "Green Belt", "Heritage Site"],
        "description": ["High risk area", "Protected green space", "Cultural value"],
        "geometry": [
            Polygon([(0.15, 0.15), (0.25, 0.15), (0.25, 0.25), (0.15, 0.25)]),
            Polygon([(0.05, 0.05), (0.2, 0.05), (0.2, 0.1), (0.05, 0.1)]),
            Polygon([(0.3, 0.3), (0.35, 0.3), (0.35, 0.35), (0.3, 0.35)]),
        ]
    }, crs="EPSG:4326")

    # Dummy housing demand forecast data (as points)
    housing_demand = gpd.GeoDataFrame({
        "ward_name": [f"Ward {i}" for i in range(1, 6)],
        "forecast_demand": np.random.randint(200, 1000, size=5),
        "geometry": [Point(0.12*i, 0.12*i) for i in range(5)]
    }, crs="EPSG:4326")

    return shlaa_data, constraints_data, housing_demand