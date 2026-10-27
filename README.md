# Building Live Voice Agents

## Deploying Real-Time Multimodal AI Systems to Production

**Authors:** Heiko Hotz and Sokratis Kartakis

This repository contains the companion code for *Building Live Voice Agents*.
The examples cover live voice and visual interaction, agent frameworks,
Agent2Agent (A2A) communication, Model Context Protocol (MCP) tools, and an
integrated live agent system.

## Getting Started

1. Clone the repository:

   ```bash
   git clone https://github.com/multimodal-realtime-agents/code.git
   cd code
   ```

2. Choose a chapter. Start with [Chapter 3](Chapter-03/README.md) for the first
   live voice application. [Chapter 4](Chapter-04/README.md) adds visual input
   and tools; [Chapter 12](Chapter-12/README.md) combines the live interface,
   A2A specialists, and MCP tools.
3. Follow the selected chapter's README for prerequisites, environment setup,
   configuration, run commands, and verification steps.

Setup differs between chapters. Chapters 3, 4, 9, 11, and 12 each use their own
virtual environment, requirements file, and `.env.example` copied to
`.env.local` inside the chapter folder. Use the paths in that chapter's README.
The root `requirements.txt` and `dotenv.example` support other examples and are
not a universal setup for all chapters.

## Versions and Compatibility

The examples use the versions documented in the relevant chapter README and
requirements file. Use those dependency versions for the book's baseline;
later models or dependencies may require changes.

## Book Chapters

### Part 1: Foundations of Modern AI Systems

1. [Intelligent Agents and Collaborative AI](Chapter-01)
2. Understanding Multimodality: Beyond Text

### Part 2: Building Live, Interactive Experiences with Real-Time Multimodal APIs

3. [Architecting for Real-Time AI Interaction](Chapter-03)
4. [Advanced Live Interactions: Video, Tools, and System Instructions](Chapter-04)

### Part 3: Architecting and Implementing Agentic Systems

5. Core Components of an Agent Framework
6. [Designing and Building Agents](Chapter-06)
7. [Multi-Agent Systems: Collaboration and Orchestration](Chapter-07)

### Part 4: Enabling Interoperability with Open Protocols

8. The Agent2Agent Protocol
9. [Implementing A2A-Compliant Agents](Chapter-09)
10. The Model Context Protocol: Standardizing Tool Interaction
11. [Implementing MCP-Enabled Agents and Tool Servers](Chapter-11)

### Part 5: Synthesizing Live, Multi-Agent, Multi-Protocol Systems

12. [Reference Architecture: An Integrated Live Agent System](Chapter-12)
13. Asynchronous Operations and Long-Running Tasks in an Integrated Agent System
14. Designing User Experience for a Live, Multimodal, Multi-Agent System

### Part 6: Productionizing

15. The Birth of AgentOps: Introduction to an Agent Operationalization Platform
16. Evaluation and Testing of Live Agent Systems
17. Managing Tools at Scale
18. Sharing and Governing Agents as Services and Reusable Components
19. Security, Privacy, and Responsible AI
20. Deployment and Scaling the Integrated System

## License

This project is licensed under the Apache License, Version 2.0 - see the [LICENSE](LICENSE) file for details.
