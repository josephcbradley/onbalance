#!/usr/bin/env python3
"""
GeoJSON Interactive Map Viewer

A simple tool to view and select from multiple GeoJSON files.
"""

import os
import sys
import json
import geopandas as gpd
import pandas as pd
import folium
from folium.plugins import MeasureControl, Fullscreen, MarkerCluster, Search
from pathlib import Path
import webbrowser
import argparse
import random
import colorsys
import tempfile
from datetime import datetime, date

# Custom JSON encoder to handle timestamps and dates
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date, pd.Timestamp)):
            return obj.isoformat()
        return super().default(obj)

def get_geojson_files(directory):
    """Get all GeoJSON files in a directory."""
    geojson_files = list(Path(directory).glob("**/*.geojson"))
    # Filter out summary files
    geojson_files = [f for f in geojson_files if not f.name.startswith("unification_summary")]
    return sorted(geojson_files)

def get_random_colors(n):
    """Generate n visually distinct colors."""
    colors = []
    for i in range(n):
        hue = i / n
        saturation = 0.7 + random.random() * 0.3
        lightness = 0.4 + random.random() * 0.2
        
        r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
        color = f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'
        colors.append(color)
    
    return colors

def simplify_geometries(gdf, tolerance=0.001):
    """Simplify geometries to improve performance."""
    try:
        return gdf.geometry.simplify(tolerance=tolerance)
    except:
        return gdf.geometry

def preprocess_dataframe(gdf):
    """Convert problematic data types for JSON serialization"""
    for col in gdf.columns:
        if col != 'geometry':
            # Convert timestamp columns to strings
            if pd.api.types.is_datetime64_any_dtype(gdf[col]):
                gdf[col] = gdf[col].astype(str)
    return gdf

