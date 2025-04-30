import streamlit as st
import folium
from streamlit_folium import folium_static
from demo_data import generate_dummy_data

# 🔧 Call the data generation function
shlaa_gdf, constraints_gdf, _ = generate_dummy_data()  # You can use `_` if you're not using housing_demand

# ✅ Ensure the data exists
if shlaa_gdf is not None and constraints_gdf is not None:
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

    st.write("### Land Availability and Constraints")
    folium_static(m, width=1000, height=600)