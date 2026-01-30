# Chapter 7: Multi-Agent Systems

This folder contains the code examples for **Chapter 7: Multi-Agent Systems: Collaboration and Orchestration**.

## Overview
This chapter tackles the complexity of systems where multiple agents must work together. It demonstrates orchestration patterns, delegation, and how to build a "Teaching Assistant" system composed of specialized sub-agents.

## Contents
- **`chapter7_main.py`**: The orchestrator script.
- **`agent_teaching_assistant/`**: The multi-agent definitions.

## How to Run

### Prerequisites
1.  **Google Cloud Project**: Ensure Vertex AI API is enabled.
2.  **Environment Variables**: Create a `.env` file in this directory:
    ```env
    GOOGLE_CLOUD_PROJECT=your-project-id
    GOOGLE_CLOUD_LOCATION=us-central1
    MODEL=gemini-2.5-flash
    ```

### Installation
Install the Google Agent Development Kit and other dependencies:
```bash
pip install google-adk google-genai python-dotenv
```

### Execution
Run the main teaching assistant orchestration example:
```bash
python chapter7_main.py
```
*This will start the multi-agent system and run through the predefined conversation flow.*
