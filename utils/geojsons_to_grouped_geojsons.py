#!/usr/bin/env python3
"""
GeoJSON Unifier with Polygon Union

This script takes a grouping JSON file that defines how GeoJSON files should be grouped
and creates unified GeoJSON files for each group. For polygon data, it dissolves overlapping
areas to create a clean union of all polygons.
"""

import os
import json
import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from pathlib import Path
import time
import argparse

def create_directory(directory):
    """Create directory if it doesn't exist."""
    os.makedirs(directory, exist_ok=True)

def load_grouping_json(json_path):
    """Load the grouping JSON file."""
    with open(json_path, 'r') as f:
        return json.load(f)

def normalize_column_names(gdf):
    """Normalize column names to lowercase and replace spaces with underscores."""
    gdf.columns = [col.lower().replace(' ', '_') for col in gdf.columns]
    return gdf

def union_polygons(gdf, tolerance):
    """
    Create a union of overlapping polygons and simplify the result.
    
    Args:
        gdf (GeoDataFrame): GeoDataFrame containing polygon geometries
        tolerance (float): Simplification tolerance
    
    Returns:
        GeoDataFrame: New GeoDataFrame with unified polygons
    """
    # Check if we're dealing with polygons
    if not all(isinstance(geom, (Polygon, MultiPolygon)) for geom in gdf.geometry):
        # If not all geometries are polygons, return the original GeoDataFrame
        print("  Not all geometries are polygons, skipping union operation")
        return gdf
    
    print("  Performing union operation on overlapping polygons...")
    
    # Get the common columns (excluding geometry and source_file)
    cols_to_keep = [col for col in gdf.columns if col not in ['geometry', 'source_file']]
    
    # Create attribute dictionary for each feature
    attributes = []
    for idx, row in gdf.iterrows():
        attr_dict = {col: row[col] for col in cols_to_keep if col in row}
        attributes.append(attr_dict)
    
    # Perform the union of all geometries
    unified_geom = unary_union(gdf.geometry)
    
    # Simplify the unified geometry
    if tolerance > 0:
        print(f"  Simplifying geometry with tolerance: {tolerance}")
        unified_geom = unified_geom.simplify(tolerance, preserve_topology=True)
    
    # Create a new GeoDataFrame with the unified geometry
    if isinstance(unified_geom, (Polygon, MultiPolygon)):
        # Single unified geometry
        new_gdf = gpd.GeoDataFrame({'geometry': [unified_geom]}, crs=gdf.crs)
        
        # Add the most common value for each attribute across all features
        for col in cols_to_keep:
            try:
                # Use the most frequent value
                value_counts = gdf[col].value_counts()
                if not value_counts.empty:
                    most_common = value_counts.index[0]
                    new_gdf[col] = most_common
            except:
                pass
    else:
        # Multiple geometries in the result
        new_geoms = []
        if hasattr(unified_geom, 'geoms'):
            new_geoms = list(unified_geom.geoms)
        else:
            new_geoms = [unified_geom]
        
        new_gdf = gpd.GeoDataFrame({'geometry': new_geoms}, crs=gdf.crs)
        
        # Add the attributes
        for col in cols_to_keep:
            try:
                # Use the most frequent value
                value_counts = gdf[col].value_counts()
                if not value_counts.empty:
                    most_common = value_counts.index[0]
                    new_gdf[col] = most_common
            except:
                pass
    
    # Add source information
    sources = set(gdf['source_file'])
    new_gdf['source_file'] = ', '.join(sorted(sources))
    
    print(f"  Union complete: {len(gdf)} polygons reduced to {len(new_gdf)} unified geometries")
    return new_gdf

def identify_geometry_types(gdfs):
    """
    Identify the geometry types present in the GeoDataFrames.
    Returns a dictionary with counts of each geometry type.
    """
    geometry_types = {}
    
    for gdf in gdfs:
        for geom in gdf.geometry:
            if geom is None:
                continue
                
            geom_type = geom.geom_type
            if geom_type in geometry_types:
                geometry_types[geom_type] += 1
            else:
                geometry_types[geom_type] = 1
    
    return geometry_types

