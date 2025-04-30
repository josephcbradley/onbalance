
import pandas as pd
import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon, Point

def generate_dummy_data():
    import numpy as np
    import geopandas as gpd
    from shapely.geometry import Polygon, Point

    # Central London bounds (approx.)
    base_lon, base_lat = -0.1, 51.5

    # Dummy SHLAA housing data
    shlaa_data = gpd.GeoDataFrame({
        "site_id": range(1, 6),
        "site_name": [f"Site {i}" for i in range(1, 6)],
        "capacity": np.random.randint(50, 300, size=5),
        "geometry": [
            Polygon([
                (base_lon + 0.01*i, base_lat + 0.01*i),
                (base_lon + 0.01*i + 0.005, base_lat + 0.01*i),
                (base_lon + 0.01*i + 0.005, base_lat + 0.01*i + 0.005),
                (base_lon + 0.01*i, base_lat + 0.01*i + 0.005)
            ]) for i in range(5)
        ]
    }, crs="EPSG:4326")

    # Dummy planning constraints
    constraints_data = gpd.GeoDataFrame({
        "constraint_type": ["Flood Zone", "Green Belt", "Heritage Site"],
        "description": ["High risk area", "Protected green space", "Cultural value"],
        "geometry": [
            Polygon([(-0.12, 51.51), (-0.11, 51.51), (-0.11, 51.52), (-0.12, 51.52)]),
            Polygon([(-0.08, 51.49), (-0.07, 51.49), (-0.07, 51.5), (-0.08, 51.5)]),
            Polygon([(-0.13, 51.48), (-0.12, 51.48), (-0.12, 51.49), (-0.13, 51.49)])
        ]
    }, crs="EPSG:4326")

    # Dummy housing demand forecast data (as points)
    housing_demand = gpd.GeoDataFrame({
        "ward_name": [f"Ward {i}" for i in range(1, 6)],
        "forecast_demand": np.random.randint(200, 1000, size=5),
        "geometry": [Point(base_lon + 0.015*i, base_lat + 0.008*i) for i in range(5)]
    }, crs="EPSG:4326")

    return shlaa_data, constraints_data, housing_demand