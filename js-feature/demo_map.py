import os
import warnings
import tempfile
import io
import numpy as np
import pandas as pd
import geopandas as gpd
import streamlit as st
import folium
import requests
from shapely.geometry import Point, Polygon
from streamlit_folium import st_folium, folium_static
from demo_data import generate_dummy_data  # Ensure this exists in the same directory or Python path

# Setup
os.environ['SHAPE_RESTORE_SHX'] = 'YES'
warnings.filterwarnings("ignore", message="Unverified HTTPS request")
st.set_page_config(layout="wide", page_title="Buildable Supply Explorer")
st.title("📍 Buildable Housing Supply Explorer")

# Toggle: Upload vs Demo
mode = st.sidebar.radio("Choose data source:", ["Upload your own", "Use demo data"])

if mode == "Upload your own":
    # 1. Upload SHLAA CSV
    st.sidebar.header("1. SHLAA Sites Data")
    shlaa_file = st.sidebar.file_uploader("Select SHLAA CSV", type="csv")
    if not shlaa_file:
        st.info("Please upload your SHLAA CSV to get started.")
        st.stop()
    df = pd.read_csv(shlaa_file)
    st.sidebar.write(f"Loaded SHLAA sites: {len(df)} rows")

    # 2. Boundary Data Source
    st.sidebar.header("2. Boundary Source")
    data_source = st.sidebar.radio("Choose boundary data:", ["ArcGIS REST (Leeds default)", "Upload Shapefile Files"])

    if data_source == "ArcGIS REST (Leeds default)":
        url = (
            "https://mapservices.leeds.gov.uk/arcgis/rest/services/"
            "Public/Boundary/FeatureServer/0/query"
            "?where=1=1&outFields=*&f=geojson"
        )
        resp = requests.get(url, verify=False)
        if resp.status_code != 200:
            st.error(f"Error fetching boundaries: HTTP {resp.status_code}")
            st.stop()
        boundary_gdf = gpd.read_file(io.StringIO(resp.text)).to_crs(epsg=4326)
    else:
        st.sidebar.write("Upload raw shapefile components (.shp, .dbf, .shx, .prj)")
        files = st.sidebar.file_uploader(
            "Select shapefile files", type=["shp", "dbf", "shx", "prj"], accept_multiple_files=True
        )
        if not files or not any(f.name.endswith('.shp') for f in files):
            st.info("Please upload all required shapefile components.")
            st.stop()
        with tempfile.TemporaryDirectory() as tmpdir:
            for uploaded in files:
                with open(os.path.join(tmpdir, uploaded.name), 'wb') as out:
                    out.write(uploaded.getbuffer())
            shp_path = next(os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.endswith('.shp'))
            boundary_gdf = gpd.read_file(shp_path)
    if boundary_gdf.crs is None:
        boundary_gdf.set_crs(epsg=27700, inplace=True)
    boundary_gdf = boundary_gdf.to_crs(epsg=4326)
    st.sidebar.write(f"Loaded {len(boundary_gdf)} boundary features")

    # 3. Boundary ID Selection
    st.sidebar.header("3. Boundary ID Field")
    exclude = ['geometry']
    id_choices = [c for c in boundary_gdf.columns if c not in exclude]
    boundary_id = st.sidebar.selectbox("Select boundary ID column", options=id_choices)
    st.sidebar.write(f"Using '{boundary_id}' as ID")

    # 4. Site Coordinates
    st.sidebar.header("4. Site Coordinates")
    coord_fmt = st.sidebar.radio("Coordinate format", ["Lon/Lat", "Easting/Northing"])
    if coord_fmt == "Lon/Lat":
        lon_col = st.sidebar.selectbox("Longitude column", df.columns.tolist())
        lat_col = st.sidebar.selectbox("Latitude column", df.columns.tolist())
        sites_gdf = gpd.GeoDataFrame(
            df, geometry=gpd.points_from_xy(df[lon_col], df[lat_col]), crs="EPSG:4326"
        )
    else:
        east_col = st.sidebar.selectbox("Easting column", df.columns.tolist())
        north_col = st.sidebar.selectbox("Northing column", df.columns.tolist())
        tmp = gpd.GeoDataFrame(
            df, geometry=gpd.points_from_xy(df[east_col], df[north_col]), crs="EPSG:27700"
        )
        sites_gdf = tmp.to_crs(epsg=4326)

    # 5. Capacity Field
    st.sidebar.header("5. Capacity Field")
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    cap_col = st.sidebar.selectbox("Select capacity column", options=numeric)
    st.sidebar.write(f"Using '{cap_col}' for buildable units")

    # 6. Spatial Join & Aggregate
    joined = gpd.sjoin(sites_gdf, boundary_gdf, how='inner', predicate='within')
    agg = joined.groupby(boundary_id)[cap_col].sum().reset_index().rename(columns={cap_col: 'capacity'})
    map_gdf = boundary_gdf.merge(agg, on=boundary_id, how='left').fillna({'capacity': 0})

    # 7. Map Filters & Style
    st.sidebar.header("6. Map Filters & Style")
    min_cap = st.sidebar.number_input("Min capacity", min_value=0, value=0)
    max_cap = st.sidebar.number_input("Max capacity", min_value=0, value=int(map_gdf.capacity.max()))
    colors = st.sidebar.selectbox("Color scale", ["YlOrRd", "Viridis", "Plasma", "Inferno"])
    vis = map_gdf[(map_gdf.capacity >= min_cap) & (map_gdf.capacity <= max_cap)]

    # 8. Render Map
    if not vis.empty:
        cent = vis.geometry.centroid
        center = [cent.y.mean(), cent.x.mean()]
    else:
        bcent = boundary_gdf.geometry.centroid
        center = [bcent.y.mean(), bcent.x.mean()]

    m = folium.Map(location=center, zoom_start=11)
    folium.Choropleth(
        geo_data=vis, data=vis,
        columns=[boundary_id, 'capacity'], key_on=f"feature.properties.{boundary_id}",
        fill_color=colors, fill_opacity=0.7, line_opacity=0.3,
        legend_name="Potential Housing Units"
    ).add_to(m)

    for _, r in sites_gdf.iterrows():
        folium.CircleMarker(
            [r.geometry.y, r.geometry.x], radius=3, color='blue', fill=True, fill_opacity=0.6,
            popup=f"Site: {r.get('SiteID', '')}<br>Capacity: {r[cap_col]}"
        ).add_to(m)

    st.subheader("🗺️ Buildable Supply Map")
    st_folium(m, width=800, height=600)

    st.subheader("📋 Capacity by Area")
    st.dataframe(vis[[boundary_id, 'capacity']].sort_values('capacity', ascending=False))

else:
    # DEMO DATA MAP
    st.subheader("🧪 Demo Map: SHLAA and Constraints")
    shlaa_gdf, constraints_gdf, _ = generate_dummy_data()

    m = folium.Map(location=[51.5, 0], zoom_start=11)

    folium.GeoJson(
        shlaa_gdf,
        name="SHLAA Sites",
        style_function=lambda x: {"color": "blue", "fillOpacity": 0.5},
        tooltip=folium.GeoJsonTooltip(fields=shlaa_gdf.columns.tolist()),
    ).add_to(m)

    folium.GeoJson(
        constraints_gdf,
        name="Planning Constraints",
        style_function=lambda x: {"color": "red", "fillOpacity": 0.4},
        tooltip=folium.GeoJsonTooltip(fields=constraints_gdf.columns.tolist()),
    ).add_to(m)

    folium.LayerControl().add_to(m)
    st_folium(m, width=1000, height=600)