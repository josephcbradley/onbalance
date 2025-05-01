# Streamlit App: Buildable Housing Supply Explorer
# ------------------------------------------------------------------
# This script loads SHLAA site data (shapefile), calculates site areas,
# fetches or loads boundary and constraint data, and renders an interactive map.
#
# Requirements:
#   pip install -r requirements.txt
#
# Usage:
#   streamlit run demo_map.py

import os
import glob
import streamlit as st

# Set page config first before any other Streamlit commands
st.set_page_config(layout="wide", page_title="Buildable Supply Explorer")

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import folium
from streamlit_folium import st_folium
import requests
import io
import warnings
import tempfile
from streamlit_sortables import sort_items

# Allow shapefile restoration if missing .shx
os.environ['SHAPE_RESTORE_SHX'] = 'YES'
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

# Import data after setting page config
from load_data import shlaa_gdf, constraint_layers, identify_site_constraints, calculate_buildable_supply
st.title("📍 Buildable Housing Supply Explorer")

# Sidebar Configuration
st.sidebar.header("1. Configuration")

# Set housing density (dwellings per hectare)
density = st.sidebar.slider(
    label="Housing Density (dwellings per hectare)",
    min_value=20,
    max_value=120,
    value=50
)

# Set housing target
housing_target = st.sidebar.number_input(
    label="Housing Target (number of dwellings)",
    min_value=1000,
    max_value=500000,
    value=50000
)

# Constraint Layers
st.sidebar.header("2. Constraint Layers")

# Select constraint layers to display
selected_constraints = st.sidebar.multiselect(
    "Constraint layers to show:",
    list(constraint_layers.keys()),
    default=list(constraint_layers.keys())
)

# Main layout: Split into two columns (map on left, controls on right)
left_col, right_col = st.columns([2, 1])

# Identify which constraints overlap with each SHLAA site
site_constraints = identify_site_constraints(shlaa_gdf, constraint_layers)

# Constraints ranking section
with right_col:
    st.subheader("📊 Prioritize Constraints")
    st.markdown("Drag and drop to rank constraints from most to least important to preserve.")
    st.markdown("Lower ranked constraints are violated first when necessary to meet housing targets.")

    # Unique constraints as list
    unique_constraints = list(constraint_layers.keys())

    # Initialize state if not present
    if "constraint_order" not in st.session_state:
        st.session_state.constraint_order = unique_constraints

    # Drag-and-drop sorting
    sorted_constraints = sort_items(st.session_state.constraint_order, direction="vertical")
    st.session_state.constraint_order = sorted_constraints

    # Display rankings in a table
    rankings_df = pd.DataFrame({
        "Constraint Type": sorted_constraints,
        "Rank (1 = Most Important)": list(range(1, len(sorted_constraints) + 1))
    })

    st.markdown("### 📋 Your Constraint Rankings")
    st.dataframe(rankings_df, use_container_width=True)

    # Calculate housing supply based on priorities
    if len(sorted_constraints) > 0:
        supply_results, total_potential = calculate_buildable_supply(
            shlaa_gdf, 
            site_constraints, 
            sorted_constraints,
            density
        )
        
        # Display housing target progress
        st.markdown("### 🏠 Housing Supply vs Target")
        
        target_met = total_potential >= housing_target
        available_percent = min(100, round((total_potential / housing_target) * 100, 1))
        
        # Create progress bar
        progress_color = "green" if target_met else "red"
        st.progress(min(1.0, total_potential / housing_target), text=f"{available_percent}% of target")
        
        if target_met:
            st.success(f"✅ Target can be met! {total_potential:,} potential homes vs {housing_target:,} target")
        else:
            st.error(f"❌ Target cannot be met. {total_potential:,} potential homes vs {housing_target:,} target")
            
            # Calculate how many constraints need to be violated
            # Find the first row where cumulative dwellings exceeds the target
            constraints_needed = "All"
            for i, row in supply_results.iterrows():
                if row['cumulative_dwellings'] >= housing_target:
                    constraints_needed = row['constraints_violated']
                    break
            
            st.info(f"To reach the target, you would need to allow building in areas with: {constraints_needed}")
        
        # Show staged results table
        st.markdown("### 📈 Progressive Supply by Constraints Violated")
        st.dataframe(supply_results, use_container_width=True)
        
        # Add a bar chart to visualize housing supply by constraint violation
        import plotly.graph_objects as go
        
        fig = go.Figure()
        
        # Add bars for each level of constraint violation
        fig.add_trace(go.Bar(
            x=supply_results['constraints_violated'],
            y=supply_results['dwellings'],
            name='Additional Dwellings',
            marker_color='royalblue'
        ))
        
        # Add line for cumulative total
        fig.add_trace(go.Scatter(
            x=supply_results['constraints_violated'],
            y=supply_results['cumulative_dwellings'],
            mode='lines+markers',
            name='Cumulative Dwellings',
            marker=dict(color='red'),
            line=dict(width=3)
        ))
        
        # Add target line
        fig.add_shape(
            type="line",
            xref="paper",
            yref="y",
            x0=0,
            y0=housing_target,
            x1=1,
            y1=housing_target,
            line=dict(
                color="green",
                width=2,
                dash="dash",
            ),
            name="Housing Target"
        )
        
        # Add annotation for the target
        fig.add_annotation(
            xref="paper",
            yref="y",
            x=0.02,
            y=housing_target,
            text=f"Target: {housing_target:,}",
            showarrow=False,
            font=dict(color="green", size=12),
            bgcolor="white",
            bordercolor="green",
            borderwidth=1
        )
        
        # Update layout
        fig.update_layout(
            title="Housing Supply by Constraint Priority",
            xaxis_title="Constraints Violated",
            yaxis_title="Number of Dwellings",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=40, b=20),
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)

