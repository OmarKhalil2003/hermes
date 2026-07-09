# Platform Task Ticket Backlog (2-Developer Partition)

This backlog organizes the remaining development phases of the **AI Research Assistant Platform** (Phases 2-21 in `IMPLEMENTATION_ROADMAP.md`) into production-style development tickets. It assigns roles based on the team's domain partitioning:
- **Developer A**: Backend, Database, Async Task Queues, Vector Indexing, DevOps, MLOps, Observability.
- **Developer B**: Next.js UI, React State, LangGraph Workflows, Prompts, Client-side API hooks, Reports.

---

## 🗺️ Milestone 1: Data & Security Foundation

### Ticket `TASK-001`: PostgreSQL DB Schema, Migrations, and Repository Classes
- **Title**: `feat(db): implement database schema, migrations, and repository layer`
- **Story Points**: 8
- **Assignee**: **Developer A**
- **Description**: Configure PostgreSQL persistence, set up database engines via SQLAlchemy 2.0 asyncpg driver, configure Alembic for automated migrations, and implement Repository patterns for core domain entities.
- **Prerequisites**: Phase 1 initialization.
- **Checklist**:
  - [ ] Configure AsyncEngine & `sessionmaker` in `backend/core/database.py`.
  - [ ] Design declarative Base model and define SQLAlchemy schemas for: `Users`, `Roles`, `Permissions`, `Sessions`, `Documents`, `Chunks`, `Conversations`, `Messages`, `TrainingJobs`, `Evaluations`, and `AuditLogs`.
  - [ ] Initialize Alembic, configure `env.py` to auto-detect target models, and generate the initial migration script.
  - [ ] Implement generic BaseRepository class and typed subclasses (e.g., `UserRepository`, `DocumentRepository`) in `backend/repositories/`.
  - [ ] Write async unit tests for repository CRUD actions utilizing a sqlite-in-memory/test-db connection fixture.
- **Acceptance Criteria**:
  - Alembic migrations run successfully with `alembic upgrade head`.
  - Strict type hints apply to all repositories, verified by `mypy`.
  - Unit tests achieve >95% code coverage for the repository layer.

---

### Ticket `TASK-002`: JWT Authentication, Session Management, and RBAC Guards
- **Title**: `feat(auth): implement oauth2 token flow, jwt validation, and rbac guards`
- **Story Points**: 5
- **Assignee**: **Developer A**
- **Description**: Secure the API using OAuth2 password bearer flow, implement JWT generation (with refresh tokens), hash passwords using bcrypt, and write Role-Based Access Control (RBAC) dependency injection decorators.
- **Prerequisites**: `TASK-001` (User/Session models).
- **Checklist**:
  - [ ] Implement password hashing utilities using `passlib[bcrypt]`.
  - [ ] Create JWT helper functions (encode, decode, validate) with configurable exp dates in `backend/core/security.py`.
  - [ ] Implement user login endpoint returning Access Token and Refresh Token.
  - [ ] Write FastAPI dependency injectors for `get_current_user`, `get_active_user`, and `check_permissions(permission_name)`.
  - [ ] Create integration tests covering user registration, valid login, invalid login, unauthorized requests, and expired token refreshes.
- **Acceptance Criteria**:
  - Unauthenticated users receive `401 Unauthorized` for protected routes.
  - Users with insufficient permissions receive `403 Forbidden` when attempting access.
  - JWT tokens use strong signature verification.

---

### Ticket `TASK-003`: User Authentication Frontend Pages
- **Title**: `feat(ui): implement login, register, and token management frontend client`
- **Story Points**: 5
- **Assignee**: **Developer B**
- **Description**: Create the frontend user interfaces for authentication (login and register) using TailwindCSS and shadcn/ui. Setup local state storage for JWT and API routing interception.
- **Prerequisites**: `TASK-002` (Auth API endpoints).
- **Checklist**:
  - [ ] Setup Axios/Fetch HTTP interceptors to append `Bearer <token>` to outbound requests and handle `401` token refreshes.
  - [ ] Create Login page form with input validations.
  - [ ] Create Register page form with password confirmation.
  - [ ] Implement Route Guards (Protected Routes redirection client-side).
- **Acceptance Criteria**:
  - Responsive dark/light theme screens designed.
  - Successful logins persist JWT securely and redirect users to Dashboard.

