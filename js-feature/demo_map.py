import os
import warnings
import tempfile
import io
import pandas as pd
import geopandas as gpd
import streamlit as st
import folium
import requests
from shapely.geometry import Point, Polygon
from streamlit_folium import st_folium
from demo_data import generate_dummy_data

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
    data_source = st.sidebar.radio("Choose boundary data:", ["ArcGIS REST (London default)", "Upload Shapefile Files"])

    if data_source == "ArcGIS REST (London default)":
        # Fetch London Borough Boundary Data (GeoJSON)
        url = "https://gis2.london.gov.uk/server/rest/services/apps/Layers/MapServer/1/query?f=geojson"
        resp = requests.get(url, verify=False)
        if resp.status_code != 200:
            st.error(f"Error fetching boundaries: HTTP {resp.status_code}")
            st.stop()
        # Read the GeoJSON data into a GeoDataFrame
        boundary_gdf = gpd.read_file(io.StringIO(resp.text)).to_crs(epsg=4326)
    else:
        # Code to handle shapefile uploads (your existing implementation)
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
    
    # 3. Check if CRS exists
    if boundary_gdf.crs is None:
        boundary_gdf.set_crs(epsg=27700, inplace=True)  # Set to a common UK CRS if missing
    boundary_gdf = boundary_gdf.to_crs(epsg=4326)  # Ensure CRS is in WGS 84
    st.sidebar.write(f"Loaded {len(boundary_gdf)} boundary features")

    # 4. Boundary ID Selection
    st.sidebar.header("3. Boundary ID Field")
    exclude = ['geometry']
    id_choices = [c for c in boundary_gdf.columns if c not in exclude]
    boundary_id = st.sidebar.selectbox("Select boundary ID column", options=id_choices)
    st.sidebar.write(f"Using '{boundary_id}' as ID")

    # 5. Site Coordinates
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

    # 6. Capacity Field
    st.sidebar.header("5. Capacity Field")
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    cap_col = st.sidebar.selectbox("Select capacity column", options=numeric)
    st.sidebar.write(f"Using '{cap_col}' for buildable units")

    # 7. Spatial Join & Aggregate
    joined = gpd.sjoin(sites_gdf, boundary_gdf, how='inner', predicate='within')
    agg = joined.groupby(boundary_id)[cap_col].sum().reset_index().rename(columns={cap_col: 'capacity'})
    map_gdf = boundary_gdf.merge(agg, on=boundary_id, how='left').fillna({'capacity': 0})

    # 8. Map Filters & Style
    st.sidebar.header("6. Map Filters & Style")
    min_cap = st.sidebar.number_input("Min capacity", min_value=0, value=0)
    max_cap = st.sidebar.number_input("Max capacity", min_value=0, value=int(map_gdf.capacity.max()))
    colors = st.sidebar.selectbox("Color scale", ["YlOrRd", "Viridis", "Plasma", "Inferno"])
    vis = map_gdf[(map_gdf.capacity >= min_cap) & (map_gdf.capacity <= max_cap)]

    # 9. Render Map
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
    st.subheader("🧪 Demo Map: SHLAA and Constraints")

    # Load demo data once
    if 'demo_data' not in st.session_state:
        st.session_state.demo_data = generate_dummy_data()
    shlaa_gdf, constraints_gdf, housing_demand_gdf = st.session_state.demo_data

    # Sidebar toggle controls
    st.sidebar.header("🗺️ Toggle Map Layers")
    show_shlaa = st.sidebar.checkbox("Show SHLAA sites (green)", value=True)
    show_constraints = st.sidebar.checkbox("Show planning constraints (red)", value=True)
    show_housing_demand = st.sidebar.checkbox("Show housing need points (orange)", value=True)

    # Center map on London
    m = folium.Map(location=[51.5, -0.1], zoom_start=11)

    # SHLAA layer
    if show_shlaa:
        folium.GeoJson(
            shlaa_gdf,
            name="SHLAA Sites",
            style_function=lambda x: {"color": "green", "fillOpacity": 0.5},
            tooltip=folium.GeoJsonTooltip(fields=[col for col in shlaa_gdf.columns if col != 'geometry']),
        ).add_to(m)

    # Constraints layer(s) by constraint_type
    if show_constraints:
        for ctype in constraints_gdf["constraint_type"].unique():
            subset = constraints_gdf[constraints_gdf["constraint_type"] == ctype]
            folium.GeoJson(
                subset,
                name=f"Constraint: {ctype}",
                style_function=lambda x: {"color": "red", "fillOpacity": 0.3},
                tooltip=folium.GeoJsonTooltip(fields=["constraint_type", "description"]),
            ).add_to(m)

    # Housing demand points
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

    # Final map setup
    folium.LayerControl().add_to(m)
    st_folium(m, width=1000, height=600)