def group_by_geometry_type(gdfs):
    """
    Group GeoDataFrames by geometry type.
    Returns a dictionary with geometry type as key and list of GeoDataFrames as value.
    """
    grouped = {}
    
    for gdf in gdfs:
        # Skip empty GeoDataFrames
        if len(gdf) == 0:
            continue
            
        # Group by first geometry's type (assumes homogeneous geometries in each GDF)
        first_geom = gdf.geometry.iloc[0]
        if first_geom is None:
            continue
            
        geom_type = first_geom.geom_type
        
        if geom_type in grouped:
            grouped[geom_type].append(gdf)
        else:
            grouped[geom_type] = [gdf]
    
    return grouped

def unify_group(group_name, file_paths, output_dir, crs="EPSG:4326", simplify_tolerance=0.1):
    """
    Unify a group of GeoJSON files into a single file.
    For polygons, performs a union operation to avoid double-counting overlapping areas.
    
    Args:
        group_name (str): Name of the group
        file_paths (list): List of file paths to unify
        output_dir (str): Output directory path
        crs (str): Coordinate reference system to use for the unified file
        simplify_tolerance (float): Tolerance for simplifying geometries
        
    Returns:
        dict: Dictionary with information about the unified file
    """
    print(f"Processing group: {group_name} ({len(file_paths)} files)")
    
    if not file_paths:
        print(f"  No files found for group: {group_name}")
        return None
    
    # Create a standardized output filename
    output_filename = f"{group_name.replace(' ', '_')}_unified.geojson"
    output_path = os.path.join(output_dir, output_filename)
    
    # Skip if there's only one file and it's already a unified file
    if len(file_paths) == 1 and os.path.basename(file_paths[0]).endswith('_unified.geojson'):
        print(f"  Only one unified file in group, copying: {file_paths[0]}")
        # Just copy the file to the output directory with the standardized name
        source_gdf = gpd.read_file(file_paths[0])
        
        # If it contains polygons, still perform the union operation
        if all(isinstance(geom, (Polygon, MultiPolygon)) for geom in source_gdf.geometry):
            print("  Performing union on single file to resolve any internal overlaps")
            source_gdf = union_polygons(source_gdf, simplify_tolerance)
            
        source_gdf.to_file(output_path, driver='GeoJSON')
        return {
            "group_name": group_name,
            "output_path": output_path,
            "input_files": 1,
            "feature_count": len(source_gdf)
        }
    
    # Load all the GeoDataFrames
    gdfs = []
    file_count = 0
    
    for file_path in file_paths:
        try:
            print(f"  Loading file {file_paths.index(file_path)+1}/{len(file_paths)}: {os.path.basename(file_path)}")
            gdf = gpd.read_file(file_path)
            
            if len(gdf) > 0:
                # Add source information
                gdf['source_file'] = os.path.basename(file_path)
                
                # Convert to common CRS
                if gdf.crs and str(gdf.crs) != crs:
                    print(f"  Converting from {gdf.crs} to {crs}")
                    gdf = gdf.to_crs(crs)
                
                # Normalize column names
                gdf = normalize_column_names(gdf)
                
                gdfs.append(gdf)
                file_count += 1
            else:
                print(f"  Skipping empty file: {os.path.basename(file_path)}")
        except Exception as e:
            print(f"  Error loading {file_path}: {str(e)}")
    
    if not gdfs:
        print(f"  No valid data found for group: {group_name}")
        return None
    
    # Identify geometry types present in the data
    geometry_types = identify_geometry_types(gdfs)
    print(f"  Geometry types found: {geometry_types}")
    
    # If we have multiple geometry types, process each type separately
    if len(geometry_types) > 1:
        print(f"  Multiple geometry types detected, processing each type separately")
        grouped_by_type = group_by_geometry_type(gdfs)
        
        combined_results = []
        
        for geom_type, type_gdfs in grouped_by_type.items():
            print(f"  Processing {geom_type} geometries ({sum(len(gdf) for gdf in type_gdfs)} features)")
            
            # Combine the GeoDataFrames of this type
            try:
                type_combined = pd.concat(type_gdfs, ignore_index=True)
                
                # For polygons, perform union operation
                if geom_type in ['Polygon', 'MultiPolygon']:
                    type_combined = union_polygons(type_combined, simplify_tolerance)
                
                combined_results.append(type_combined)
            except Exception as e:
                print(f"  Error processing {geom_type} geometries: {str(e)}")
        
        # Combine all results
        try:
            combined_gdf = pd.concat(combined_results, ignore_index=True)
        except Exception as e:
            print(f"  Error combining geometry types: {str(e)}")
            return None
    else:
        # We have only one geometry type, proceed with regular combining
        try:
            combined_gdf = pd.concat(gdfs, ignore_index=True)
            
            # If we're dealing with polygons, perform union
            if 'Polygon' in geometry_types or 'MultiPolygon' in geometry_types:
                combined_gdf = union_polygons(combined_gdf, simplify_tolerance)
        except Exception as e:
            print(f"  Error unifying group {group_name}: {str(e)}")
            return None
    
    # Save to file
    print(f"  Saving unified file with {len(combined_gdf)} features to {output_path}")
    combined_gdf.to_file(output_path, driver='GeoJSON')
    
    return {
        "group_name": group_name,
        "output_path": output_path,
        "input_files": file_count,
        "feature_count": len(combined_gdf),
        "geometry_types": list(geometry_types.keys())
    }

