# Chapter 6: Designing and Building Agents

This folder contains the code examples for **Chapter 6: Designing and Building Agents**.

## Overview
This chapter illustrates the practical implementation of agents using the Agent Development Kit (ADK). It moves from basic agent configurations to a full-featured live agent capable of handling complex interactions.

## Contents
- **`basic_agent/`**: Examples of simple agents (ADK basics).
- **`live_agent/`**: A complete, production-ready ADK agent.

## How to Run

### Basic Agent Examples
These examples demonstrate core ADK concepts.

1.  **Navigate to the directory**:
    ```bash
    cd basic_agent
    ```
2.  **Setup Environment**:
    Create a `.env` file with `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION`.
3.  **Run Examples**:
    ```bash
    # Run the basic section 1 example
    python section1_main_basic.py
    
    # Run the single agent example
    python section2_main_single_agent.py
    ```

### Live Agent Application
This is a full-stack application similar to Chapter 3 but built with ADK.

1.  **Navigate to the directory**:
    ```bash
    cd live_agent/backend
    ```
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Start Backend**:
    ```bash
    python backend.py
    ```
4.  **Start Frontend**:
    In a new terminal, navigate to `live_agent/frontend` and run:
    ```bash
    python -m http.server 8000
    ```
5.  **Access**: Open [http://localhost:8000](http://localhost:8000).

*See `live_agent/README.md` for more detailed instructions.*
