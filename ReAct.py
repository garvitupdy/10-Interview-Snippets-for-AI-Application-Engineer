
"""
Snippet: ReAct (Reasoning + Acting) Execution Engine
Difficulty: Advanced
Interview Context:
The ReAct pattern is the backbone of modern autonomous agents. Interviewers use this to evaluate your ability to manage stateful multi-turn loops, implement robust string parsing for "Thought/Action" blocks, and handle the "Context Window" by correctly interleaving model outputs with external tool observations.
"""
import re
import json
from typing import Dict, Callable, List, Optional
class ReActAgent:
def init(self, tools: Dict[str, Callable], max_iterations: int = 5):
"""
Initializes the ReAct engine.
Code
Args:
        tools: A dictionary mapping tool names to Python functions.
        max_iterations: Safety cap to prevent infinite loops (and burning API credits).
    """
    self.tools = tools
    self.max_iterations = max_iterations
    
    # The System Prompt is the "Brain" of the ReAct agent. 
    # It defines the strict grammar the model must follow.
    self.system_prompt = """
    You operate in a loop of Thought, Action, PAUSE, Observation.
    At the end of the loop you output an Answer.

    Use Thought to describe your thoughts about the question you have been asked.
    Use Action to run one of the actions available to you - then return PAUSE.
    Observation will be the result of running those actions.

    Your available actions are:
    {tool_descriptions}

    Example session:
    Question: What is the capital of France?
    Thought: I need to look up the capital of France.
    Action: wikipedia: France
    PAUSE

    You will be called again with this:
    Observation: France is a country. Its capital is Paris.

    Thought: I now know the answer.
    Answer: The capital of France is Paris.
    """.strip()

def _parse_action(self, text: str) -> Optional[tuple[str, str]]:
    """
    Uses Regex to extract the Action and Action Input from the LLM's raw text.
    
    Pattern: Action: tool_name: tool_input
    """
    # We look for the "Action:" line. This is a common failure point in agents;
    # robust parsing is key.
    regex = r"Action:\s*([\w_]+):\s*(.*)"
    match = re.search(regex, text)
    if match:
        return match.group(1), match.group(2)
    return None

def run(self, question: str, llm_client: Callable[[str], str]):
    """
    The core execution loop. 
    
    Args:
        question: The user's query.
        llm_client: A function that takes a string (prompt) and returns a string (LLM response).
    """
    # 1. Initialize Context
    # We format the tool descriptions so the LLM knows what it can do.
    tool_desc = "\n".join([f"- {name}: {func.__doc__.strip() if func.__doc__ else ''}" 
                           for name, func in self.tools.items()])
    
    prompt = self.system_prompt.format(tool_descriptions=tool_desc)
    prompt += f"\n\nQuestion: {question}"
    
    print(f"--- Starting ReAct Loop for: {question} ---")

    for i in range(self.max_iterations):
        print(f"\n[Iteration {i+1}]")
        
        # 2. LLM Generation
        # The model generates Thought + Action + PAUSE
        response = llm_client(prompt)
        print(f"Agent Response:\n{response}")
        
        # 3. Check for Final Answer
        # If the model provides an 'Answer:', we are done.
        if "Answer:" in response:
            return response.split("Answer:")[-1].strip()

        # 4. Parse and Execute Action
        action_data = self._parse_action(response)
        if action_data:
            tool_name, tool_input = action_data
            
            if tool_name not in self.tools:
                observation = f"Error: Tool '{tool_name}' is not available."
            else:
                print(f"Executing Tool: {tool_name}({tool_input})")
                try:
                    # Execute the native Python function
                    observation = str(self.tools[tool_name](tool_input))
                except Exception as e:
                    observation = f"Error executing tool: {str(e)}"
            
            # 5. Update Context
            # We append the Observation back to the prompt. This is the "Acting" 
            # feedback loop that informs the next "Reasoning" step.
            print(f"Observation: {observation}")
            prompt += f"\n{response}\nObservation: {observation}"
        else:
            # Edge Case: The model hallucinated a format or failed to act.
            # We nudge it to follow the format.
            prompt += f"\n{response}\nObservation: Invalid format. Please use Thought/Action/PAUSE."

    return "Failed to reach an answer within max iterations."
--- Example Usage & Verification ---
1. Define some tools
def get_stock_price(symbol: str):
"""Returns the current stock price of a company."""
# Mock data
prices = {"AAPL": 150.0, "GOOG": 2800.0, "TSLA": 700.0}
return prices.get(symbol.upper(), "Symbol not found.")
def calculate_investment(args_str: str):
"""Calculates value: 'price * shares'. Input format: 'price, shares'"""
try:
price, shares = map(float, args_str.split(","))
return price * shares
except:
return "Invalid input format. Use 'price, shares'"
2. Mock LLM Client
In a real scenario, this would call OpenAI/Anthropic.
Here, we simulate the model's "Thought/Action" logic.
def mock_llm(prompt: str) -> str:
if "Observation:" not in prompt:
return "Thought: I need to find the price of AAPL first.\nAction: get_stock_price: AAPL\nPAUSE"
elif "150.0" in prompt and "calculate_investment" not in prompt:
return "Thought: I have the price (150.0). Now I need to calculate the value for 10 shares.\nAction: calculate_investment: 150.0, 10\nPAUSE"
else:
return "Thought: I have the final calculation.\nAnswer: The total value of 10 AAPL shares is $1500.0."
if name == "main":
# Initialize Registry
tools = {
"get_stock_price": get_stock_price,
"calculate_investment": calculate_investment
}
Code
agent = ReActAgent(tools)

# Run the agent
final_result = agent.run(
    question="How much is 10 shares of AAPL worth?",
    llm_client=mock_llm
)

print(f"\n--- Final Result ---\n{final_result}")

# Sanity Check
assert "1500" in final_result, "The agent failed to calculate the correct value."
print("\nImplementation successful: ReAct loop correctly managed state and tool execution.")
