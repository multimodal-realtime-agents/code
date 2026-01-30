
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Construct the path to the .env file in the parent directory
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# --- Function Declarations for the Model ---
# This section defines the structure of the functions that the generative model can call.
# Each FunctionDeclaration describes the function's name, what it does, and the parameters it expects.
# This information helps the model understand how and when to use each tool.

# Declaration for the 'add' function.
add_func = types.FunctionDeclaration(
    name="add",
    description="Calculates the sum of a list of integers.",
    parameters={
        "type": "object",
        "properties": {
            "numbers": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "A list of integers to be added.",
            }
        },
        "required": ["numbers"],
    },
)

# Declaration for the 'subtract' function.
subtract_func = types.FunctionDeclaration(
    name="subtract",
    description="Subtracts numbers in a list sequentially from left to right.",
    parameters={
        "type": "object",
        "properties": {
            "numbers": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "A list of integers to be subtracted.",
            }
        },
        "required": ["numbers"],
    },
)

# Declaration for the 'multiply' function.
multiply_func = types.FunctionDeclaration(
    name="multiply",
    description="Calculates the product of a list of integers.",
    parameters={
        "type": "object",
        "properties": {
            "numbers": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "A list of integers to be multiplied.",
            }
        },
        "required": ["numbers"],
    },
)

# Declaration for the 'divide' function.
divide_func = types.FunctionDeclaration(
    name="divide",
    description="Divides numbers in a list sequentially from left to right.",
    parameters={
        "type": "object",
        "properties": {
            "numbers": {
                "type": "array",
                "items": {"type": "number"},
                "description": "A list of numbers to be divided.",
            }
        },
        "required": ["numbers"],
    },
)

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
math_tool = types.Tool(
    function_declarations=[
        add_func,
        subtract_func,
        multiply_func,
        divide_func,
    ],
)

# --- Function Handler ---
# This dictionary maps the function names (as strings) to the actual Python function objects.
# It acts as a router, allowing the application to easily call the correct function based on the model's output.
function_handler = {
    "add": add,
    "subtract": subtract,
    "multiply": multiply,
    "divide": divide,
}


def agent_core(contents, tools=math_tool):
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
        The model's response object, which may contain text or one or more
        function call requests.
    """
    # Define the system instruction, which sets the context for the model's behavior.
    instruction_prompt = """You are a specialized math assistant. Your sole purpose is to solve arithmetic problems involving addition, subtraction, multiplication, and division. Handle multi-step calculations and number ranges. Decline all non-mathematical requests."""
    
    # Call the generative model's API specifying the model version and the tools it can use.
    return client.models.generate_content(
            model=MODEL, # Updated to a recommended model e.g. "gemini-2.5-flash"
            contents = contents,
            config={
                "tools": [tools],
                "system_instruction": instruction_prompt,
                "automatic_function_calling": { "disable": True }
            }
        )

# --- Core Interact and Function Calling Loop ---
# This function orchestrates the conversation with the model.
# It sends the user's query, handles function calls requested by the model,
# executes the corresponding Python functions, and sends the results back to the model.
def send_user_query(query: str):
    """
    Orchestrates the multi-turn conversation with the model.

    It sends an initial query, then enters a loop to handle any function calls
    the model requests. It executes these functions, sends the results back,
    and continues until the model provides a final, text-based answer.

    Args:
        query (str): The initial question or prompt from the user.
    """

    # 1. Initial Setup
    # Format the user's query into the required 'Content' object structure.
    user_prompt_content = types.Content(role='user', parts=[types.Part.from_text(text=query)])

    # Send the first request to the model with the user's query.
    response = agent_core(user_prompt_content)
    
    # Initialize a list to keep track of the entire conversation history.
    # This starts with the user's first message.
    content_history = [user_prompt_content]
    
    # 2. Function Calling Loop
    # This loop continues as long as the model responds by requesting function calls.
    while True:
        # Check for a function call in the response
        if response.function_calls:
            # First, add the function call to the model interaction history
            function_calls_content = response.candidates[0].content
            content_history.append(function_calls_content)

            # Iterate through each function call requested by the model in this turn.
            for function_call in response.function_calls:
                function_name = function_call.name
                if function_name in function_handler:
                    function_to_call = function_handler[function_name] # Retrieve the actual Python function from our handler dictionary.
                    function_args = function_call.args # Get the arguments for the function, as provided by the model.
                    
                    print("----------------------")
                    print('>>> Tool Selection <<<')
                    print("----------------------")
                    print(f">>> Function call: {function_name} with input argument ({function_args})\n")
                    
                    # Execute the corresponding Python function with the model-provided arguments.
                    function_response = function_to_call(**function_args)
                    
                    print("-------------------------")
                    print('>>> Function Response <<<')
                    print("-------------------------")
                    print(f">>> Response: {function_response}\n")
                    
                    # Package the result from the tool into a 'Content' object.
                    # This object explicitly states its role is 'tool' and includes the function name and its output.
                    function_response_content = types.Content(role='tool', 
                                                              parts=[types.Part.from_function_response(
                                                                  name=function_name,
                                                                  response={"result": function_response})])

                    # Add the tool's response to our conversation history.
                    content_history.append(function_response_content)

                else:
                    print(f"Error: Model requested unknown function '{function_name}'")

            # 3. Send Updated History to Model
            # After executing all function calls for the current turn, send the entire updated
            # conversation history back to the model so it can generate the next response.
            response = agent_core(content_history)
        else:
            # 4. Exit Condition
            # If the model's response does not contain any function calls, it means the model
            # has provided its final text answer. Print this answer and break the loop.
            print("--------------------")
            print('>>> LLM Response <<<')
            print("--------------------")
            print(response.text)
            break


# --- Main Execution Block ---
# This is the entry point of the script.
if __name__ == '__main__':

    GOOGLE_GENAI_USE_VERTEXAI = os.getenv("GOOGLE_GENAI_USE_VERTEXAI")
    
    if(GOOGLE_GENAI_USE_VERTEXAI=="1"):
        GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT") # The Google Cloud Project
        LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1") # The location of execution e.g. "us-central1"
        client = genai.Client(vertexai=True, project=GOOGLE_CLOUD_PROJECT, location=LOCATION)
    else:
        GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        client = genai.Client(vertexai=False, api_key=GOOGLE_API_KEY)

    MODEL = os.getenv("MODEL", "gemini-2.5-flash") # The model ID for the example

    send_user_query("Could you add all the numbers between 1 and 5 and then multiply by 2?")

