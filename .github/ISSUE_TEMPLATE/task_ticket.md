---
name: 📋 Task Ticket
about: Define a structured development task for implementation.
title: "[TASK] "
labels: ["task"]
assignees: ""
---

## Milestone / Phase Link
Link to the target implementation phase (e.g. Phase 2: Database Layer).

## Description
Provide a clear description of the task requirements and technical scope.

## Technical Details / Guidelines
- Target folders: [e.g. `backend/`, `rag/`]
- Classes/Interfaces to implement or modify.
- Design patterns or architecture considerations (SOLID, DI, repository pattern).

## Acceptance Criteria
- [ ] Logic implemented completely (no placeholders).
- [ ] Strict type hinting (no `Any`, Mypy passes).
- [ ] Formatting (`black`) and Linting (`ruff`) checks pass.
- [ ] Unit & Integration tests written and passing (target coverage 95%).
- [ ] Docker builds run successfully.
- [ ] Documentation updated (README + Google docstrings).
