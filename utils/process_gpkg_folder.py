#!/usr/bin/env python3
"""
GPKG to GeoJSON Converter

This script converts all GeoPackage (.gpkg) files in a directory to GeoJSON format,
with the option to unify layers with the same name across different files.
"""

import os
import sys
import argparse
import geopandas as gpd
from pathlib import Path
import pandas as pd
from fiona import listlayers
import json
from datetime import datetime
import time

def list_gpkg_files(directory):
    """List all GPKG files in the specified directory."""
    path = Path(directory)
    gpkg_files = list(path.glob("**/*.gpkg"))
    return gpkg_files

def list_all_layers(gpkg_files):
    """List all layers from all GPKG files with their source file."""
    all_layers = []
    
    for gpkg_file in gpkg_files:
        try:
            layers = listlayers(gpkg_file)
            for layer in layers:
                all_layers.append((str(gpkg_file), layer))
        except Exception as e:
            print(f"Error listing layers in {gpkg_file}: {str(e)}")
    
    return all_layers

def group_layers_by_name(all_layers):
    """Group layers by name across different files."""
    layer_groups = {}
    
    for gpkg_file, layer_name in all_layers:
        if layer_name not in layer_groups:
            layer_groups[layer_name] = []
        layer_groups[layer_name].append(gpkg_file)
    
    return layer_groups

def prepare_geodataframe(gdf):
    """Prepare a GeoDataFrame for conversion to GeoJSON."""
    
    # Make a copy to avoid modifying the original
    gdf = gdf.copy()
    
    # Convert datetime columns to strings to avoid JSON serialization issues
    for col in gdf.columns:
        if pd.api.types.is_datetime64_any_dtype(gdf[col]):
            gdf[col] = gdf[col].astype(str)
    
    # Remove columns that are exactly the same for all rows (constants)
    for col in gdf.columns:
        if col != gdf.geometry.name and len(gdf[col].unique()) == 1:
            # Keep constant columns that might be useful metadata
            if not (isinstance(gdf[col].iloc[0], str) and len(gdf[col].iloc[0]) > 100):
                continue
    
    # Ensure the geometry is valid
    if hasattr(gdf, 'geometry'):
        gdf = gdf[~gdf.geometry.isna()]
        # Try to fix any invalid geometries
        try:
            gdf.geometry = gdf.geometry.make_valid()
        except:
            # make_valid() might not be available in older versions
            pass
    
    return gdf

def convert_single_layer(gpkg_path, layer_name, output_dir, counter=None):
    """Convert a single layer from a GPKG file to GeoJSON."""
    try:
        # Read the layer
        gdf = gpd.read_file(gpkg_path, layer=layer_name)
        
        if len(gdf) == 0:
            print(f"  - Skipping empty layer: {layer_name}")
            return None, 0
        
        # Prepare the GeoDataFrame
        gdf = prepare_geodataframe(gdf)
        
        # Define output path
        if counter is not None:
            output_filename = f"{layer_name}_{counter}.geojson"
        else:
            output_filename = f"{layer_name}.geojson"
        output_path = Path(output_dir) / output_filename
        
        # Convert to WGS84 (EPSG:4326) if needed
        if gdf.crs and str(gdf.crs) != "EPSG:4326":
            print(f"  - Converting from {gdf.crs} to WGS84 (EPSG:4326)")
            gdf = gdf.to_crs("EPSG:4326")
        
        # Save to GeoJSON
        gdf.to_file(output_path, driver='GeoJSON')
        print(f"  - Exported to: {output_path} ({len(gdf)} features)")
        
        return output_path, len(gdf)
    
    except Exception as e:
        print(f"  - Error converting layer '{layer_name}' from '{gpkg_path}': {str(e)}")
        return None, 0

