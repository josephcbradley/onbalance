import geopandas as gpd
import matplotlib.pyplot as plt
import os
from fiona import listlayers
import json

def explore_and_convert_gpkg(gpkg_path, export_geojson=True):
    # List all layers in the geopackage
    layers = listlayers(gpkg_path)
    print(f"Layers in the GeoPackage: {layers}")
    
    # Read the first layer
    first_layer = layers[0]
    print(f"\nReading first layer: {first_layer}")
    
    # Open the layer with geopandas
    gdf = gpd.read_file(gpkg_path, layer=first_layer)
    
    # Print basic info about the layer
    print("\nBasic information:")
    print(f"Number of features: {len(gdf)}")
    print(f"Geometry type: {gdf.geometry.geom_type.unique()}")
    print(f"CRS: {gdf.crs}")
    
    # Print the first few rows
    print("\nFirst 5 rows:")
    print(gdf.head())
    
    # List column names
    print("\nColumns in the dataset:")
    print(gdf.columns.tolist())
    
    # Visualize the data
    print("\nCreating visualization...")
    fig, ax = plt.subplots(figsize=(10, 8))
    gdf.plot(ax=ax)
    plt.title(f"Visualization of layer: {first_layer}")
    
    # Save the figure
    output_file = f"{os.path.splitext(os.path.basename(gpkg_path))[0]}_{first_layer}.png"
    plt.savefig(output_file)
    print(f"Visualization saved as: {output_file}")
    
    # Show the plot
    plt.show()
    
    # Convert to GeoJSON if requested
    if export_geojson:
        # Convert CRS to WGS84 (EPSG:4326) if it isn't already
        # GeoJSON spec recommends using WGS84
        if gdf.crs and gdf.crs != "EPSG:4326":
            print(f"\nConverting from {gdf.crs} to WGS84 (EPSG:4326)...")
            gdf = gdf.to_crs("EPSG:4326")
        
        # Create output filename
        geojson_output = f"{os.path.splitext(os.path.basename(gpkg_path))[0]}_{first_layer}.geojson"
        
        # Export to GeoJSON
        print(f"\nExporting to GeoJSON: {geojson_output}")
        gdf.to_file(geojson_output, driver='GeoJSON')
        print("GeoJSON export complete!")
        
        # Optionally print the first part of the GeoJSON
        print("\nPreview of the GeoJSON (first feature):")
        if len(gdf) > 0:
            # Get the first feature as GeoJSON
            first_feature_json = json.loads(gdf.iloc[0:1].to_json())
            # Pretty print with indentation
            print(json.dumps(first_feature_json, indent=2)[0:500] + "...\n(truncated)")
        
    return gdf


def convert_gpkg_layer_to_geojson(gpkg_path, layer_name=None, output_path=None):
    """
    Convert a specific layer from a GeoPackage to GeoJSON.
    
    Args:
        gpkg_path (str): Path to the GeoPackage file
        layer_name (str, optional): Name of the layer to convert. If None, uses the first layer.
        output_path (str, optional): Path for the output GeoJSON file. If None, auto-generates a name.
        
    Returns:
        str: Path to the created GeoJSON file
    """
    # If no layer specified, get the first one
    if layer_name is None:
        layers = listlayers(gpkg_path)
        if not layers:
            raise ValueError("No layers found in the GeoPackage")
        layer_name = layers[0]
    
    # Read the layer
    gdf = gpd.read_file(gpkg_path, layer=layer_name)
    
    # Convert to WGS84 if needed
    if gdf.crs and gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")
    
    # Generate output path if not provided
    if output_path is None:
        base_name = os.path.splitext(os.path.basename(gpkg_path))[0]
        output_path = f"{base_name}_{layer_name}.geojson"
    
    # Export to GeoJSON
    gdf.to_file(output_path, driver='GeoJSON')
    print(f"Exported layer '{layer_name}' to {output_path}")
    
    return output_path
import geopandas as gpd
import matplotlib.pyplot as plt
import os
from fiona import listlayers
import json

def explore_gpkg_layers(gpkg_path):
    """
    List and print details about all layers in a GeoPackage file.
    
    Args:
        gpkg_path (str): Path to the GeoPackage file
        
    Returns:
        dict: Dictionary with layer names as keys and basic info as values
    """
    # List all layers in the geopackage
    layers = listlayers(gpkg_path)
    
    print(f"\n===== LAYERS IN {os.path.basename(gpkg_path)} =====")
    print(f"Total number of layers: {len(layers)}")
    
    layers_info = {}
    
    # Process each layer
    for i, layer_name in enumerate(layers):
        print(f"\n----- Layer {i+1}: {layer_name} -----")
        
        # Read the layer
        gdf = gpd.read_file(gpkg_path, layer=layer_name)
        
        # Get basic information
        feature_count = len(gdf)
        geometry_types = gdf.geometry.geom_type.unique().tolist()
        crs = str(gdf.crs)
        columns = gdf.columns.tolist()
        
        # Store the info
        layers_info[layer_name] = {
            "feature_count": feature_count,
            "geometry_types": geometry_types,
            "crs": crs,
            "columns": columns
        }
        
        # Print the info
        print(f"Number of features: {feature_count}")
        print(f"Geometry type(s): {', '.join(geometry_types)}")
        print(f"CRS: {crs}")
        print(f"Columns ({len(columns)}):")
        for j, col in enumerate(columns[:10]):  # Show first 10 columns
            print(f"  - {col}")
        if len(columns) > 10:
            print(f"  ... and {len(columns) - 10} more columns")
            
    return layers_info

