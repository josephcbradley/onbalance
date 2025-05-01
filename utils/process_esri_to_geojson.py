import os
import geopandas as gpd
from pathlib import Path

def convert_shapefiles_to_geojson(input_dir, output_dir=None, to_wgs84=True):
    """
    Convert all shapefiles in a directory to GeoJSON format.
    
    Args:
        input_dir (str): Path to directory containing shapefiles
        output_dir (str, optional): Path to output directory. If None, uses input_dir
        to_wgs84 (bool): Whether to convert coordinates to WGS84 (EPSG:4326)
        
    Returns:
        list: Paths to the created GeoJSON files
    """
    # Set up input and output directories
    input_path = Path(input_dir)
    if output_dir is None:
        output_path = input_path
    else:
        output_path = Path(output_dir)
        os.makedirs(output_path, exist_ok=True)
    
    # Find all shapefiles in the directory
    shapefiles = list(input_path.glob("**/*.shp"))
    
    if not shapefiles:
        print(f"No shapefiles found in {input_dir}")
        return []
    
    print(f"Found {len(shapefiles)} shapefiles to convert")
    converted_files = []
    
    # Process each shapefile
    for i, shp_file in enumerate(shapefiles):
        print(f"\nProcessing file {i+1}/{len(shapefiles)}: {shp_file.name}")
        
        try:
            # Read the shapefile
            gdf = gpd.read_file(shp_file)
            
            # Print basic info
            print(f"  Features: {len(gdf)}")
            print(f"  Geometry types: {gdf.geometry.geom_type.unique().tolist()}")
            print(f"  Original CRS: {gdf.crs}")
            
            # Convert to WGS84 if requested and needed
            if to_wgs84 and gdf.crs and str(gdf.crs) != "EPSG:4326":
                print(f"  Converting from {gdf.crs} to WGS84 (EPSG:4326)")
                gdf = gdf.to_crs("EPSG:4326")
            
            # Generate output filename
            rel_path = shp_file.relative_to(input_path) if shp_file.is_relative_to(input_path) else shp_file.name
            output_file = output_path / rel_path.with_suffix('.geojson')
            
            # Create parent directories if they don't exist
            os.makedirs(output_file.parent, exist_ok=True)
            
            # Save to GeoJSON
            gdf.to_file(output_file, driver='GeoJSON')
            print(f"  Saved to: {output_file}")
            
            converted_files.append(str(output_file))
            
        except Exception as e:
            print(f"  Error processing {shp_file}: {str(e)}")
    
    print(f"\nConversion complete. Converted {len(converted_files)} of {len(shapefiles)} files.")
    return converted_files

def process_london_shlaa(shlaa_dir, output_dir=None):
    """
    Process the London SHLAA shapefiles specifically.
    
    Args:
        shlaa_dir (str): Directory containing SHLAA shapefiles
        output_dir (str, optional): Directory for output files
        
    Returns:
        list: Paths to created GeoJSON files
    """
    print("=== Processing London SHLAA 2017 Site Boundary Polygons ===")
    
    # Convert shapefiles to GeoJSON
    geojson_files = convert_shapefiles_to_geojson(shlaa_dir, output_dir)
    
    # Additional SHLAA-specific processing could be added here
    
    return geojson_files

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert London SHLAA shapefiles to GeoJSON')
    parser.add_argument('input_dir', help='Directory containing SHLAA shapefiles')
    parser.add_argument('--output_dir', '-o', help='Output directory for GeoJSON files')
    parser.add_argument('--keep_crs', action='store_true', 
                        help='Keep original coordinate reference system (default is to convert to WGS84)')
    
    args = parser.parse_args()
    
    # Run the conversion
    process_london_shlaa(args.input_dir, args.output_dir)