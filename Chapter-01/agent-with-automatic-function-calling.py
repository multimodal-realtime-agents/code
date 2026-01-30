
import os
from google import genai
from dotenv import load_dotenv

# Construct the path to the .env file in the parent directory
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# --- Python Function Definitions ---
# These are the actual Python functions that perform the calculations.
# When the model decides to call a function, the corresponding Python code below is executed.

def add(numbers: list[int]) -> int:
  """Calculates the sum of a list of integers.

    This function takes a list of integers as input and returns the sum of all
    the elements in the list.  It uses the built-in `sum()` function for
    efficiency.

    Args:
        numbers: A list of integers to be added.

    Returns:
        The sum of the integers in the input list.  Returns 0 if the input
        list is empty.

    Examples:
        add([1, 2, 3]) == 6
        add([-1, 0, 1]) == 0
        add([]) == 0
    """
  return sum(numbers)

def subtract(numbers: list[int]) -> int:
    """Subtracts numbers in a list sequentially from left to right.

    This function performs subtraction on a list of integers, applying the
    subtraction operation from left to right.  For example, given the list
    [10, 2, 5], the function will calculate 10 - 2 - 5.

    Args:
        numbers: A list of integers to be subtracted.

    Returns:
        The result of the sequential subtraction as an integer. Returns 0 if the input list is empty.

    Examples:
        subtract([10, 2, 5]) == 3  # (10 - 2) - 5 = 8 - 5 = 3
        subtract([10, 2]) == 8      # 10 - 2 = 8
        subtract([]) == 0
    """
    if not numbers:
        return 0  # Handle empty list
    result = numbers[0]
    for num in numbers[1:]:
        result -= num
    return result

def multiply(numbers: list[int]) -> int:
  """Calculates the product of a list of integers.

    This function takes a list of integers as input and returns the product of all
    the elements in the list. It iterates through the list, multiplying each
    number with the accumulated product.

    Args:
        numbers: A list of integers to be multiplied.

    Returns:
        The product of the integers in the input list. Returns 1 if the input
        list is empty.

    Examples:
        multiply([2, 3, 4]) == 24  # 2 * 3 * 4 = 24
        multiply([1, -2, 5]) == -10 # 1 * -2 * 5 = -10
        multiply([]) == 1
    """
  product = 1
  for num in numbers:
    product *= num
  return product

def divide(numbers: list[int]) -> float:  # Use float for division
    """Divides numbers in a list sequentially from left to right.

    This function performs division on a list of integers, applying the division
    operation from left to right.  For example, given the list [10, 2, 5], the
    function will calculate 10 / 2 / 5.

    Args:
        numbers: A list of integers to be divided.

    Returns:
        The result of the sequential division as a float.

    Raises:
        ZeroDivisionError: If any number in the list *after* the first element
                           is zero, a ZeroDivisionError is raised.  Division by
                           zero is not permitted.

    Returns:
        float: The result of the division. Returns 0.0 if the input list is empty.

    Examples:
        divide([10, 2, 5]) == 1.0  # (10 / 2) / 5 = 5 / 5 = 1.0
        divide([10, 2]) == 5.0      # 10 / 2 = 5.0
        divide([10, 0, 5])  # Raises ZeroDivisionError
        divide([]) == 0.0
    """
    if not numbers:
        return 0.0 # Handle empty list
    if 0 in numbers[1:]: # Check for division by zero
        raise ZeroDivisionError("Cannot divide by zero.")
    result = numbers[0]
    for num in numbers[1:]:
        result /= num
    return result

# --- Tool Creation ---
# A Tool is a collection of FunctionDeclarations that are grouped together.
# This 'math_tool' bundles all the calculator functions, which will then be provided to the model.
math_tool = [ add, subtract, multiply, divide ]

def agent_core_with_history(tools=math_tool):
    """Sends a request to the generative model with a specific configuration.

    This function is the core of an agent and packages the conversation history, 
    a system instruction, and a set of tools, then sends it to the model. 
    It's configured for manual function calling, allowing the calling code to handle tool execution.

    Args:
        contents (list): A list of 'types.Content' objects representing the
            conversation history.
        tools (genai.types.Tool, optional): The tool or set of tools available
            to the model for this request. Defaults to the global `math_tool`.

    Returns:
        The chat object that a user can interact and keep the history of interactions.
    """
    # Define the system instruction, which sets the context for the model's behavior.
    instruction_prompt = """You are a specialized math assistant. Your sole purpose is to solve arithmetic problems involving addition, subtraction, multiplication, and division. Handle multi-step calculations and number ranges. Decline all non-mathematical requests."""
    
    return client.chats.create(
            model=MODEL,
            config={
                "tools": tools,
                "system_instruction": instruction_prompt,
                # automatic_function_calling defaults to enabled
            }
        )

# --- Utility Function for History Logging ---
# The following function is a helper utility designed for debugging and
# demonstration. It provides a clear, formatted output of the entire
# conversation history, making it easy to trace the interaction between
# the user, the model, and any tools that were called.
def print_history(chat):
  """Prints the conversation history of a chat session in a readable format.

  This function iterates through each turn in the chat's history, displaying
  the role (user, model, or tool) and the content of each part of the message,
  including text, function calls, and function responses.

  Args:
      chat (genai.ChatSession): The chat object from which to retrieve and
          print the history.
  """
  for content in chat.get_history():
      # Print the role of the author for this turn (e.g., "user" or "model").
      print(">" + content.role + ":")

      # Iterate through each content object (turn) in the conversation history.
      for part in content.parts:
          if part.text:
              print(part.text)
          if part.function_call:
              print("Function call: {", part.function_call, "}")
          if part.function_response:
              print("Function response: {", part.function_response, "}")
      print("-" * 80)

# --- Main Execution Block ---
# This is the entry point of the script.
if __name__ == '__main__':
    GOOGLE_GENAI_USE_VERTEXAI = os.getenv("GOOGLE_GENAI_USE_VERTEXAI") # The Google Cloud Project
    
    if(GOOGLE_GENAI_USE_VERTEXAI=="1"):
        GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT") # The Google Cloud Project
        LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1") # The location of execution e.g. "us-central1"
        client = genai.Client(vertexai=True, project=GOOGLE_CLOUD_PROJECT, location=LOCATION)
    else:
        GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        client = genai.Client(vertexai=False, api_key=GOOGLE_API_KEY)

    instruction_prompt = """You are a specialized math assistant. Your sole purpose is to solve arithmetic problems involving addition, subtraction, multiplication, and division. Handle multi-step calculations and number ranges. Decline all non-mathematical requests."""
   
    chat = agent_core_with_history(tools=math_tool)
    
    response = chat.send_message("Could you add all the numbers between 1 and 5 and then multiply by 2?")

    print("--------------------")
    print('>>> LLM Response <<<')
    print("--------------------")
    print(f">>> Response:{response.text}\n")

    print("---------------------------")
    print('>>> Interaction History <<<')
    print("---------------------------")
    print_history(chat)   
