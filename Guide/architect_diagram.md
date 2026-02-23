# Architectural Diagram

The following diagram illustrates the flow of data and control within the AI-Powered BDD Automation Framework, including the advanced AI Self-Healing and Chrome Session Persistence features.

```mermaid
graph TD
    A[User Story] -->|Upload/Paste| B[Frontend]
    B -->|API Request| C[Backend - FastAPI]

    C -->|Phase 1: Gherkin| D[LLM Service]
    D -->|BDD Content| E[Storage/BDD]

    C -->|Phase 2: Navigation Steps| D
    D -->|JSON Steps| F[Harvester Agent]

    subgraph "Harvester Agent (Playwright)"
        F1[Profile Loader] -->|Check Lock| F2{Cloned/Local?}
        F2 -->|If Locked| F3[Temp Profile]
        F2 -->|If Free| F4[Real Profile]
        F3 --> F5[Chrome Instance]
        F4 --> F5
        F5 -->|Execution| G[Target Web App]
        G -->|Failure/UI Change| F6[AI Healing Layer]
        F6 -->|Request Action| D
        D -->|New Selector/Action| F6
        F6 -->|Recovered Step| F5
        F5 -->|Recorded Selectors| F7[Trace Log Generator]
    end

    F7 -->|Trace Log| H[Storage/Trace Logs]

    C -->|Phase 4: Code Gen| D
    H --> D
    E --> D
    D -->|Python Script| I[Storage/Scripts]

    B -->|Run Test| J[Pytest Executor]
    I --> J
    J -->|Results| K[Allure Report]
    K -->|View| B
```

## Component Roles

- **Frontend**: User interface for management, configuration (Chrome paths), and viewing healing reports.
- **Backend**: Service orchestration, file management, and FastAPI host.
- **LLM Service**: Intelligent translation of requirements and real-time healing reasoning.
- **Harvester Agent**: Dynamic execution engine with session persistence and AI-driven recovery.
- **AI Healing Layer**: Captures DOM context and coordinates with LLM to resolve navigation blockers.
- **Pytest/Allure**: Standard testing framework and visual reporting tools.
