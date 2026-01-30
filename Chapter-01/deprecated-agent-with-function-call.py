# Import the necessary components from the Vertex AI SDK for Python.
# This includes classes for interacting with generative models, defining tools, and handling responses.

import vertexai
from vertexai.generative_models import (
    FunctionDeclaration,
    GenerationConfig,
    GenerationResponse,
    GenerativeModel,
    Part,
    Tool,
)

import os
from dotenv import load_dotenv

# Construct the path to the .env file in the parent directory
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# --- Function Declarations for the Model ---
# This section defines the structure of the functions that the generative model can call.
# Each FunctionDeclaration describes the function's name, what it does, and the parameters it expects.
# This information helps the model understand how and when to use each tool.

# Declaration for the 'add' function.
add_func = FunctionDeclaration(
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
subtract_func = FunctionDeclaration(
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
multiply_func = FunctionDeclaration(
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
divide_func = FunctionDeclaration(
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
math_tool = Tool(
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

# --- Helper Function to Extract Function Calls ---
# This function processes the model's response to extract the specific function calls it wants to make.
# It parses the response and returns a list of dictionaries, each containing a function name and its arguments.
def extract_function_calls(response: GenerationResponse) -> list[dict]:
    function_calls: list[dict] = []
    if response.candidates[0].function_calls:
        for function_call in response.candidates[0].function_calls:
            function_call_dict: dict[str, dict[str, Any]] = {function_call.name: {}}
            for key, value in function_call.args.items():
                function_call_dict[function_call.name][key] = value
            function_calls.append(function_call_dict)
    return function_calls

# --- Main Chat and Function Calling Loop ---
# This function orchestrates the conversation with the model.
# It sends the user's query, handles function calls requested by the model,
# executes the corresponding Python functions, and sends the results back to the model.
def send_chat_message(query):
    instruction_prompt = """You can perform arithmetic operations only. Only use the results that you learn from the tools."""
    prompt = instruction_prompt + "\n\n" + query 
    print("--------------------")
    print('>>> Input Prompt <<<')
    print("--------------------")
    print(prompt, "\n")

    # Send the initial prompt to the model.
    response = chat.send_message(prompt)

    # This loop continues as long as the model is requesting function calls.
    function_calling_in_process = True
    while function_calling_in_process:
        try:
            # Check if the model's response contains a function call.
            # If not, it's a final text response, and the 'except' block will be triggered.
            response_call_name = (response.candidates[0].content.parts[0].function_call.name)

            # Extract the function call details from the LLM response.
            # The details contain the function name and input arguments. 
            function_calls = extract_function_calls(response)

            print("----------------------")
            print('>>> Tool Selection <<<')
            print("----------------------")
            print(function_calls)

            # Process each function call requested by the model.
            function_responses = []  # Initialize as a list of lists
            for function_call in function_calls:
                for function_name, function_args in function_call.items():
                    if function_name in function_handler.keys():
                        # Call the appropriate Python function with the provided arguments.
                        params = {key: value for key, value in function_args.items()}

                        # Invoke a function
                        function_response = function_handler[function_name](params['numbers'])

                        # Append the function name and response as a pair to the list
                        function_responses.append([function_name, function_response])

                        print("\n---------------------")
                        print('>>> Tool Response <<<')
                        print("---------------------")
                        print(function_response, "\n")

            # Loop over multiple function calls to extract all API response contents
            processed_methods = set()  # Set to track processed methods
            parts = []  # Prepare parts to send

            for funct_name in function_calls:
                # Iterate through the keys:
                for key in funct_name.keys():
                    # Check if we've already processed this method
                    if key in processed_methods:
                        # Skip if method is already processed
                        continue
                    # Add the method to the processed set
                    processed_methods.add(key)

                    # Find all matching responses for the current function name in the list
                    matching_responses = [ response[1] for response in function_responses if response[0] == key]

                    # Check if there are multiple responses
                    if (isinstance(matching_responses, list) and len(matching_responses) > 0):
                        for content in matching_responses:  # Iterate over the list
                            parts.append(Part.from_function_response(name=key, response={"content": content}))

            # Send all API response back to Gemini to generate natural summary or another function call
            # If this does not have the '.function_call.name' method, the 'except' is triggered
            response = chat.send_message(parts)
            print("-----------------------------\n")

        except AttributeError:
            function_calling_in_process = False

    # Show the final natural language summary
    print("--------------------")
    print('>>> LLM response <<<')
    print("--------------------")
    print(response.text)



def orchestrate_chat(query: str):
    """
    Orchestrates a multi-turn conversation with the Gemini model, handling tool calls.
    """
    instruction_prompt = """You can perform arithmetic operations only. Only use the results that you learn from the tools."""
    prompt = f"{instruction_prompt}\n\n{query}"
    
    print("--------------------")
    print('>>> Input Prompt <<<')
    print("--------------------")
    print(prompt, "\n")

    # Start the conversation
    response = chat.send_message(prompt)

    #Loop as long as the model wants to call functions
    while True:
        # Check for a function call in the response
        if response.candidates and response.candidates[0].content.parts and response.candidates[0].content.parts[0].function_call:
            
            print("----------------------")
            print('>>> Tool Selection <<<')
            print(f"Model wants to use tools: {[fc.name for fc in response.candidates[0].function_calls]}")

            function_responses_to_send = []

            for function_call in response.candidates[0].function_calls:
                function_name = function_call.name
                if function_name in function_handler:
                    function_to_call = function_handler[function_name]
                    function_args = function_call.args
                    
                    print(f'\n>>> Executing: {function_name}({function_args}) <<<')
                    
                    tool_response = function_to_call(**function_args)
                    
                    print('>>> Tool Response <<<')
                    print(tool_response, "\n")

                    function_responses_to_send.append(
                        Part.from_function_response(
                            name=function_name,
                            response={"content": tool_response}
                        )
                    )
                else:
                    print(f"Error: Model requested unknown function '{function_name}'")
            
            # Send the tool responses back to the model
            response = chat.send_message(function_responses_to_send)
        
        else:
            # If there are no more function calls, print the final text response and exit the loop.
            print("--------------------")
            print('>>> LLM Response <<<')
            print("--------------------")
            print(response.text)
            break

# --- Main Execution Block ---
# This is the entry point of the script.
if __name__ == '__main__':
    PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT") # The Google Cloud Project
    LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1") # The location of execution e.g. "us-central1"

    MODEL = os.getenv("MODEL", "gemini-2.0-flash") # The model ID for the example

    # Initialize the Vertex AI SDK with the project and location.
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    # Load the LLM, specifying the model version and the tools it can use.
    gemini_model = GenerativeModel(
        MODEL, # Updated to a recommended model e.g. "gemini-2.0-flash"
        generation_config=GenerationConfig(temperature=0),
        tools=[math_tool],
    )

    # Start a new chat session with the model.
    chat = gemini_model.start_chat()

    # Send an initial prompt to begin the conversation.
    send_chat_message("Could you add all the numbers between 1 and 5?")

    # Send a more complex questions
    #send_chat_message("Could you add all the numbers between 1 and 5 and then multiply by 2?")
    #orchestrate_chat("Could you add all the numbers between 1 and 5?")

    #orchestrate_chat("Could you add all the numbers between 1 and 5 and then multiply by 2?")

    