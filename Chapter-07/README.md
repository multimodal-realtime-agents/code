# Chapter 7: Multi-Agent Systems

This folder contains the code examples for **Chapter 7: Multi-Agent Systems: Collaboration and Orchestration**.

## Overview
This chapter tackles the complexity of systems where multiple agents must work together. It demonstrates orchestration patterns, delegation, and how to build a "Teaching Assistant" system composed of specialized sub-agents.

## Contents
- **`chapter7_main.py`**: The main entry point for the orchestrated system. It initializes the `root_agent` and manages the user session loop.
- **`agent_teaching_assistant/`**: Contains the logic for the specific agents in this system (e.g., a root dispatcher, a math specialist, a quiz generator).
- **`section1_main_basic.py`**: Basic example of multi-agent setup.
- **`section2_main_single_agent.py`**: Single agent baseline for comparison.
- **`sectionbonus_agent_deployment.py`**: Advanced topics on deploying multi-agent systems.

## Key Concepts
- **Orchestration**: A central agent routing tasks to sub-agents.
- **Handoffs**: Transferring control from one agent to another.
- **Specialization**: Designing agents with narrow, deep expertise (e.g., "Math Agent" vs "History Agent").
