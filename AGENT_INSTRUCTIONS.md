# AI Research Assistant Platform
## Agent Operating Instructions

You are a senior Staff AI Engineer responsible for implementing this project exactly as specified.

The specification documents are the source of truth.

Never simplify requirements.

Never replace technologies with easier alternatives.

If the specification conflicts with your assumptions, the specification wins.

---

# Your Mission

Implement a production-quality AI Research Assistant Platform.

The project must demonstrate expertise in

- AI Engineering
- Backend Engineering
- LLM Engineering
- MLOps
- DevOps
- Distributed Systems

The repository is intended as a portfolio project that showcases production engineering rather than academic experimentation.

Everything should look like code that could be merged into a real startup repository.

---

# Absolute Rules

Never generate placeholder implementations.

Never leave TODO comments.

Never return pseudo code.

Never write demonstration code.

Never mock business logic.

Never skip validation.

Never skip tests.

Never skip documentation.

Never generate incomplete modules.

If a dependency is required, implement it completely.

---

# Repository Philosophy

Every module must be production ready.

Every module must compile.

Every module must be testable.

Every module must be documented.

Every public interface must be typed.

Every service must be injectable.

Every API must be documented.

Every workflow must be observable.

---

# Architecture

Always follow

Modular Monolith

Domain Driven Design

SOLID

Dependency Injection

Repository Pattern

Factory Pattern

Strategy Pattern

Never violate package boundaries.

---

# Code Quality

Python >=3.12

Strict typing.

mypy clean.

ruff clean.

black formatted.

No wildcard imports.

No duplicated logic.

No circular imports.

No global mutable state.

No hidden side effects.

---

# Documentation

Every module must contain

README

Architecture explanation

Usage examples

API documentation

Limitations

Future improvements

Public functions require Google-style docstrings.

---

# Testing

Every module requires

Unit tests

Integration tests

Failure tests

Edge case tests

Coverage target

95%

Do not implement features without tests.

---

# Logging

Every service logs

Request ID

Trace ID

Execution time

Errors

Warnings

Resource usage

Use structured JSON logging.

Never print().

---

# Observability

Every service exports

Prometheus metrics

OpenTelemetry traces

Health checks

Readiness checks

Liveness checks

---

# Error Handling

Never swallow exceptions.

Use typed exceptions.

Provide meaningful messages.

Attach correlation IDs.

Recover whenever possible.

---

# Security

Validate all external input.

Never trust user data.

Escape SQL.

Sanitize file uploads.

Validate MIME types.

Protect against prompt injection.

Protect against path traversal.

Protect against command injection.

Protect against XSS.

Protect against CSRF where applicable.

Use JWT.

Use RBAC.

Never hardcode secrets.

---

# Performance

Avoid unnecessary allocations.

Prefer async I/O.

Batch database operations.

Batch embedding generation.

Cache repeated operations.

Use connection pooling.

Avoid N+1 queries.

Avoid blocking calls inside async code.

---

# AI Engineering

Never call an LLM directly from business logic.

All model calls must go through the Model Service.

All agent execution must go through LangGraph.

All prompts must come from the Prompt Registry.

All tools must come from the Tool Registry.

All retrieval must go through the Retrieval Service.

---

# Fine-Tuning

Implement

QLoRA

PEFT

TRL

MLflow tracking

Checkpointing

Evaluation

Model Registry

Do not implement toy training loops.

Implement production pipelines.

---

# Retrieval

Implement

Hybrid Search

Semantic Search

BM25

Cross Encoder Re-ranking

Metadata Filtering

Context Compression

Adaptive Top-K

---

# DevOps

Everything must run with

Docker Compose

The repository must also support

Kubernetes

GitHub Actions

Environment variables

Health checks

Graceful shutdown

---

# Frontend

Use

Next.js

TypeScript

Tailwind

shadcn/ui

Responsive design.

Dark mode.

Accessibility.

---

# Git Standards

Small commits.

Meaningful commit messages.

Feature branches.

Conventional Commits.

---

# When Requirements Are Missing

Do not invent architecture.

Instead

Infer the solution from surrounding specifications.

If multiple valid implementations exist

Choose the one most commonly used in production by modern AI startups.

---

# Libraries

Prefer mature libraries.

Avoid abandoned projects.

Avoid experimental frameworks.

---

# Folder Creation

Never create unnecessary folders.

Never duplicate functionality.

Respect the repository structure specification.

---

# Acceptance Criteria

A task is complete only if

- implementation exists
- tests pass
- documentation exists
- lint passes
- typing passes
- Docker builds
- API documented
- metrics exported
- traces exported
- logging implemented
- security reviewed

Otherwise the task is incomplete.

---

# Final Objective

The finished repository should be indistinguishable from a production internal AI platform developed by a small team of experienced AI engineers.

A hiring manager should conclude that the author understands modern AI engineering, backend engineering, MLOps, distributed systems, and production software development—not just how to build another chatbot.