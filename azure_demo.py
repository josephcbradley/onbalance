
import os 
from openai import AzureOpenAI

def azure_summary_call(df, potential_homes, target_homes):

    with open('SECRETS', 'r') as f:
        for line in f:
            # Skip empty lines and comments
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key.strip()] = value.strip()
    openai_model = os.environ.get("AZURE_OPENAI_MODEL", "gpt-4.1-mini")
    api_version = os.environ.get("OPENAI_API_VERSION", "2024-12-01-preview")
    azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_KEY")

    # Ensure your environment variables are set - these will have been provided as part of the hackathon
    

    # gets the API Key from environment variable AZURE_OPENAI_API_KEY
    client = AzureOpenAI(
        api_version=api_version,
        azure_endpoint=azure_endpoint,
        azure_deployment=openai_model,
        api_key=api_key,
    )

    # Convert dataframe to JSON string
    json_data = df.to_json(orient='records')

    # Create prompt with JSON data
    prompt = f"Here is the data in JSON format: {json_data}. Please analyze this data and provide a summary in clear, concise, British english. Don't quote too many numbers - just highlight which constraints open up the most new houses when we break them. Also include the number of potential homes the user has identified, {potential_homes}, and the number of target homes, {target_homes}."


    completion = client.chat.completions.create(
        model=openai_model,
        messages=[
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    return completion.choices[0].message.content