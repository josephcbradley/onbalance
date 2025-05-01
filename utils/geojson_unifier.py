#!/usr/bin/env python3
"""
London GeoJSON Directory Grouper

This script scans a directory for GeoJSON files and groups them based on their names,
handling singular/plural variations and other similar naming patterns.
It outputs the groupings to a JSON file.
"""

import os
import json
import glob
from collections import defaultdict
import re
from pathlib import Path

# Define known singular/plural equivalents and other variations
EQUIVALENTS = {
    # Format: 'standard_name': [list of variations]
    'air quality management area': ['air quality management areas'],
    'allotment': ['allotments', 'allotment site'],
    'ancient monument': ['ancient monuments', 'scheduled ancient monument', 'scheduled ancient monuments', 'scheduled monument', 'scheduled monuments'],
    'archaeological priority area': ['archaelogical priority area', 'archaelogical priority areas', 'archaeological priority areas', 'archaeological priority zone', 'archaeological priority zones'],
    'area action plan': ['area action plans'],
    'area of special character': ['areas of special character'],
    'blue ribbon': ['blue ribbon network'],
    'burial space': ['burial spaces'],
    'central activities zone': ['central activities zone frontage', 'central activities zone fringe'],
    'community open space': ['community open spaces'],
    'conservation area': ['conservation areas'],
    'critical drainage area': ['critical drainage areas'],
    'crossrail': ['crossrail safeguarding', 'crossrail safeguarding area', 'crossrail safeguarding line'],
    'crossrail 2': ['crossrail 2 safeguarding', 'crossrail 2 safeguarding area'],
    'cultural quarter': ['cultural quarters'],
    'district centre': ['district centres', 'district shopping centre', 'district town centres'],
    'flood risk area': ['flood risk areas', 'areas at risk of flooding'],
    'flood zone 2': ['flood risk zone 2', 'floodzone 2'],
    'flood zone 3': ['flood risk zone 3', 'floodzone 3', 'flood zone 3a', 'flood zone 3b', 'functional floodplain', 'floodzone 3a fluvial and tidal', 'floodzone 3a surface water', 'floodzone 3b fluvial and tidal'],
    'green belt': ['metropolitan green belt', 'greenbelt', 'green belt employment sites'],
    'green chain': ['green chains', 'green chain link', 'green chain parks', 'green chain walk', 'south east london green chain', 'south east london green chain walk', 'metropolitan green chains', 'green chains and corridors'],
    'green corridor': ['green corridors', 'wildlife corridor', 'wildlife corridors', 'ecological corridors'],
    'green grid': ['green grid buffer zone', 'new green grid', 'new green grid buffer zone'],
    'green link': ['green links'],
    'growth area': ['growth areas'],
    'gypsy and traveller site': ['gypsy traveller site', 'gypsy traveller sites', 'gypsy and traveller sites', 'sites for gypsies and travellers', 'safeguarded for gypsies and traveller accommodation', 'safeguarded gypsy traveller sites'],
    'heritage land': ['heritage lands'],
    'historic park and garden': ['historic parks and gardens', 'historic parks gardens', 'registered parks and gardens', 'historic parks', 'registered parks gardens', 'locally listed historic parks and gardens', 'registered historic parks and gardens'],
    'landmark': ['landmarks'],
    'lee valley regional park': ['lee valley regional park authority boundary', 'lvpra boundary'],
    'listed building': ['listed buildings', 'statutory listed buildings', 'listed building points'],
    'local centre': ['local centres', 'local shopping centres', 'local shopping areas'],
    'local green space': ['local green spaces'],
    'local industrial location': ['local industrial locations'],
    'local nature reserve': ['local nature reserves', 'nature reserves'],
    'local open space': ['local open spaces', 'local open space deficiency'],
    'local shopping parades': ['local shopping parade', 'neighbourhood parades', 'neighbourhood retail parades'],
    'local view': ['local views', 'views of local importance', 'local designated views'],
    'locally listed building': ['locally listed buildings', 'locally listed buildings points'],
    'locally significant industrial site': ['locally significant industrial sites', 'lsis'],
    'london distributor road': ['london distributor roads'],
    'london square': ['london squares', 'protected london squares', 'protected squares'],
    'major centre': ['major centres', 'major shopping centres', 'major town centres'],
    'metropolitan open land': ['metropolitan open lands'],
    'neighbourhood centre': ['neighbourhood centres', 'neighbourhood shopping centres', 'neighbourhood town centres'],
    'open space': ['open spaces', 'urban open space', 'other open spaces', 'other open land', 'other large protected open spaces', 'other undesignated open space protected by london plan policy 7 18'],
    'opportunity area': ['opportunity areas'],
    'place': ['places'],
    'primary frontage': ['primary frontages', 'primary shopping frontage', 'primary shopping frontages', 'primary retail frontage', 'core shopping frontages', 'protected core shopping frontages', 'main retail frontage', 'key shopping frontage'],
    'primary shopping area': ['primary shopping areas', 'principal shopping areas'],
    'regionally important geological site': ['regionally important geological sites', 'regionally important geological and geomorphological site', 'regionally important geological and geomorphological sites', 'regionally and locally important geological sites', 'locally important geological site', 'locally important geological sites', 'geology rigs ligs'],
    'safeguarded waste site': ['safeguarded waste sites', 'safeguarded existing waste sites'],
    'safeguarded wharf': ['safeguarded wharves', 'safeguarded wharf'],
    'school site': ['school sites'],
    'secondary frontage': ['secondary frontages', 'secondary shopping frontage', 'secondary shopping frontages', 'secondary retail frontage', 'protected secondary shopping frontages', 'secondary shopping areas'],
    'shopping frontage': ['shopping frontages', 'shopping frontages other', 'protected shopping frontages'],
    'site allocation': ['site allocations', 'site proposals', 'proposal sites'],
    'site of importance for nature conservation': ['sites of importance for nature conservation', 'sites of importance to nature conservation', 'sites of nature conservation importance', 'sincs', 'sinc grades 1 and 2'],
    'site of special scientific interest': ['sites of special scientific interest', 'sssi', 'sssis'],
    'strategic cultural area': ['strategic cultural areas', 'south kensington strategic cultural area'],
    'strategic industrial land': ['strategic industrial location', 'strategic industrial locations', 'strategic protected industrial land', 'preferred industrial locations', 'integrated industrial locations', 'separated industrial locations', 'strategic industrial land', 'established industrial locations', 'priority industrial areas'],
    'strategic road': ['strategic roads', 'strategic road network', 'tfL road network', 'transport for london road network', 'strategic routes'],
    'strategic site': ['strategic sites', 'strategic development locations', 'strategic development areas'],
    'strategic view': ['strategic views', 'london view management framework', 'lvmf protected vistas', 'protected vistas', 'protected vistas lvmf 2010', 'protected views', 'viewing corridor', 'strategically important skyline'],
    'tall building': ['tall buildings', 'tall building zones', 'tall buildings zones', 'tall building areas', 'tall building locations', 'tall building growth areas', 'appropriate location for tall buildings'],
    'thames path': ['thamesfoot path', 'existing thames path', 'proposed thames path'],
    'thames policy area': ['thames policy areas'],
    'town centre boundary': ['town centre boundaries'],
    'town centre': ['town centres'],
    'wandle valley regional park': ['wandle valley regional park 400m buffer'],
    'waste site': ['waste sites', 'waste management sites', 'waste safeguarded facilities', 'integrated waste management facility', 'waste site', 'waste safeguarding', 'waste areas', 'strategic waste sites', 'south london waste plan', 'waste disposal'],
    'world heritage site': ['world heritage site buffer zone', 'world heritage site and buffer area', 'world heritage site views', 'immediate setting of westminster world heritage site', 'approaches to westminster world heritage site']
}

