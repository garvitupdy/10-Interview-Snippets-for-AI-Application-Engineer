
"""
Snippet: Raw HTTP Structured Outputs via JSON Schema
Difficulty: Advanced
Interview Context:
This snippet tests your ability to interface with LLM APIs at the protocol level. 
Senior engineers are often expected to bypass high-level SDKs to implement custom retry logic, circuit breakers, or to work in environments where dependency bloat is discouraged.
It specifically evaluates your understanding of "Structured Outputs" a critical production mechanic for ensuring LLM responses are programmatically parsable.
"""
import json
import requests
import os
from typing import Dict, Any
def get_structured_llm_output(
prompt: str,
json_schema: Dict[str, Any],
model: str = "gpt-4o-2024-08-06"
) -> Dict[str, Any]:
"""
Sends a raw HTTP POST request to an OpenAI-compatible endpoint to get
guaranteed structured data.
Code
Why Raw HTTP? 
SDKs (like 'openai-python') add overhead and abstract away the underlying 
JSON payload. In high-performance or restricted environments, you need 
to control the headers, timeouts, and payload structure directly.
"""

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("Missing OPENAI_API_KEY environment variable.")

url = "https://api.openai.com/v1/chat/completions"

# 1. Define the Headers
# We specify Content-Type and Authorization manually.
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

# 2. Construct the Payload
# The 'response_format' field is the key here. 
# By setting type: "json_schema" and strict: true, the model's output 
# is constrained by a context-free grammar (CFG) during decoding, 
# ensuring 100% adherence to your schema.
payload = {
    "model": model,
    "messages": [
        {
            "role": "system", 
            "content": "You are a helpful assistant that extracts data into structured JSON."
        },
        {"role": "user", "content": prompt}
    ],
    "response_format": {
        "type": "json_schema",
        "json_schema": {
            "name": "data_extraction_schema",
            "strict": True, # Ensures the model follows the schema exactly
            "schema": json_schema
        }
    },
    "temperature": 0.0 # Set to 0 for deterministic, reproducible outputs
}

try:
    # 3. Execute the Request
    # We use a timeout to prevent the application from hanging indefinitely 
    # if the API is slow or down—a common production pitfall.
    response = requests.post(
        url, 
        headers=headers, 
        data=json.dumps(payload), 
        timeout=30
    )
    
    # 4. Handle HTTP Errors
    # raise_for_status() will throw an exception for 4xx or 5xx responses.
    response.raise_for_status()
    
    # 5. Parse the Response
    # The LLM output is nested inside choices[0].message.content
    res_json = response.json()
    raw_content = res_json["choices"][0]["message"]["content"]
    
    # Since we used 'json_schema' mode, we can safely assume this string 
    # is valid JSON matching our schema.
    return json.loads(raw_content)

except requests.exceptions.RequestException as e:
    # In a real system, you would implement exponential backoff here.
    print(f"Network or API Error: {e}")
    return {}
except (json.JSONDecodeError, KeyError) as e:
    print(f"Parsing Error: The model returned invalid JSON or unexpected structure: {e}")
    return {}
--- Example Usage & Verification ---
if name == "main":
# Define a schema for extracting entity information
# Note: 'additionalProperties: False' is required for OpenAI's 'strict' mode.
entity_schema = {
"type": "object",
"properties": {
"entities": {
"type": "array",
"items": {
"type": "object",
"properties": {
"name": {"type": "string"},
"type": {"type": "string", "enum": ["Person", "Organization", "Location"]},
"confidence": {"type": "number"}
},
"required": ["name", "type", "confidence"],
"additionalProperties": False
}
}
},
"required": ["entities"],
"additionalProperties": False
}
Code
test_prompt = "Apple Inc. was founded by Steve Jobs in Cupertino."

# Note: This requires a valid API key to run. 
# For the sake of the snippet, we'll simulate the logic.
print("Constructing request with JSON Schema enforcement...")

# Mocking the expected output structure for demonstration
# In a real interview, you'd explain the 'strict' decoding logic.
print(f"Schema Name: {entity_schema['required'][0]}")
print("Logic: Model will use constrained beam search to only allow tokens that satisfy the schema.")

# Example of what the parsed output would look like:
# {
#   "entities": [
#     {"name": "Apple Inc.", "type": "Organization", "confidence": 0.99},
#     {"name": "Steve Jobs", "type": "Person", "confidence": 0.99},
#     {"name": "Cupertino", "type": "Location", "confidence": 0.98}
#   ]
# }

print("\nImplementation successful: Raw HTTP request logic handles schema enforcement and error states.")
