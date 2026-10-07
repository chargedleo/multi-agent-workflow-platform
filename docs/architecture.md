# System Architecture — Multi-Agent AI Workflow Automation Platform

This document describes the architectural foundation established in **Milestone 1** and outlines the roadmap toward the full multi-agent enterprise platform.

---

## 1. Milestone 1 Architecture

Milestone 1 proves that a multi-agent orchestration workflow built on **LangGraph** and **FastAPI** can process a complex business query through shared state and return validated, structured answers.

### 1.1 Milestone 1 Component Flow

```mermaid
flowchart TD
    User([User])
    UI["React + Vite Frontend\n(Port 5173)"]
    API["FastAPI REST API\n(Port 8000)"]
    
    subgraph LG ["LangGraph Orchestration Pipeline"]
        direction TB
        InitState["Initialize WorkflowState\n(request_id, query)"]
        Planner["Planner Agent\n(Deconstructs query into Goal & Steps)"]
        Researcher["Research Agent\n(Reasons over steps, generates findings)"]
        Responder["Response Agent\n(Synthesizes findings into final output)"]
        
        InitState --> Planner
        Planner --> Researcher
        Researcher --> Responder
    end

    Response["Structured WorkflowAPIResponse\n(request_id, answer, key_points, confidence)"]
    DB[("PostgreSQL\n(Health Check Foundation)")]

    User -->|Submits Query| UI
    UI -->|POST /api/v1/workflows| API
    API -->|run_workflow| InitState
    Responder -->|Return Final State| API
    API -->|JSON Response| UI
    API -.->|Health Check / Connect| DB
```

---

## 2. Shared LangGraph State Design

The core of multi-agent collaboration in this platform is strongly typed, shared state represented by `WorkflowState`:

```python
class WorkflowState(TypedDict, total=False):
    # Core attributes (Milestone 1)
    request_id: str
    user_query: str
    plan: Optional[Dict[str, Any]]                # Validated Plan
    research_results: Optional[Dict[str, Any]]    # Validated ResearchResult
    intermediate_results: Annotated[List[Dict[str, Any]], operator.add]
    final_answer: Optional[Dict[str, Any]]        # Validated WorkflowResponse
    errors: Annotated[List[str], operator.add]   # Accumulated errors
    metadata: Dict[str, Any]

    # Future extension points (Milestones 2+)
    retrieved_documents: Optional[List[Dict[str, Any]]]
    analysis_results: Optional[Dict[str, Any]]
    validation_results: Optional[Dict[str, Any]]
    tool_calls: Optional[List[Dict[str, Any]]]
    approval_status: Optional[str]
```

### Key State Characteristics:
1. **Additive Reducers (`operator.add`)**: Fields like `errors` and `intermediate_results` append state updates from every node rather than overwriting previous entries.
2. **Immutability & Safety**: Each agent receives the full state, inspects earlier outputs, produces its typed output, and returns only the delta dictionary.
3. **Decoupled Extensions**: Later agents (e.g., Document Retrieval, Data Analysis) can add fields directly into the existing state schema without requiring refactoring of existing agents.

---

## 3. Agent Responsibilities & Schemas

### 3.1 Planner Agent (`backend/app/agents/planner.py`)
- **Input**: `state["user_query"]`
- **Output Schema**: `Plan`
  - `goal: str`: Objective extracted from the query.
  - `steps: List[str]`: Chronological, actionable steps.
- **Responsibility**: Deconstructs high-level business queries into structured execution milestones.

### 3.2 Research Agent (`backend/app/agents/researcher.py`)
- **Input**: `state["plan"]`, `state["user_query"]`
- **Output Schema**: `ResearchResult`
  - `findings: List[str]`: In-depth analytical points addressing each planned step.
  - `assumptions: List[str]`: Assumptions explicitly recognized during reasoning.
  - `unanswered_questions: List[str]`: Open questions or variables requiring more context.
- **Responsibility**: In Milestone 1, functions as an LLM-based reasoning agent over the plan. In Milestone 3+, will leverage external tools and MCP servers.

### 3.3 Response Agent (`backend/app/agents/responder.py`)
- **Input**: `state["user_query"]`, `state["plan"]`, `state["research_results"]`
- **Output Schema**: `WorkflowResponse`
  - `request_id: str`: Propagation of the workflow run UUID.
  - `answer: str`: Comprehensive synthesized response.
  - `key_points: List[str]`: Bullet points summarizing actionable takeaways.
  - `confidence: float`: Calibrated confidence rating between `0.0` and `1.0`.
- **Responsibility**: Synthesizes agent work into a structured executive report.

---

## 4. Central LLM Abstraction (`backend/app/services/llm.py`)

To prevent tight coupling to a single AI provider, LLM instantiation is managed by a central factory:
- **Configurable Provider**: Controlled via `LLM_PROVIDER` (`openai`, `azure`, `ollama`, or `mock`).
- **OpenAI-Compatible Support**: Accepts custom `LLM_BASE_URL` (compatible with vLLM, LMStudio, local Ollama, etc.).
- **Built-in Mock Model (`MockChatModel`)**: A deterministic model that simulates structured output without requiring live API keys or incur costs during automated CI/CD and testing.
- **Resilient Fallback Parsing**: When native `.with_structured_output()` fails or is unsupported by an endpoint, the service automatically falls back to schema-guided JSON prompting and `PydanticOutputParser`.

---