def unify_layers(gpkg_files, layer_name, output_dir):
    """Unify the same layer from multiple GPKG files into a single GeoJSON."""
    combined_gdf = None
    feature_count = 0
    
    print(f"Unifying layer '{layer_name}' from {len(gpkg_files)} files")
    
    for gpkg_file in gpkg_files:
        try:
            # Read the layer
            gdf = gpd.read_file(gpkg_file, layer=layer_name)
            
            if len(gdf) == 0:
                continue
            
            # Prepare the GeoDataFrame
            gdf = prepare_geodataframe(gdf)
            
            # Add a source column
            gdf['source_file'] = os.path.basename(gpkg_file)
            
            # Convert to WGS84 if needed
            if gdf.crs and str(gdf.crs) != "EPSG:4326":
                gdf = gdf.to_crs("EPSG:4326")
            
            # Append to combined GeoDataFrame
            if combined_gdf is None:
                combined_gdf = gdf
            else:
                # Find common columns to avoid errors when combining dataframes
                common_columns = set(combined_gdf.columns) & set(gdf.columns)
                # Make sure 'geometry' is included
                if 'geometry' not in common_columns and combined_gdf.geometry.name == gdf.geometry.name:
                    common_columns.add(combined_gdf.geometry.name)
                
                # Add the features with common columns
                combined_gdf = pd.concat([combined_gdf, gdf[list(common_columns)]], ignore_index=True)
            
            feature_count += len(gdf)
            print(f"  - Added {len(gdf)} features from {os.path.basename(gpkg_file)}")
            
        except Exception as e:
            print(f"  - Error processing '{layer_name}' from '{gpkg_file}': {str(e)}")
    
    if combined_gdf is not None and len(combined_gdf) > 0:
        # Define output path
        output_path = Path(output_dir) / f"{layer_name}_unified.geojson"
        
        # Save to GeoJSON
        combined_gdf.to_file(output_path, driver='GeoJSON')
        print(f"  - Unified layer exported to: {output_path} ({len(combined_gdf)} features)")
        
        return output_path, feature_count
    else:
        print(f"  - No valid features found for layer '{layer_name}'")
        return None, 0

def create_summary(conversion_results, output_dir):
    """Create a summary JSON file of the conversion results."""
    summary = {
        "conversion_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_files_processed": len(conversion_results["files"]),
        "total_layers_processed": len(conversion_results["layers"]),
        "total_features_converted": conversion_results["total_features"],
        "unified_layers": conversion_results["unified_layers"],
        "individual_layers": conversion_results["individual_layers"],
        "files": conversion_results["files"],
        "layers": conversion_results["layers"]
    }
    
    summary_path = Path(output_dir) / "conversion_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nSummary saved to: {summary_path}")

