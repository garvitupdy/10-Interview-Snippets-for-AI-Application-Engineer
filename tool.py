
"""
Snippet: Dynamic Tool Execution Framework
Difficulty: Advanced
Interview Context:
This question tests your ability to build the "Action" layer of an Agentic system. Interviewers want to see if you can bridge the gap between unstructured LLM outputs (JSON tool calls) and structured code execution. It evaluates your proficiency with Python introspection (inspect module), type safety, and the ability to auto-generate API contracts (JSON Schemas) that LLMs require for function calling.
"""
import inspect
import json
from typing import Any, Callable, Dict, List, get_type_hints
class ToolRegistry:
def init(self):
# Maps function names to the actual callable and its metadata
self.tools: Dict[str, Dict[str, Any]] = {}
Code
# Mapping Python types to JSON Schema types
    self.TYPE_MAP = {
        int: "integer",
        str: "string",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object"
    }

def register(self, func: Callable):
    """
    Registers a Python function as a tool and automatically generates 
    its JSON Schema based on type hints and docstrings.
    """
    name = func.__name__
    # Use inspect to get the function signature (parameters and return type)
    sig = inspect.signature(func)
    # Use get_type_hints for better support of postponed evaluations/strings
    type_hints = get_type_hints(func)
    # Extract the docstring for the 'description' field
    doc = inspect.getdoc(func) or "No description provided."

    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        # Skip 'self' or 'cls' if this were used inside a class context
        if param_name in ["self", "cls"]:
            continue

        p_type = type_hints.get(param_name, Any)
        json_type = self.TYPE_MAP.get(p_type, "string")

        properties[param_name] = {
            "type": json_type,
            "description": f"Parameter {param_name}" # In production, parse docstrings for this
        }

        # If there's no default value, the parameter is required
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    # Construct the OpenAI/Anthropic compatible tool definition
    self.tools[name] = {
        "callable": func,
        "schema": {
            "type": "function",
            "function": {
                "name": name,
                "description": doc,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False
                }
            }
        }
    }
    return func

def get_tool_schemas(self) -> List[Dict[str, Any]]:
    """Returns the list of schemas to be sent to the LLM."""
    return [tool["schema"] for tool in self.tools.values()]

def execute(self, tool_name: str, arguments_json: str) -> Any:
    """
    Safely parses JSON arguments and executes the corresponding Python function.
    
    Why this way? Direct mapping prevents 'eval()' security risks and 
    allows for centralized logging, validation, and error handling.
    """
    if tool_name not in self.tools:
        return f"Error: Tool '{tool_name}' not found."

    try:
        # 1. Parse the arguments from the LLM
        args = json.loads(arguments_json) if isinstance(arguments_json, str) else arguments_json
        
        # 2. Retrieve the function
        func = self.tools[tool_name]["callable"]
        
        # 3. Validation: Check if all required arguments are present
        # This acts as a guard against the LLM hallucinating arguments.
        sig = inspect.signature(func)
        sig.bind(**args) # Throws TypeError if arguments don't match signature
        
        # 4. Execution
        return func(**args)

    except json.JSONDecodeError:
        return "Error: Invalid JSON provided for arguments."
    except TypeError as e:
        return f"Error: Argument mismatch: {str(e)}"
    except Exception as e:
        return f"Error during execution: {str(e)}"

registry = ToolRegistry()
@registry.register
def get_weather(location: str, unit: str = "celsius"):
"""
Fetches the current weather for a given location.
"""
# Mock implementation
return f"The weather in {location} is 22 degrees {unit}."
@registry.register
def calculate_roi(principal: float, rate: float, time_years: int):
"""
Calculates the Return on Investment.
"""
amount = principal * (1 + rate) ** time_years
return round(amount - principal, 2)
if __name__ == "__main__":
# 1. Verify Schema Generation
    schemas = registry.get_tool_schemas()
    print("Generated Tool Schema for LLM:")
    print(json.dumps(schemas, indent=2))
    
    # 2. Simulate LLM Tool Call
   
    tool_to_call = "calculate_roi"
    llm_args = '{"principal": 1000.0, "rate": 0.05, "time_years": 5}'
    
    print(f"\nExecuting {tool_to_call}...")
    result = registry.execute(tool_to_call, llm_args)
    print(f"Result: {result}")
    
    # 3. Test Error Handling (Missing required argument)
    bad_args = '{"principal": 1000.0}' # Missing 'rate' and 'time_years'
    error_result = registry.execute("calculate_roi", bad_args)
    print(f"\nError Handling Check: {error_result}")
    
    # Sanity Checks
    assert "get_weather" in registry.tools
    assert schemas[1]["function"]["parameters"]["required"] == ["principal", "rate", "time_years"]
    print("\nImplementation successful: Dynamic mapping and execution are robust.")