def main():
    """Main function to execute the script."""
    parser = argparse.ArgumentParser(description='Unify GeoJSON files based on a grouping JSON')
    parser.add_argument('grouping_json', help='JSON file with grouping definitions')
    parser.add_argument('--output_dir', '-o', default='unified_geojson', help='Output directory for unified files')
    parser.add_argument('--crs', default='EPSG:4326', help='Coordinate reference system for output files')
    parser.add_argument('--simplify', '-s', type=float, default=0.3, 
                        help='Tolerance for simplifying geometries (0 to disable)')
    
    args = parser.parse_args()
    
    start_time = time.time()
    
    # Load the grouping JSON
    grouping_data = load_grouping_json(args.grouping_json)
    
    # Create output directory
    create_directory(args.output_dir)
    
    # Initialize results
    results = {
        "unified_groups": [],
        "skipped_groups": [],
        "total_input_files": 0,
        "total_output_files": 0,
        "total_features": 0
    }
    
    # Process each group
    groups = grouping_data.get('groups', {})
    total_groups = len(groups)
    processed_groups = 0
    
    for group_name, file_paths in groups.items():
        processed_groups += 1
        print(f"Processing group {processed_groups}/{total_groups}: {group_name}")
        
        result = unify_group(group_name, file_paths, args.output_dir, args.crs, args.simplify)
        
        if result:
            results["unified_groups"].append(result)
            results["total_input_files"] += result["input_files"]
            results["total_output_files"] += 1
            results["total_features"] += result["feature_count"]
        else:
            results["skipped_groups"].append(group_name)
    
    # Save results to a summary file
    summary = {
        "unification_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "input_grouping_file": args.grouping_json,
        "output_directory": args.output_dir,
        "simplification_tolerance": args.simplify,
        "total_groups_processed": total_groups,
        "total_groups_unified": len(results["unified_groups"]),
        "total_groups_skipped": len(results["skipped_groups"]),
        "total_input_files_processed": results["total_input_files"],
        "total_output_files_created": results["total_output_files"],
        "total_features_unified": results["total_features"],
        "unified_groups": results["unified_groups"],
        "skipped_groups": results["skipped_groups"]
    }
    
    summary_path = os.path.join(args.output_dir, "unification_summary.json")
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Print final stats
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    print("\n=== Unification Summary ===")
    print(f"Total groups processed: {total_groups}")
    print(f"Groups unified: {len(results['unified_groups'])}")
    print(f"Groups skipped: {len(results['skipped_groups'])}")
    print(f"Total input files processed: {results['total_input_files']}")
    print(f"Total output files created: {results['total_output_files']}")
    print(f"Total features in unified files: {results['total_features']}")
    print(f"Time taken: {elapsed_time:.2f} seconds")
    print(f"Summary saved to: {summary_path}")

if __name__ == "__main__":
    main()