def create_interactive_map(geojson_files, selected_files=None, output_file=None):
    """
    Create an interactive map with selected GeoJSON files.
    
    Args:
        geojson_files (list): List of all GeoJSON file paths
        selected_files (list): List of indices or names of files to display
        output_file (str): Path to save the HTML output
        
    Returns:
        str: Path to the created HTML file
    """
    print("Creating interactive map...")
    
    # If no files are selected, show a list for selection
    if selected_files is None:
        print("\nAvailable GeoJSON files:")
        for i, file in enumerate(geojson_files):
            print(f"[{i}] {file.name}")
        
        selection = input("\nEnter file numbers to display (comma-separated), or 'all': ")
        if selection.lower() == 'all':
            selected_files = list(range(len(geojson_files)))
        else:
            try:
                selected_files = [int(idx.strip()) for idx in selection.split(',') if idx.strip()]
            except ValueError:
                print("Invalid selection. Please enter numbers separated by commas.")
                return None
    
    # Filter to selected files only
    if isinstance(selected_files[0], int):
        selected_paths = [geojson_files[idx] for idx in selected_files if 0 <= idx < len(geojson_files)]
    else:
        # Assume selected_files contains filenames
        selected_paths = [f for f in geojson_files if f.name in selected_files or str(f) in selected_files]
    
    if not selected_paths:
        print("No valid files selected.")
        return None
    
    print(f"\nLoading {len(selected_paths)} selected files...")
    
    # Generate colors for each layer
    colors = get_random_colors(len(selected_paths))
    
    # Create the map centered on London
    m = folium.Map(
        location=[51.509865, -0.118092],  # London center
        zoom_start=10,
        tiles='CartoDB positron',
        width='100%',
        height='100%'
    )
    
    # Add base layers
    folium.TileLayer('CartoDB positron', name='Light Map').add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='Dark Map').add_to(m)
    folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite'
    ).add_to(m)
    
    # Create a custom HTML for the map title and legend
    title_html = '''
        <div style="position: fixed; 
                    top: 10px; left: 50%; transform: translateX(-50%);
                    z-index: 9999; background-color: white; 
                    padding: 10px; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.2);
                    font-family: Arial, sans-serif; font-size: 16px; font-weight: bold;">
            London GeoJSON Viewer
        </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Add selected GeoJSON files to the map
    bounds = None
    for i, file_path in enumerate(selected_paths):
        try:
            print(f"Adding layer: {file_path.name}")
            
            # Read the GeoJSON file
            gdf = gpd.read_file(file_path)
            
            # Skip empty files
            if len(gdf) == 0:
                print(f"  Skipping empty file: {file_path.name}")
                continue
            
            # Update bounds to include this layer
            if bounds is None:
                bounds = gdf.total_bounds
            else:
                layer_bounds = gdf.total_bounds
                bounds = [
                    min(bounds[0], layer_bounds[0]),
                    min(bounds[1], layer_bounds[1]),
                    max(bounds[2], layer_bounds[2]),
                    max(bounds[3], layer_bounds[3])
                ]
            
            # Get a color for this layer
            color = colors[i % len(colors)]
            
            # Try to simplify geometries for better performance if there are many features
            if len(gdf) > 100:
                print(f"  Simplifying geometries for better performance ({len(gdf)} features)")
                try:
                    gdf.geometry = simplify_geometries(gdf, tolerance=0.0005)
                except Exception as e:
                    print(f"  Simplification failed: {str(e)}")
            
            # Preprocess the dataframe to handle timestamps and other problematic types
            gdf = preprocess_dataframe(gdf)
            
            # Create a feature group for this layer
            feature_group = folium.FeatureGroup(name=file_path.name)
            
            # Style function for the GeoJSON
            style_function = lambda x: {
                'fillColor': color,
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0.5
            }
            
            # Create tooltip columns
            tooltip_fields = []
            for col in gdf.columns[:5]:  # Use first 5 columns only
                if col != 'geometry' and isinstance(gdf[col].iloc[0], (str, int, float)):
                    tooltip_fields.append(col)
            
            # Create popup function
            popup_function = lambda feature: folium.Popup(
                create_popup_content(feature['properties']),
                max_width=300
            )
            
            # Add the GeoJSON to the map with custom JSON encoder
            gjson = folium.GeoJson(
                data=json.loads(gdf.to_json(cls=CustomJSONEncoder)),
                name=file_path.name,
                style_function=style_function,
                popup=popup_function,
                tooltip=folium.GeoJsonTooltip(fields=tooltip_fields, labels=True) if tooltip_fields else None
            )
            
            # Add to feature group
            feature_group.add_child(gjson)
            
            # Try to add search if there are good fields for it
            search_fields = ['name', 'id', 'site_id', 'site_name', 'title', 'sitename']
            search_column = None
            
            for field in search_fields:
                matching_cols = [col for col in gdf.columns if field.lower() in col.lower() and 
                                pd.api.types.is_string_dtype(gdf[col])]
                if matching_cols:
                    search_column = matching_cols[0]
                    break
            
            if search_column:
                print(f"  Adding search for field: {search_column}")
                Search(
                    layer=gjson,
                    geom_type="Polygon",
                    placeholder=f"Search {search_column}",
                    collapsed=True,
                    search_label=search_column
                ).add_to(m)
            
            # Add the feature group to the map
            m.add_child(feature_group)
            
        except Exception as e:
            print(f"Error loading {file_path}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Set the map view to fit all layers
    if bounds is not None:
        m.fit_bounds([
            [bounds[1], bounds[0]],  # SW corner
            [bounds[3], bounds[2]]   # NE corner
        ])
    
    # Add controls
    folium.LayerControl(collapsed=False).add_to(m)
    MeasureControl(position='bottomleft').add_to(m)
    Fullscreen().add_to(m)
    
    # If no output file specified, create a temporary file
    if output_file is None:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
        output_file = tmp.name
        tmp.close()
    
    # Save the map to HTML file
    m.save(output_file)
    print(f"Map saved to: {output_file}")
    
    return output_file

def create_popup_content(properties):
    """Create HTML content for popups."""
    # Filter out irrelevant or redundant properties
    exclude_keys = ['geometry', 'geom', 'shape_leng', 'shape_area']
    
    html = "<div style='max-height:200px; overflow:auto; width:300px;'>"
    html += "<table style='width:100%; border-collapse:collapse;'>"
    
    for key, value in properties.items():
        if key.lower() not in [k.lower() for k in exclude_keys] and value is not None:
            html += f"<tr><th style='text-align:left; padding:2px 5px; border-bottom:1px solid #eee;'>{key}</th>"
            html += f"<td style='text-align:left; padding:2px 5px; border-bottom:1px solid #eee;'>{value}</td></tr>"
    
    html += "</table></div>"
    return html

def main():
    parser = argparse.ArgumentParser(description='Interactive GeoJSON Map Viewer')
    parser.add_argument('directory', help='Directory containing GeoJSON files')
    parser.add_argument('--output', '-o', help='Output HTML file')
    parser.add_argument('--files', '-f', nargs='+', help='Specific files to display (names or indices)')
    parser.add_argument('--no_browser', action='store_true', help='Do not open browser automatically')
    
    args = parser.parse_args()
    
    # Check if directory exists
    if not os.path.isdir(args.directory):
        print(f"Error: Directory '{args.directory}' does not exist.")
        return 1
    
    # Get all GeoJSON files
    geojson_files = get_geojson_files(args.directory)
    
    if not geojson_files:
        print(f"No GeoJSON files found in {args.directory}")
        return 1
    
    print(f"Found {len(geojson_files)} GeoJSON files in {args.directory}")
    
    # Create interactive map
    output_file = create_interactive_map(geojson_files, args.files, args.output)
    
    if output_file and not args.no_browser:
        webbrowser.open('file://' + os.path.abspath(output_file))
    
    return 0

if __name__ == "__main__":
    sys.exit(main())