---

## 🗄️ Milestone 2: Search & Retrieval Engine (RAG)

### Ticket `TASK-004`: Asynchronous Document Ingestion, OCR, Parsing, and Chunking Pipeline
- **Title**: `feat(rag): implement celery-driven document ingestion, parsing, OCR, and chunking`
- **Story Points**: 8
- **Assignee**: **Developer A** (Worker/Ingestion backend) & **Developer B** (Upload API & metadata parsing)
- **Description**: Set up the celery backend. When a document is uploaded, run a Celery task to parse (PDF, DOCX, PPTX, CSV), execute OCR on scanned images, segment text into semantic chunks with metadata filters, and check for duplicates.
- **Prerequisites**: `TASK-001`.
- **Checklist**:
  - [ ] Create Celery app configuration and task handlers in `backend/celery_worker/tasks.py`.
  - [ ] Implement file parser handlers using `PyPDF2`/`pdfplumber`, `python-docx`, `python-pptx`, and `tesseract` for OCR parsing.
  - [ ] Implement recursive text splitter with overlap settings in `rag/chunking.py`.
  - [ ] Extract document metadata (author, created date, headers, filetype).
  - [ ] Implement SHA-256 duplicate checking against pre-calculated database checksums.
  - [ ] Add async REST endpoints for document upload, upload status query, and document deletion.
- **Acceptance Criteria**:
  - Document uploads parse successfully and execute asynchronously.
  - Text chunks and metadata populate database entries upon task completion.

---

### Ticket `TASK-005`: Qdrant Vector Search and Hybrid BM25/Dense Retrieval Engine
- **Title**: `feat(rag): implement hybrid search with qdrant, bm25, and cross-encoder reranker`
- **Story Points**: 8
- **Assignee**: **Developer A**
- **Description**: Configure a hybrid search pipeline combining sparse (BM25) search and dense (Qdrant vectors) search, then apply a Cross-Encoder to re-rank results.
- **Prerequisites**: `TASK-004`.
- **Checklist**:
  - [ ] Set up Qdrant client connection pool and create index collections.
  - [ ] Integrate SentenceTransformers (e.g. `all-MiniLM-L6-v2`) to embed chunks during ingestion.
  - [ ] Implement local BM25 indexing (e.g., using `rank_bm25`).
  - [ ] Implement Reciprocal Rank Fusion (RRF) or normalization to merge BM25 and Dense search outputs.
  - [ ] Integrate CrossEncoder (e.g. `ms-marco-MiniLM-L-6-v2`) to re-rank the merged top-K results.
  - [ ] Implement search routes supporting metadata filtering (document ID, upload date, owner).
- **Acceptance Criteria**:
  - Hybrid query return times remain <150ms.
  - Re-ranked documents exhibit higher semantic relevance scores.

---

### Ticket `TASK-006`: Document Management and Search UI Pages
- **Title**: `feat(ui): implement document management grid and semantic search interface`
- **Story Points**: 5
- **Assignee**: **Developer B**
- **Description**: Create user screens to upload files (with drop-zone, drag-and-drop, and upload progress indicators), list existing files in a table, and perform keyword/semantic queries.
- **Prerequisites**: `TASK-003`, `TASK-005`.
- **Checklist**:
  - [ ] Build file drag-and-drop upload card component.
  - [ ] Build files table component displaying filename, status, size, parsing date, and action triggers.
  - [ ] Build search console input with interactive search-results card grids, exposing matched metadata tags and matching confidence scores.
- **Acceptance Criteria**:
  - Upload status polls state progress updates correctly.
  - Search results display highlighting snippets.

---

## 🤖 Milestone 3: LangGraph & Multi-Agent Orchestration

### Ticket `TASK-007`: LangGraph Multi-Agent Orchestrator
- **Title**: `feat(agents): implement multi-agent supervisor orchestrator via langgraph`
- **Story Points**: 13
- **Assignee**: **Developer B** (Graph configuration and state variables) & **Developer A** (Model Service and database state checkpointing)
- **Description**: Construct a multi-agent workflow using LangGraph. The Supervisor routes tasks based on query intent to specific agents: Retriever Agent, Research Agent, Reviewer Agent, and Report Agent.
- **Prerequisites**: `TASK-005`.
- **Checklist**:
  - [ ] Define global `AgentState` schema inside `agents/state.py`.
  - [ ] Write Supervisor agent node logic using LangChain LLM prompts.
  - [ ] Implement member agent nodes (Retriever node, Research node, Reviewer node, Report node).
  - [ ] Build graph layout, register edge transitions, and define compile checkpoints via PostgreSQL database state stores.
  - [ ] Implement streaming API endpoints to stream token outputs and agent transition steps.