# Map section
with left_col:
    st.subheader("🗺️ Buildable Supply Map with Constraints")
    
    # Create base map
    m = folium.Map(
        location=[shlaa_gdf.geometry.centroid.y.mean(), shlaa_gdf.geometry.centroid.x.mean()],
        zoom_start=11
    )
    
    # Create a copy of SHLAA GeoDataFrame with constraint information for visualization
    shlaa_viz = shlaa_gdf.copy()
    
    # Add constraint information to SHLAA visualization
    shlaa_viz['constraints'] = [', '.join(site_constraints.get(idx, [])) for idx in shlaa_viz.index]
    shlaa_viz['constraint_count'] = [len(site_constraints.get(idx, [])) for idx in shlaa_viz.index]
    
    # Style function for SHLAA sites based on constraints
    def site_style_function(feature):
        constraint_count = feature['properties']['constraint_count']
        
        # Color scheme based on number of constraints
        if constraint_count == 0:
            color = "#00CC00"  # Green for unconstrained sites
            opacity = 0.8
        elif constraint_count == 1:
            color = "#FFCC00"  # Yellow for one constraint
            opacity = 0.6
        elif constraint_count == 2:
            color = "#FF9900"  # Orange for two constraints
            opacity = 0.5
        else:
            color = "#FF0000"  # Red for three or more constraints
            opacity = 0.4
            
        return {
            "fillColor": color,
            "color": "#000000",
            "weight": 1,
            "fillOpacity": opacity
        }
    
    # Add SHLAA sites with color coding
    folium.GeoJson(
        shlaa_viz,
        name="SHLAA Sites",
        style_function=site_style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=["area_ha", "constraints", "constraint_count"],
            aliases=["Area (ha):", "Constraints:", "Number of Constraints:"],
            localize=True
        )
    ).add_to(m)
    
    # Add constraint layers
    colors = {name: col for name, col in zip(
        constraint_layers.keys(),
        ["#FF3333", "#FF9933", "#FFCC33", "#33CC33", "#3366FF", "#9933FF", "#996633"]
    )}
    
    for name in selected_constraints:
        gdf = constraint_layers[name]["gdf"]
        folium.GeoJson(
            gdf,
            name=name,
            style_function=lambda feat, color=colors.get(name, 'red'): {
                "color": color,
                "fillOpacity": 0.2,
                "weight": 2
            },
            tooltip=folium.GeoJsonTooltip(
                fields=[f for f in gdf.columns if gdf.dtypes[f] != 'geometry']
            )
        ).add_to(m)
    
    # Add a legend (as HTML)
    legend_html = '''
    <div style="position: fixed; bottom: 50px; left: 50px; z-index: 1000; background-color: white; 
        padding: 10px; border-radius: 5px; border: 1px solid grey; opacity: 0.8;">
        <p><strong>SHLAA Sites by Constraints</strong></p>
        <p><i style="background: #00CC00; opacity: 0.8; width: 20px; height: 14px; 
            display: inline-block; margin-right: 5px;"></i>No constraints</p>
        <p><i style="background: #FFCC00; opacity: 0.6; width: 20px; height: 14px; 
            display: inline-block; margin-right: 5px;"></i>1 constraint</p>
        <p><i style="background: #FF9900; opacity: 0.5; width: 20px; height: 14px; 
            display: inline-block; margin-right: 5px;"></i>2 constraints</p>
        <p><i style="background: #FF0000; opacity: 0.4; width: 20px; height: 14px; 
            display: inline-block; margin-right: 5px;"></i>3+ constraints</p>
    </div>
    '''
    
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Display the map
    st_folium(m, width=700, height=600)
    
    # Add SHLAA site statistics
    st.subheader("📊 SHLAA Site Statistics")
    
    # Calculate total area
    total_area_ha = shlaa_gdf['area_ha'].sum()
    total_potential_dwellings = int(total_area_ha * density)
    
    # Display site statistics
    st.markdown(f"**Total Sites:** {len(shlaa_gdf)}")
    st.markdown(f"**Total Area:** {total_area_ha:.2f} hectares")
    st.markdown(f"**Theoretical Maximum Capacity:** {total_potential_dwellings:,} homes at {density} dwellings/ha")
    
    # Display detailed SHLAA statistics
    with st.expander("Detailed SHLAA Site Area Statistics"):
        st.dataframe(shlaa_gdf[["area_m2", "area_ha"]].describe())