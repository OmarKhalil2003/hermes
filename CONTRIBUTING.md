# Contributing to Enterprise AI Research Assistant

Welcome! This project is developed by a team of **two developers** working collaboratively. To ensure high code quality, consistency, and a professional software engineering workflow, we follow the guidelines detailed below.

---

## 👥 Dev Team Roles & Responsibilities

To avoid merge conflicts and maximize efficiency, work is partitioned by domain:

- **Developer A (Backend & Infrastructure)**:
  - Focus: Database design, schemas (SQLAlchemy/Alembic), queue workers (Celery/RabbitMQ), vector database setup (Qdrant), API routes, and container configurations.
- **Developer B (Frontend & AI Integration)**:
  - Focus: React Components (Next.js), UI/UX (Tailwind + shadcn/ui), state management, LangGraph workflows, prompt engineering, and report generator utilities.

*Note: Critical integrations (e.g., matching API response formats with frontend queries or writing end-to-end integration tests) should be done via collaborative pair programming or formal PR reviews.*

---

## 🌿 Git Branching Strategy

We use **GitHub Flow** (feature branches off `main`):

1. **Create a Branch**: Always create a feature or bugfix branch. Do not work directly on `main`.
2. **Branch Naming Convention**:
   - Features: `feature/issue-<num>-<short-description>` (e.g., `feature/issue-102-db-migrations`)
   - Bugfixes: `bugfix/issue-<num>-<short-description>` (e.g., `bugfix/issue-205-jwt-expiration`)
   - Infrastructure/Chore: `chore/issue-<num>-<short-description>` (e.g., `chore/issue-15-ci-caching`)

---

## 📝 Commit Standards (Conventional Commits)

Commit messages must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Allowed Types:
- `feat`: A new feature (e.g. `feat(auth): implement refresh token endpoint`)
- `fix`: A bug fix (e.g. `fix(rag): resolve off-by-one chunking boundary`)
- `docs`: Documentation changes (e.g. `docs(readme): add docker setup instructions`)
- `style`: Changes that do not affect the meaning of the code (formatting, missing semi-colons)
- `refactor`: A code change that neither fixes a bug nor adds a feature (e.g. `refactor(db): extract base repository pattern`)
- `perf`: A code change that improves performance
- `test`: Adding missing tests or correcting existing tests
- `build`: Changes that affect the build system or external dependencies (e.g., uv or npm packages)
- `ci`: Changes to CI/CD configurations and scripts (e.g., GitHub Actions workflows)
- `chore`: Other changes that don't modify src or test files

---

## 🔍 Pull Request & Code Review Process

1. **Open a PR**: Link the PR to the relevant issue (e.g. `Closes #102` in description).
2. **Review Requirements**:
   - Since we are a team of 2, **every PR requires at least 1 approval** from the other developer before merging.
   - Direct pushing or merging without review is strictly prohibited.
3. **CI Pipeline Pass**: The PR cannot be merged unless all checks in the GitHub Actions CI pass.
4. **Merge**: Once approved and CI passes, use the "Squash and Merge" option to keep a clean history.

---

## 🛠️ Code Quality Control Checklist

Before pushing your branch, run local checks to ensure the CI passes:

### Backend Checks (Python)
```bash
# Auto-format code
py -3.13 -m uv run black .

# Auto-fix linting and sort imports
py -3.13 -m uv run ruff check . --fix

# Run strict type checking
py -3.13 -m uv run mypy .

# Run unit tests
py -3.13 -m uv run pytest
```

### Frontend Checks (TypeScript / Node.js)
```bash
cd frontend

# Run linter
npm run lint

# Dry run production build compilation
npm run build
```
