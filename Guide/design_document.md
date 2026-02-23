# Design Document: AI-Powered BDD Automation Framework

## Overview

This framework automates the creation of BDD (Behavior Driven Development) tests from plain English user stories. It uses Large Language Models (LLMs) to understand requirements, an AI-enhanced "Harvester Agent" to discover stable web element locators through real-time healing, and a code generator to produce production-grade Playwright Python scripts.

## System Architecture

### 1. Frontend (React + Vite)

- **UploadTab**: Workspace for story processing. Features a sticky "Data Documents" sidebar and a real-time "AI Healing Report" to track automated repairs during generation.
- **ExecutionTab**: Dashboard for script management, manual self-healing triggers, and Allure report visualization.
- **SettingsModal**: Central configuration for LLM providers (Gemini, OpenAI, DeepSeek, Ollama) and local Chrome environment paths.

### 2. Backend (FastAPI)

- **API Layer**: Orchestrates the multi-phase generation pipeline and manages background execution jobs.
- **Harvester Agent**: An advanced Playwright-based agent that performs "Smart Tracing":
    - **Session Persistence**: Detects locked Chrome profiles and automatically clones them to temporary directories to maintain login states.
    - **Real-time AI Healing**: If a step fails, the agent captures a simplified DOM snapshot and screenshot, calling the LLM to find a semantic match (e.g., "Sign In" vs "Login") and continue the flow.
    - **Stable Selector Engine**: Prioritizes `data-testid`, `id`, and stable ARIA attributes over fragile positional XPaths.
- **LLM Service**: Provides the reasoning layer for BDD translation, navigation step extraction, and real-time healing decisions.

## Generation Workflow

1. **Story to BDD**: LLM converts user story to Gherkin feature.
2. **BDD to Navigation**: LLM extracts atomic navigation steps (Click, Type, Goto, Validate).
3. **Smart Harvesting**: 
    - Harvester launches Chrome with profile cloning support.
    - Executes steps with real-time AI recovery for UI/flow changes.
    - Records a detailed Trace Log containing stable selectors and screenshots.
4. **Code Generation**: LLM uses the BDD content and the healed Trace Log to generate a Playwright Python script using the Page Object Model (POM).

## Key Features

- **Autonomous Healing**: The agent thinks in business goals, not just fixed selectors, allowing it to survive UI refactors.
- **Chrome Session Persistence**: Seamlessly uses existing browser profiles, even when they are currently in use.
- **Production-Grade Selectors**: Strictly avoids absolute XPaths (`/html/body/...`), producing resilient, maintainable code.
- **Data-Driven Testing**: Detects data files mentioned in stories and generates the corresponding validation logic.
- **Comprehensive Reporting**: Integrated Allure reports and generation-time healing summaries.
