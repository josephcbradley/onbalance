import os
import requests

# List of datasets you want to fetch
datasets = [
    "flood-risk-level",
    "green-belt",
    "heritage-site"
    # Add other dataset names here as needed
]

# Base URL for fetching datasets
base_url = "https://www.planning.data.gov.uk/entity.geojson"

# Create the data folder if it doesn't exist
if not os.path.exists("data"):
    os.makedirs("data")

# Loop over each dataset and fetch the data
for dataset in datasets:
    print(f"Fetching data for dataset: {dataset}")
    
    # Define the parameters to pass in the API call
    params = {
        "dataset": dataset,
        "limit": 1000  # Adjust the limit as needed (maximum number of results)
    }
    
    try:
        # Make the GET request to fetch data
        response = requests.get(base_url, params=params)
        
        # Check if the request was successful
        if response.status_code == 200:
            # Get the filename based on dataset name
            file_name = f"{dataset}.geojson"
            file_path = os.path.join("data", file_name)
            
            # Save the response data (GeoJSON) to the file
            with open(file_path, "w") as f:
                f.write(response.text)
            
            print(f"Data for {dataset} saved to {file_path}")
        else:
            print(f"Failed to fetch data for {dataset}. Status code: {response.status_code}")
    except Exception as e:
        print(f"An error occurred while fetching {dataset}: {e}")