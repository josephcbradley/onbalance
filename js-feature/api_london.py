import requests
import json

# Define the base URL for the API
base_url = "https://api.planning.data.gov.uk/entity.geojson"

# List of datasets you want to fetch
datasets = [
    "flood-risk-level"
]

# Define additional parameters if necessary (e.g., filters)
params = {
    "limit": 10,  # Limit to 10 results per dataset
    "typology": ["residential"],  # Filter by typology, if necessary
}

# Loop through each dataset and fetch the data
for dataset in datasets:
    print(f"Fetching data for dataset: {dataset}")
    
    # Add the current dataset to the params
    params["dataset"] = [dataset]  # Replace the dataset filter with the current one
    
    # Make the GET request
    response = requests.get(base_url, params=params)
    
    # Check if the request was successful
    if response.status_code == 200:
        # Save the GeoJSON data to a file named by the dataset
        filename = f"{dataset}_data.geojson"
        with open(filename, 'w') as f:
            json.dump(response.json(), f)
        print(f"Data for {dataset} has been saved as {filename}!")
    else:
        print(f"Failed to fetch data for {dataset}. Status code: {response.status_code}")