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
import plotly.graph_objects as go
from streamlit_sortables import sort_items

# Allow shapefile restoration if missing .shx
os.environ['SHAPE_RESTORE_SHX'] = 'YES'
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

# Import data after setting page config
from load_data import shlaa_gdf, constraint_layers, identify_site_constraints, calculate_buildable_supply

# Simple cached values with stable hashing 
constraint_colors = ["#FF3333", "#FF9933", "#FFCC33", "#33CC33", "#3366FF", "#9933FF", "#996633"]

# Use session state to cache expensive calculations
if 'site_constraints' not in st.session_state:
    st.session_state.site_constraints = identify_site_constraints(shlaa_gdf, constraint_layers)
    
# Function for cached access to constraint information
def get_constraint_info(sorted_constraints, density):
    """Helper function to get cached supply results by constraint ranking"""
    # Create a cache key from the constraint order and density
    cache_key = f"supply_{'-'.join(sorted_constraints)}_{density}"
    
    if cache_key not in st.session_state:
        # Calculate and cache the results
        results, potential = calculate_buildable_supply(
            shlaa_gdf, 
            st.session_state.site_constraints, 
            sorted_constraints,
            density
        )
        st.session_state[cache_key] = (results, potential)
    
    return st.session_state[cache_key]

# Create tabs for different sections of the app
st.title("📍 Buildable Housing Supply Explorer")

# Initialize session state for configuration
if "density" not in st.session_state:
    st.session_state.density = 50
if "housing_target" not in st.session_state:
    st.session_state.housing_target = 50000
if "selected_constraints" not in st.session_state:
    # Start with just a few constraints selected by default for performance
    st.session_state.selected_constraints = list(constraint_layers.keys())[:3]
if "constraint_order" not in st.session_state:
    st.session_state.constraint_order = list(constraint_layers.keys())
if "show_map" not in st.session_state:
    st.session_state.show_map = True

# Use the cached site constraints
site_constraints = st.session_state.site_constraints

# Main tabs
tab1, tab2, tab3 = st.tabs(["📊 Housing Supply Analysis", "🗺️ Interactive Map", "⚙️ Configuration"])

# Tab 1: Housing Supply Analysis
with tab1:
    # Configuration panel at the top in a compact form
    config_col1, config_col2 = st.columns(2)
    
    with config_col1:
        st.session_state.density = st.number_input(
            "Housing Density (dwellings/ha)", 
            min_value=20, 
            max_value=120, 
            value=st.session_state.density
        )
    
    with config_col2:
        st.session_state.housing_target = st.number_input(
            "Housing Target (dwellings)", 
            min_value=1000, 
            max_value=500000, 
            value=st.session_state.housing_target
        )
    
    # Prioritize Constraints section
    st.subheader("📊 Prioritize Constraints")
    st.markdown("""
    Drag and drop to rank constraints from most to least important to preserve.
    Lower ranked constraints are violated first when necessary to meet housing targets.
    """)
    
    # Unique constraints as list (we don't need all constraints for ranking)
    unique_constraints = list(constraint_layers.keys())
    
    # Drag-and-drop sorting
    sorted_constraints = sort_items(st.session_state.constraint_order, direction="vertical")
    st.session_state.constraint_order = sorted_constraints
    
    # Display rankings in a table
    left_panel, right_panel = st.columns([1, 2])
    
    with left_panel:
        rankings_df = pd.DataFrame({
            "Constraint Type": sorted_constraints,
            "Rank (1 = Most Important)": list(range(1, len(sorted_constraints) + 1))
        })
        
        st.markdown("### 📋 Your Constraint Rankings")
        st.dataframe(rankings_df, use_container_width=True)
    
    # Calculate housing supply based on priorities
    if len(sorted_constraints) > 0:
        # Use our cached calculation function
        supply_results, total_potential = get_constraint_info(
            sorted_constraints,
            st.session_state.density
        )
        
        with right_panel:
            # Display housing target progress
            st.markdown("### 🏠 Housing Supply vs Target")
            
            target_met = total_potential >= st.session_state.housing_target
            available_percent = min(100, round((total_potential / st.session_state.housing_target) * 100, 1))
            
            # Create progress bar
            st.progress(min(1.0, total_potential / st.session_state.housing_target), text=f"{available_percent}% of target")
            
            if target_met:
                st.success(f"✅ Target can be met! {total_potential:,} potential homes vs {st.session_state.housing_target:,} target")
            else:
                st.error(f"❌ Target cannot be met. {total_potential:,} potential homes vs {st.session_state.housing_target:,} target")
                
                # Calculate how many constraints need to be violated
                # Find the first row where cumulative dwellings exceeds the target
                constraints_needed = "All"
                for i, row in supply_results.iterrows():
                    if row['cumulative_dwellings'] >= st.session_state.housing_target:
                        constraints_needed = row['constraints_violated']
                        break
                
                st.info(f"To reach the target, you would need to allow building in areas with: {constraints_needed}")
    
    # Show comprehensive results
    st.subheader("📈 Progressive Housing Supply Analysis")
    
    results_col1, results_col2 = st.columns([2, 1])
    
    with results_col1:
        # Add a bar chart to visualize housing supply by constraint violation
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
            y0=st.session_state.housing_target,
            x1=1,
            y1=st.session_state.housing_target,
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
            y=st.session_state.housing_target,
            text=f"Target: {st.session_state.housing_target:,}",
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
    
    with results_col2:
        # Show staged results table
        st.markdown("### Progressive Supply Details")
        st.dataframe(supply_results, use_container_width=True)
        
        # SHLAA site statistics
        st.markdown("### 📊 SHLAA Site Statistics")
        
        # Calculate total area
        total_area_ha = shlaa_gdf['area_ha'].sum()
        total_potential_dwellings = int(total_area_ha * st.session_state.density)
        
        # Display site statistics
        st.markdown(f"**Total Sites:** {len(shlaa_gdf)}")
        st.markdown(f"**Total Area:** {total_area_ha:.2f} hectares")
        st.markdown(f"**Maximum Capacity:** {total_potential_dwellings:,} homes")
        
        # Display detailed SHLAA statistics in an expander
        with st.expander("Detailed Area Statistics"):
            st.dataframe(shlaa_gdf[["area_m2", "area_ha"]].describe())