## 5. PostgreSQL Persistence Architecture (Milestone 2)

Milestone 2 introduces enterprise persistence for multi-agent workflows, transforming transient LangGraph executions into durable audit trails.

### 5.1 Database Entity-Relationship Diagram

```mermaid
erDiagram
    WORKFLOW_RUNS ||--o{ WORKFLOW_STEPS : "contains"
    
    WORKFLOW_RUNS {
        uuid id PK
        uuid request_id "Indexed"
        text user_query
        string status "Indexed: PENDING, RUNNING, COMPLETED, FAILED"
        timestamptz started_at "Indexed"
        timestamptz completed_at
        bigint duration_ms
        text final_answer
        jsonb key_points
        float confidence
        jsonb plan
        jsonb research_results
        jsonb errors
        jsonb metadata
        timestamptz created_at "Indexed"
        timestamptz updated_at
    }

    WORKFLOW_STEPS {
        uuid id PK
        uuid run_id FK "References workflow_runs.id ON DELETE CASCADE"
        string agent_name "planner, researcher, responder"
        integer step_order "1, 2, 3"
        string status "PENDING, RUNNING, COMPLETED, FAILED"
        timestamptz started_at
        timestamptz completed_at
        bigint duration_ms
        jsonb input_data
        jsonb output_data
        text error
        timestamptz created_at
    }
```

### 5.2 Workflow & Step Lifecycle

The execution lifecycle transitions through deterministic states:

```mermaid
stateDiagram-v2
    [*] --> PENDING: POST /api/v1/workflows (create_run)
    PENDING --> RUNNING: start_workflow_run
    
    state RUNNING {
        [*] --> PlannerStep
        PlannerStep --> ResearcherStep: step complete
        ResearcherStep --> ResponderStep: step complete
        ResponderStep --> [*]: step complete
        
        PlannerStep --> StepFailed: error
        ResearcherStep --> StepFailed: error
        ResponderStep --> StepFailed: error
    }
    
    RUNNING --> COMPLETED: All steps finish successfully
    RUNNING --> FAILED: Agent exception / step failure
    StepFailed --> FAILED
    
    COMPLETED --> [*]
    FAILED --> [*]
```

### 5.3 Architectural Rationale: Separation of LangGraph State vs. DB Persistence

1. **In-Memory LangGraph State (`WorkflowState`)**:
   - Optimized for ultra-low latency intra-agent message passing and fast functional transitions.
   - Preserves typed immutability and additive reducers (`operator.add`) during runtime execution.
   - Contains operational working memory and internal prompts without tying the execution loop to database write patterns.

2. **Durable Database Persistence (`WorkflowRun` & `WorkflowStep`)**:
   - Provides an asynchronous, queryable audit log accessible across restarts and external services.
   - Captures wall-clock execution metrics (`duration_ms`), agent latency, error traces, and input/output snapshots.
   - Enables pagination, history filtering, performance observability, and future replay capabilities.

3. **Transaction Boundary Decoupling**:
   - Database operations use isolated, short-lived transactions (`get_db_context()`) at step entry and step completion.
   - **Crucially, database transactions are never held open across external LLM network calls**. Step records are created immediately before invocation and committed, then updated upon completion in a separate transaction.

---

## 6. Target Future Architecture (Milestones 3 — 6)

The diagram below illustrates the target architecture to be incrementally implemented in future milestones:

```mermaid
flowchart TD
    User([User]) --> UI["React Monitoring Dashboard"]
    UI --> API["FastAPI Gateway"]
    API --> Checkpointer[("PostgreSQL Persistence & History\n(workflow_runs & workflow_steps)")]
    
    subgraph MultiAgentSystem ["Full Multi-Agent Orchestration"]
        direction TB
        PlannerAgent["Planner Agent"]
        
        subgraph ParallelExecution ["Specialized Investigation Agents"]
            ResearchAgent["Research Agent\n(Web & External Search)"]
            DocAgent["Document Retrieval Agent\n(FAISS Vector Store)"]
            DataAgent["Data Analysis Agent\n(Python Sandbox / Code Execution)"]
        end
        
        ValidationAgent["Validation & Critique Agent"]
        HITL{"Human-in-the-Loop\nApproval Gate"}
        ResponseAgent["Response Agent"]
        
        PlannerAgent --> ParallelExecution
        ParallelExecution --> ValidationAgent
        ValidationAgent -->|Needs Approval| HITL
        ValidationAgent -->|Approved| ResponseAgent
        HITL -->|Approved| ResponseAgent
        HITL -->|Rejected / Revised| PlannerAgent
    end

    API --> MultiAgentSystem
    MultiAgentSystem -.-> Checkpointer
    
    subgraph ExternalTools ["Tool Integration & MCP Layer"]
        FAISS[("FAISS Vector DB")]
        MCP["MCP Protocol Servers"]
        DocAgent -.-> FAISS
        ResearchAgent -.-> MCP
    end
```

### Future Milestone Roadmap:
- **Milestone 3**: Document Retrieval Agent with FAISS Vector Store, document ingestion, and chunked vector embeddings.
- **Milestone 4**: Data Analysis Agent with sandboxed function calling, MCP protocol tools, and code execution.
- **Milestone 5**: Validation Agent and Human-in-the-Loop (HITL) pause/resume approval gates leveraging persistent run IDs.
- **Milestone 6**: Advanced monitoring dashboard with streaming execution, run inspection, and agent analytics.