def extract_core_name(filepath):
    """
    Extract the core name from a file path, removing extension and trailing numbers.
    
    Args:
        filepath (str): File path to process
        
    Returns:
        str: Core name
    """
    basename = os.path.basename(filepath)
    name, _ = os.path.splitext(basename)
    
    # Remove trailing numbers (district identifiers)
    name = re.sub(r'_\d+$', '', name)
    
    return name

def normalize_name(name):
    """
    Normalize a name by replacing underscores with spaces and converting to lowercase.
    
    Args:
        name (str): Name to normalize
        
    Returns:
        str: Normalized name
    """
    # Replace underscores with spaces
    name = name.replace('_', ' ')
    
    # Convert to lowercase
    name = name.lower()
    
    # Remove multiple spaces
    name = ' '.join(name.split())
    
    return name

def create_reverse_mapping(equivalents):
    """
    Create a reverse mapping from all variations to their standard names.
    
    Args:
        equivalents (dict): Dictionary of standard names to variations
        
    Returns:
        dict: Reverse mapping from variations to standard names
    """
    reverse_map = {}
    for standard, variations in equivalents.items():
        for variation in variations:
            reverse_map[variation] = standard
        # Also map the standard to itself
        reverse_map[standard] = standard
    return reverse_map

def group_geojson_files(directory, equivalents):
    """
    Scan a directory for GeoJSON files and group them based on their normalized names and known equivalents.
    
    Args:
        directory (str): Directory path to scan
        equivalents (dict): Dictionary of standard names to variations
        
    Returns:
        tuple: (grouped_files, file_list) - Dictionary of grouped files and list of all files
    """
    # Create reverse mapping
    reverse_map = create_reverse_mapping(equivalents)
    
    # Find all GeoJSON files in the directory (including subdirectories)
    file_list = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.geojson'):
                file_path = os.path.join(root, file)
                file_list.append(file_path)
    
    # Alternative method using glob (can be simpler for some cases)
    # file_list = glob.glob(os.path.join(directory, '**', '*.geojson'), recursive=True)
    
    # Group files by their normalized name
    grouped_files = defaultdict(list)
    
    for filepath in file_list:
        # Extract core name
        core_name = extract_core_name(filepath)
        
        # Normalize the name
        norm_name = normalize_name(core_name)
        
        # Look up in equivalents
        if norm_name in reverse_map:
            standard_name = reverse_map[norm_name]
        else:
            # If not found, use the normalized name
            standard_name = norm_name
        
        # Add to the group
        grouped_files[standard_name].append(filepath)
    
    return grouped_files, file_list