def convert_gpkg_to_geojson(input_dir, output_dir, unify=False):
    """
    Convert all GPKG files in a directory to GeoJSON format.
    
    Args:
        input_dir (str): Directory containing GPKG files
        output_dir (str): Directory for output GeoJSON files
        unify (bool): Whether to unify layers with the same name
        
    Returns:
        dict: Conversion results summary
    """
    start_time = time.time()
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # List all GPKG files
    gpkg_files = list_gpkg_files(input_dir)
    if not gpkg_files:
        print(f"No GPKG files found in {input_dir}")
        return
    
    print(f"Found {len(gpkg_files)} GPKG files")
    
    # List all layers from all files
    all_layers = list_all_layers(gpkg_files)
    print(f"Found {len(all_layers)} layers in total")
    
    # Initialize results dictionary
    conversion_results = {
        "files": {},
        "layers": {},
        "total_features": 0,
        "unified_layers": 0,
        "individual_layers": 0
    }
    
    # Process files
    if unify:
        # Group layers by name
        layer_groups = group_layers_by_name(all_layers)
        print(f"Found {len(layer_groups)} unique layer names")
        
        # Process each layer group
        for layer_name, layer_files in layer_groups.items():
            print(f"\nProcessing layer: {layer_name} (found in {len(layer_files)} files)")
            
            if len(layer_files) > 1:
                # Unify this layer from multiple files
                output_path, feature_count = unify_layers(layer_files, layer_name, output_dir)
                
                if output_path:
                    conversion_results["unified_layers"] += 1
                    conversion_results["total_features"] += feature_count
                    conversion_results["layers"][layer_name] = {
                        "unified": True,
                        "feature_count": feature_count,
                        "source_files": layer_files,
                        "output_path": str(output_path)
                    }
            else:
                # Just convert this single layer
                gpkg_path = layer_files[0]
                output_path, feature_count = convert_single_layer(gpkg_path, layer_name, output_dir)
                
                if output_path:
                    conversion_results["individual_layers"] += 1
                    conversion_results["total_features"] += feature_count
                    conversion_results["layers"][layer_name] = {
                        "unified": False,
                        "feature_count": feature_count,
                        "source_file": gpkg_path,
                        "output_path": str(output_path)
                    }
                    
                    # Update file statistics
                    if gpkg_path not in conversion_results["files"]:
                        conversion_results["files"][gpkg_path] = {
                            "layers_processed": 1,
                            "features_converted": feature_count
                        }
                    else:
                        conversion_results["files"][gpkg_path]["layers_processed"] += 1
                        conversion_results["files"][gpkg_path]["features_converted"] += feature_count
    else:
        # Process each file and layer individually
        for i, gpkg_file in enumerate(gpkg_files):
            print(f"\nProcessing file {i+1}/{len(gpkg_files)}: {gpkg_file}")
            
            # Initialize file statistics
            conversion_results["files"][str(gpkg_file)] = {
                "layers_processed": 0,
                "features_converted": 0
            }
            
            try:
                # List layers in this file
                layers = listlayers(gpkg_file)
                print(f"Found {len(layers)} layers in {gpkg_file.name}")
                
                # Process each layer
                for j, layer_name in enumerate(layers):
                    print(f"  Processing layer {j+1}/{len(layers)}: {layer_name}")
                    
                    # Convert layer to GeoJSON
                    output_path, feature_count = convert_single_layer(
                        gpkg_file, layer_name, output_dir, counter=i
                    )
                    
                    if output_path:
                        conversion_results["individual_layers"] += 1
                        conversion_results["total_features"] += feature_count
                        conversion_results["layers"][f"{layer_name}_{i}"] = {
                            "unified": False,
                            "feature_count": feature_count,
                            "source_file": str(gpkg_file),
                            "output_path": str(output_path)
                        }
                        
                        # Update file statistics
                        conversion_results["files"][str(gpkg_file)]["layers_processed"] += 1
                        conversion_results["files"][str(gpkg_file)]["features_converted"] += feature_count
                        
            except Exception as e:
                print(f"Error processing file {gpkg_file}: {str(e)}")
    
    # Calculate elapsed time
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"\nConversion completed in {elapsed_time:.2f} seconds")
    print(f"Converted {conversion_results['total_features']} features from {len(gpkg_files)} files")
    print(f"Created {conversion_results['unified_layers']} unified layers and {conversion_results['individual_layers']} individual layers")
    
    # Create summary
    create_summary(conversion_results, output_dir)
    
    return conversion_results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert GPKG files to GeoJSON format')
    parser.add_argument('input_dir', help='Directory containing GPKG files')
    parser.add_argument('--output_dir', '-o', help='Output directory for GeoJSON files')
    parser.add_argument('--unify', '-u', action='store_true', 
                        help='Unify layers with the same name across different files')
    
    args = parser.parse_args()
    
    # Set default output directory if not specified
    if not args.output_dir:
        args.output_dir = os.path.join(args.input_dir, 'geojson_output')
    
    # Check if input directory exists
    if not os.path.isdir(args.input_dir):
        print(f"Error: Input directory '{args.input_dir}' does not exist.")
        sys.exit(1)
    
    # Run the conversion
    convert_gpkg_to_geojson(args.input_dir, args.output_dir, args.unify)