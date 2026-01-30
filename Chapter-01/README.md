# Chapter 1: Foundations of Modern AI Systems

This folder contains the code examples for **Chapter 1: Intelligent Agents and Collaborative AI**.

## Overview
The examples demonstrate the evolution of AI agents from simple text generation to active entities capable of executing code and calling functions. We explore both manual and automatic function calling mechanisms using the Gemini API.

## Contents
- **`agent-with-automatic-function-calling.py`**: A clean, modern implementation of an agent that uses Gemini's automatic function calling capability. The model decides when to call tools (math functions), and the library handles the execution and history management.
- **`agent-with-manual-function-calling.py`**: A deep-dive implementation showing the "under the hood" mechanics of function calling. It explicitly defines the `FunctionDeclaration`, handles the tool loop, executes Python functions based on model requests, and manages the conversation history manually.

## Key Concepts
- **Tools**: Collections of functions (add, subtract, multiply, divide) provided to the model.
- **Function Calling**: How the model "asks" to execute code instead of just generating text.
- **Agent Loop**: The cycle of User Input -> Model decision -> Tool Execution -> Model Response.