def format_group_name(name):
    """
    Format a group name for display, using title case.
    
    Args:
        name (str): Group name to format
        
    Returns:
        str: Formatted group name
    """
    return ' '.join(word.capitalize() for word in name.split())

def main():
    """Main function to execute the script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Group GeoJSON files in a directory based on name patterns')
    parser.add_argument('directory', help='Directory containing GeoJSON files')
    parser.add_argument('--output', '-o', default='geojson_groups.json', help='Output JSON file path')
    args = parser.parse_args()
    
    directory = args.directory
    output_file = args.output
    
    print(f"Scanning directory: {directory}")
    
    # Group the files
    grouped_files, file_list = group_geojson_files(directory, EQUIVALENTS)
    
    print(f"Found {len(file_list)} GeoJSON files")
    
    # Format the results
    result = {
        "groups": {},
        "summary": {
            "total_files": len(file_list),
            "total_groups": len(grouped_files),
            "average_files_per_group": len(file_list) / len(grouped_files) if grouped_files else 0,
            "largest_groups": []
        }
    }
    
    # Sort the groups by name and add to result
    for group_name in sorted(grouped_files.keys()):
        display_name = format_group_name(group_name)
        result["groups"][display_name] = sorted(grouped_files[group_name])
    
    # Add the largest groups to the summary
    sorted_by_size = sorted(grouped_files.items(), key=lambda x: len(x[1]), reverse=True)
    for i, (name, files) in enumerate(sorted_by_size[:10]):
        display_name = format_group_name(name)
        result["summary"]["largest_groups"].append({
            "name": display_name,
            "count": len(files)
        })
    
    # Write the results to a JSON file
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"Grouped {result['summary']['total_files']} files into {result['summary']['total_groups']} groups")
    print(f"Results saved to {output_file}")
    
    print("\nTop 10 largest groups:")
    for i, group_info in enumerate(result["summary"]["largest_groups"]):
        print(f"{i+1}. {group_info['name']}: {group_info['count']} files")

if __name__ == "__main__":
    main()