# Tab 2: Interactive Map
with tab2:
    st.subheader("🗺️ Buildable Supply Map with Constraints")
    
    # Map configuration options
    map_col1, map_col2, map_col3 = st.columns(3)
    
    with map_col1:
        show_shlaa = st.checkbox("Show SHLAA Sites", value=True)
    
    with map_col2:
        show_constraints = st.checkbox("Show Constraints", value=True)
    
    with map_col3:
        # Select constraint layers to display
        st.session_state.selected_constraints = st.multiselect(
            "Constraint layers to show:",
            list(constraint_layers.keys()),
            default=st.session_state.selected_constraints
        )
    
    # Only generate the map if it should be shown (performance optimization)
    if show_shlaa or show_constraints:
        # Create base map
        m = folium.Map(
            location=[shlaa_gdf.geometry.centroid.y.mean(), shlaa_gdf.geometry.centroid.x.mean()],
            zoom_start=11
        )
        
        if show_shlaa:
            # Cache map data preparation in session state if not already cached
            if 'shlaa_viz' not in st.session_state:
                shlaa_viz = shlaa_gdf.copy()
                shlaa_viz['constraints'] = [', '.join(site_constraints.get(idx, [])) for idx in shlaa_viz.index]
                shlaa_viz['constraint_count'] = [len(site_constraints.get(idx, [])) for idx in shlaa_viz.index]
                st.session_state.shlaa_viz = shlaa_viz
            
            # Use the cached visualization data
            shlaa_viz = st.session_state.shlaa_viz
            
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
        
        if show_constraints:
            # Add constraint layers with pre-defined colors
            colors = {name: col for name, col in zip(
                constraint_layers.keys(),
                constraint_colors[:len(constraint_layers)]
            )}
            
            for name in st.session_state.selected_constraints:
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
        st_folium(m, width=None, height=600, use_container_width=True)

# Tab 3: Configuration
with tab3:
    st.subheader("⚙️ App Configuration")
    
    st.markdown("### Housing Supply Parameters")
    st.session_state.density = st.slider(
        label="Housing Density (dwellings per hectare)",
        min_value=20,
        max_value=120,
        value=st.session_state.density
    )
    
    st.session_state.housing_target = st.slider(
        label="Housing Target (number of dwellings)",
        min_value=1000,
        max_value=500000,
        value=st.session_state.housing_target,
        step=1000
    )
    
    st.markdown("### Constraint Selection")
    st.write("Select which constraints to include in the analysis:")
    
    # Create multiple columns for selecting constraints
    constraint_cols = st.columns(3)
    all_constraints = list(constraint_layers.keys())
    
    # Show all constraint options as checkboxes
    constraint_states = {}
    for i, constraint in enumerate(all_constraints):
        col_idx = i % 3
        with constraint_cols[col_idx]:
            constraint_states[constraint] = st.checkbox(
                constraint, 
                value=constraint in st.session_state.selected_constraints
            )
    
    # Update selected constraints based on checkboxes
    st.session_state.selected_constraints = [
        constraint for constraint, selected in constraint_states.items() if selected
    ]
    
    # Add button to select/deselect all
    select_col1, select_col2 = st.columns(2)
    with select_col1:
        if st.button("Select All Constraints"):
            st.session_state.selected_constraints = all_constraints
            st.rerun()
    
    with select_col2:
        if st.button("Deselect All Constraints"):
            st.session_state.selected_constraints = []
            st.rerun()
    
    # Information about app performance
    st.markdown("### 💡 Performance Tips")
    st.info("""
    - The map is now separated from the analysis panels and won't recompute when you change settings
    - Reducing the number of selected constraints improves map loading speed
    - The app uses caching to avoid repeating expensive calculations
    - Use the Configuration tab to adjust settings without triggering recalculations
    """)