- **Acceptance Criteria**:
  - Multi-agent states transition sequentially, avoiding infinite loops.
  - Token results stream to clients chunk-by-chunk in real time.

---

### Ticket `TASK-008`: Custom Action Tools for Agent Execution
- **Title**: `feat(tools): build python executor, sql compiler, and pdf report generator`
- **Story Points**: 8
- **Assignee**: **Developer A**
- **Description**: Implement secure, injectable tools for agents: Python sandbox executor, SQL query compiler, Chart generator (matplotlib), and a PDF/PowerPoint report generator.
- **Prerequisites**: `TASK-007`.
- **Checklist**:
  - [ ] Implement Python executor running scripts in isolated subprocesses/sandboxes with resource constraints.
  - [ ] Implement Natural Language to SQL converter mapping DB metadata schemas securely (prevent SQL injection).
  - [ ] Implement Matplotlib/Seaborn graph-drawing tool returning base64 images.
  - [ ] Implement PDF and PowerPoint builders converting agent outputs into exportable files.
  - [ ] Register all items to `tools/registry.py`.
- **Acceptance Criteria**:
  - Execution runs with resource memory caps.
  - Generated PDFs format layout structures successfully.

---

### Ticket `TASK-009`: Interactive Chat & Report Generation UI
- **Title**: `feat(ui): implement markdown stream chat panel and downloadable reports dashboard`
- **Story Points**: 8
- **Assignee**: **Developer B**
- **Description**: Build the primary workspace screen: interactive chat panel with markdown support, citation popups, agent thought-process steps, and a side dashboard listing generated reports.
- **Prerequisites**: `TASK-006`, `TASK-007`.
- **Checklist**:
  - [ ] Build chat message container parsing Markdown, code blocks, and embedded base64 graphics.
  - [ ] Build expandable "Thought Process" container detailing agent node transitions.
  - [ ] Build citation tooltip displaying raw source document text.
  - [ ] Create Report library tab displaying files with quick download options.
- **Acceptance Criteria**:
  - Token rendering streams smoothly.
  - Citations click to highlight source document snippets.

---

## 📈 Milestone 4: Fine-Tuning, MLOps, & Evaluation

### Ticket `TASK-010`: Model Fine-Tuning Pipeline (QLoRA) & MLflow Tracking
- **Title**: `feat(ml): implement dataset compiler and qlora fine-tuning pipeline logged to mlflow`
- **Story Points**: 8
- **Assignee**: **Developer A**
- **Description**: Build a pipeline to compile instruction pairs from user conversations and documents, run a QLoRA fine-tuning loop on Qwen2.5-3B-Instruct using PEFT/TRL, and log progress to MLflow.
- **Prerequisites**: `TASK-001`.
- **Checklist**:
  - [ ] Build preprocessing script parsing input formats into instruction-response JSON templates.
  - [ ] Configure QLoRA training script load models in 4-bit precision (using `bitsandbytes`).
  - [ ] Integrate PyTorch `Trainer` hooks to log training loss, learning rate, and checkpoints to MLflow tracking services.
  - [ ] Implement script merging PEFT adapters back into base models.
- **Acceptance Criteria**:
  - Model weights save correctly to MLflow model registry.
  - Training metrics log successfully without GPU memory overflows.

---

### Ticket `TASK-011`: Automated Model Evaluation Pipeline
- **Title**: `feat(ml): implement automated evaluation comparing base vs fine-tuned models`
- **Story Points**: 8
- **Assignee**: **Developer A** (Backend pipeline) & **Developer B** (Evaluation dataset config)
- **Description**: Write a benchmark evaluation script using ROUGE, BLEU, BERTScore, and RAGAS framework metrics to compare base LLM performance with fine-tuned model performance.
- **Prerequisites**: `TASK-010`.
- **Checklist**:
  - [ ] Set up evaluation data configurations in JSON format (Query, Ground Truth, Context).
  - [ ] Implement calculators for ROUGE, BLEU, and BERTScore.
  - [ ] Integrate RAGAS metrics (Faithfulness, Answer Relevance, Context Recall).
  - [ ] Write a comparison reporter logging results directly as run artifacts in MLflow.
