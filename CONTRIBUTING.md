# Contributing to v-rag

Thanks for your interest in contributing to v-rag! This is an early-stage project (P0), so the process is lightweight for now and will evolve.

## Project Status

v-rag is in the design + P0 phase. The full design spec lives at
[`docs/superpowers/specs/2026-07-03-v-rag-tech-selection-design.md`](./docs/superpowers/specs/2026-07-03-v-rag-tech-selection-design.md).
Reading it first will save you a lot of time — it explains the architecture, module boundaries, and roadmap.

## How to Contribute

1. **Open an issue first** for bug reports, feature ideas, or design questions. This avoids duplicated work.
2. **Fork & branch**: branch from `main`, name it `feat/<topic>` or `fix/<topic>`.
3. **Keep changes surgical**: match existing patterns, don't refactor unrelated code, don't add unrequested features (YAGNI).
4. **Tests**: every new module should ship with unit tests (we follow a test-first approach for core logic).
5. **Lint / type checks** must pass before requesting review:
   ```bash
   # backend
   ruff check backend/ && mypy backend/ && pytest
   # frontend
   pnpm lint && pnpm typecheck && pnpm test
   ```
6. **Commit messages**: use Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
7. **Open a Pull Request** against `main` with a clear description of what and why.

## Code Style

- Every function/method has a docstring explaining purpose, params, and return value.
- Functions stay single-responsibility, ideally under 40 lines.
- Pass only the parameters you need; return only what callers need.
- Semantic names — no `data`, `info`, `temp`.

## Repo Layout

Monorepo: `backend/` (Python/FastAPI + v-rag-core), `frontend/` (Next.js), `docs/`.

## Licensing

By contributing, you agree your contributions will be licensed under the Apache License 2.0.
