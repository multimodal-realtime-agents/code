# Chapter 1: Foundations of Modern AI Systems

This folder contains the code examples for **Chapter 1: Intelligent Agents and Collaborative AI**.

## Overview
The examples demonstrate the evolution of AI agents from simple text generation to active entities capable of executing code and calling functions. We explore both manual and automatic function calling mechanisms using the Gemini API.

## Contents
- **`agent-with-automatic-function-calling.py`**: A clean, modern implementation of an agent that uses Gemini's automatic function calling capability.
- **`agent-with-manual-function-calling.py`**: A deep-dive implementation showing the "under the hood" mechanics of function calling.

## How to Run

### Prerequisites
1.  **Google Cloud Project**: You need a Google Cloud Project with the Vertex AI API enabled.
2.  **Environment Variables**: Create a `.env` file in the **root of the repository** (or in this folder) with the following:
    ```env
    GOOGLE_CLOUD_PROJECT=your-project-id
    GOOGLE_CLOUD_LOCATION=us-central1
    MODEL=gemini-2.5-flash
    ```

### Installation
Install the required Python packages:
```bash
pip install google-genai python-dotenv
```

### Execution
Run the automatic function calling example:
```bash
python agent-with-automatic-function-calling.py
```

Run the manual function calling example:
```bash
python agent-with-manual-function-calling.py
```