- **Acceptance Criteria**:
  - Comparison charts compile and export successfully.
  - Evaluation results log into the MLflow experiment dashboard.

---

### Ticket `TASK-012`: Model Management & System Metric Dashboard UI
- **Title**: `feat(ui): implement model deployment panel and evaluation benchmark dashboards`
- **Story Points**: 5
- **Assignee**: **Developer B**
- **Description**: Create a management UI screen detailing MLflow experiment runs, comparing model benchmark evaluations, and selecting active models/adapters to handle API traffic.
- **Prerequisites**: `TASK-011`.
- **Checklist**:
  - [ ] Build training job progress monitoring bar dashboard.
  - [ ] Build model comparative chart interface.
  - [ ] Build deployment controller selecting the active adapter loaded by the model service.
- **Acceptance Criteria**:
  - Active adapter changes successfully route new chat queries to the targeted model adapter.

---

## 🚀 Milestone 5: Monitoring, Deployment, & QA

### Ticket `TASK-013`: Observability Stack (OpenTelemetry, Jaeger, Prometheus, Grafana)
- **Title**: `feat(ops): implement distributed tracing, prometheus metrics, and grafana dashboards`
- **Story Points**: 5
- **Assignee**: **Developer A**
- **Description**: Hook up OpenTelemetry metrics/traces from the FastAPI app and Celery workers, route trace Spans to Jaeger, expose Prometheus metrics endpoints, and construct Grafana performance dashboards.
- **Prerequisites**: Phase 1 docker configurations.
- **Checklist**:
  - [ ] Instrument FastAPI application endpoints using `OpenTelemetryMiddleware`.
  - [ ] Export traces via OTLP grpc exporter to Jaeger.
  - [ ] Implement API request metrics (latency histogram, request rate counters, error counters).
  - [ ] Create pre-configured Grafana JSON dashboards plotting system latencies, CPU/GPU resource utilization, and error rates.
- **Acceptance Criteria**:
  - Metrics scrape correctly at `/metrics`.
  - Complete request trace paths show up in Jaeger UI.

---

### Ticket `TASK-014`: Production Kubernetes Deployment Manifests
- **Title**: `feat(ops): create kubernetes deployment files, configurations, and service graphs`
- **Story Points**: 5
- **Assignee**: **Developer A**
- **Description**: Translate local Docker Compose services into Kubernetes manifests (Deployments, Services, ConfigMaps, Secrets, Ingress) supporting scale capabilities.
- **Prerequisites**: Docker compose configurations.
- **Checklist**:
  - [ ] Write manifests for databases (`postgres`, `redis`, `rabbitmq`, `qdrant`).
  - [ ] Write manifests for applications (`backend`, `celery-worker`, `frontend`).
  - [ ] Configure Horizontal Pod Autoscalers (HPA) targeting app deployments based on resource usage.
  - [ ] Setup ConfigMaps and secret encryptions.
- **Acceptance Criteria**:
  - Entire stack deploys cleanly inside local minikube / cloud cluster.
  - Live services route external traffic through ingress controllers.

---

### Ticket `TASK-015`: Load Testing, Final Verification, and Repository Handover
- **Title**: `chore(qa): perform load testing, final validation, and technical documentation`
- **Story Points**: 5
- **Assignee**: **Developer A** & **Developer B** (Pair)
- **Description**: Run comprehensive system verification. Run load testing scripts (e.g. using `locust`), write complete API documentation, build final screenshots/GIFs, and finalize the repository readme.
- **Prerequisites**: All previous tasks.
- **Checklist**:
  - [ ] Run automated concurrent user simulations tracking response capacities.
  - [ ] Verify unit test coverage targets satisfy the 95% threshold.
  - [ ] Generate database ERD schema maps and multi-agent sequence diagrams.
  - [ ] Package deployment guides and screenshots into doc assets.
- **Acceptance Criteria**:
  - Full codebase builds without error, typecheck passes, and tests run.
  - Readme contains setup instructions and system architecture charts.