def explore_and_convert_gpkg(gpkg_path, layer_name=None, export_geojson=True):
    """
    Explore a specific layer from a GeoPackage file, visualize it, and optionally convert to GeoJSON.
    
    Args:
        gpkg_path (str): Path to the GeoPackage file
        layer_name (str, optional): Name of the layer to explore. If None, uses the first layer.
        export_geojson (bool): Whether to export the layer as GeoJSON
        
    Returns:
        geopandas.GeoDataFrame: The geodataframe for the layer
    """
    # List all layers in the geopackage
    layers = listlayers(gpkg_path)
    if not layers:
        raise ValueError("No layers found in the GeoPackage")
    
    # If no layer specified, use the first one
    if layer_name is None:
        layer_name = layers[0]
    elif layer_name not in layers:
        raise ValueError(f"Layer '{layer_name}' not found. Available layers: {layers}")
    
    print(f"\nExploring layer: {layer_name}")
    
    # Open the layer with geopandas
    gdf = gpd.read_file(gpkg_path, layer=layer_name)
    
    # Print basic info about the layer
    print("\nBasic information:")
    print(f"Number of features: {len(gdf)}")
    print(f"Geometry type: {gdf.geometry.geom_type.unique()}")
    print(f"CRS: {gdf.crs}")
    
    # Print the first few rows
    print("\nFirst 5 rows:")
    print(gdf.head())
    
    # List column names
    print("\nColumns in the dataset:")
    print(gdf.columns.tolist())
    
    # Visualize the data
    print("\nCreating visualization...")
    fig, ax = plt.subplots(figsize=(10, 8))
    gdf.plot(ax=ax)
    plt.title(f"Visualization of layer: {layer_name}")
    
    # Save the figure
    output_file = f"{os.path.splitext(os.path.basename(gpkg_path))[0]}_{layer_name}.png"
    plt.savefig(output_file)
    print(f"Visualization saved as: {output_file}")
    
    # Show the plot
    plt.show()
    
    # Convert to GeoJSON if requested
    if export_geojson:
        convert_gpkg_layer_to_geojson(gpkg_path, layer_name)
        
    return gdf

def convert_gpkg_layer_to_geojson(gpkg_path, layer_name=None, output_path=None):
    """
    Convert a specific layer from a GeoPackage to GeoJSON.
    
    Args:
        gpkg_path (str): Path to the GeoPackage file
        layer_name (str, optional): Name of the layer to convert. If None, uses the first layer.
        output_path (str, optional): Path for the output GeoJSON file. If None, auto-generates a name.
        
    Returns:
        str: Path to the created GeoJSON file
    """
    # If no layer specified, get the first one
    if layer_name is None:
        layers = listlayers(gpkg_path)
        if not layers:
            raise ValueError("No layers found in the GeoPackage")
        layer_name = layers[0]
    
    # Read the layer
    gdf = gpd.read_file(gpkg_path, layer=layer_name)
    
    # Convert to WGS84 if needed
    if gdf.crs and gdf.crs != "EPSG:4326":
        print(f"\nConverting from {gdf.crs} to WGS84 (EPSG:4326)...")
        gdf = gdf.to_crs("EPSG:4326")
    
    # Generate output path if not provided
    if output_path is None:
        base_name = os.path.splitext(os.path.basename(gpkg_path))[0]
        output_path = f"{base_name}_{layer_name}.geojson"
    
    # Export to GeoJSON
    gdf.to_file(output_path, driver='GeoJSON')
    print(f"Exported layer '{layer_name}' to {output_path}")
    
    # Print a preview of the GeoJSON
    print("\nPreview of the GeoJSON (first feature):")
    if len(gdf) > 0:
        # Get the first feature as GeoJSON
        first_feature_json = json.loads(gdf.iloc[0:1].to_json())
        # Pretty print with indentation
        print(json.dumps(first_feature_json, indent=2)[0:500] + "...\n(truncated)")
    
    return output_path

# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python gpkg_converter.py path/to/your/file.gpkg [layer_name]")
        sys.exit(1)
    
    gpkg_file = sys.argv[1]
    
    # First print all layers and their info
    layers_info = explore_gpkg_layers(gpkg_file)
    
    # If a specific layer is provided, explore that one
    if len(sys.argv) > 2:
        layer_name = sys.argv[2]
        data = explore_and_convert_gpkg(gpkg_file, layer_name)
    else:
        # Otherwise, ask the user if they want to explore a specific layer
        layers = list(layers_info.keys())
        print("\nDo you want to explore a specific layer? Enter the number or name:")
        for i, layer in enumerate(layers):
            print(f"{i+1}. {layer}")
        
        choice = input("Enter your choice (or press Enter to skip): ")
        
        if choice.strip():
            # Try to interpret as a number first
            try:
                layer_idx = int(choice) - 1
                if 0 <= layer_idx < len(layers):
                    layer_name = layers[layer_idx]
                    data = explore_and_convert_gpkg(gpkg_file, layer_name)
                else:
                    print("Invalid layer number")
            except ValueError:
                # Try as a layer name
                if choice in layers:
                    data = explore_and_convert_gpkg(gpkg_file, choice)
                else:
                    print(f"Layer '{choice}' not found")
