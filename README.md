# v-rag

> An open-source **Agentic RAG** system with intent routing, multimodal retrieval, self-built long-term memory, and autonomous planning — configurable and debuggable from a web admin console.

[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](./LICENSE)
[![Status](https://img.shields.io/badge/status-P0%20in%20progress-orange)](#roadmap)

---

## Why v-rag?

Traditional RAG is a static *retrieve → generate* pipeline. v-rag treats retrieval as a **decision** made by an agent, not a fixed step. It is built around four capabilities that plain RAG platforms lack:

| Capability | What it does |
|---|---|
| **Intent Routing** | Classifies each query and routes it to the right branch (chitchat / knowledge QA / multimodal doc / tool / complex task / clarification / unsupported) via a configurable cascade (rule → semantic → LLM). |
| **Autonomous Planning** | For complex queries, decomposes into sub-tasks using Plan-and-Execute / ReAct / Reflexion. |
| **Long-term Memory** | Self-built (no Mem0/Letta dependency): episodic / semantic / procedural memory, with Policy Gate on write and Memory Gate + Context Builder on read. PostgreSQL is the source of truth. |
| **Multimodal** | ColPali page-level visual retrieval (OCR-free, layout-preserving), with a pluggable OCR pipeline (PaddleOCR-VL default). |

Everything is **configurable and debuggable from a web admin console**, including a visual graph editor for the routing DAG (React Flow + Node Registry whitelist + version management).

## Design Philosophy

1. **Core capabilities are self-built; external components are replaceable.** Provider, vector store, OCR, and parser are all abstraction layers — v-rag is not a thin wrapper over LangGraph/Mem0/LlamaIndex.
2. **PostgreSQL is the single source of truth**; vector databases are index-only.
3. **Configuration-driven, not code-driven.** Intents, routing, node params, and graph structure are all editable from the admin console.
4. **Safety over flexibility.** The visual editor uses a Node Registry whitelist; graph JSON never carries executable code.
5. **YAGNI.** Graph reasoning and multi-tenancy are deferred, but graph-ready and multi-tenant-ready structures are preserved.

## Tech Stack

| Layer | Choice |
|---|---|
| Backend | Python · FastAPI · LangGraph · LlamaIndex (retrieval) |
| Core | Self-built `v-rag-core` (provider / memory / retrieval / document-processor / multimodal / storage / graph-engine) |
| Models | Hybrid: commercial APIs (OpenAI / Claude / Gemini) + self-hosted (Ollama / vLLM) |
| Storage | PostgreSQL (source of truth) + Zvec (default local vector index) / Milvus (scale) / Qdrant (optional) |
| Multimodal | ColPali / ColQwen2 · Docling + Unstructured + PyMuPDF · PaddleOCR-VL |
| Observability | OpenTelemetry + Langfuse + v-rag Trace Schema |
| Frontend | Next.js 16 · shadcn/ui · Tailwind v4 · React Flow |
| Deploy | docker-compose (P0) → K8s/Helm (later) |

## Repository Structure (monorepo)

```
v-rag/
├── backend/            # FastAPI + v-rag-core (P0)
├── frontend/           # Next.js admin console (P0)
├── docs/
│   └── superpowers/specs/
│       └── 2026-07-03-v-rag-tech-selection-design.md   # full design spec
├── docker-compose.yml  # P0
├── LICENSE
└── README.md
```

## Roadmap

Each phase is an independent deliverable with a demoable outcome.

| Phase | Deliverable |
|---|---|
| **P0 Foundation** | FastAPI skeleton + provider/storage abstraction + base retrieval + Next.js shell + observability |
| **P1 Intent Routing** ⭐ | LangGraph router + 7-class taxonomy + visual graph editor (dry-run + versioning) + node-level playground trace |
| **P2 Autonomous Planning** | Plan-and-Execute + ReAct + reflect (bounded, branch-aware) + MCP Adapter |
| **P3 Self-built Memory** | 3 memory types + Policy/Memory Gates + Context Builder + consolidation + memory viewer |
| **P4 Multimodal** | DocumentProfiler + parser routing + ColPali two-stage + OCR plugins + tables + citation |
| **P5 Eval & Observability** | Golden sets + eval gates + v-rag Trace Schema + degradation policies |

> **Status:** P0-A backend foundation is implemented on the backend feature branch.

## Quick Start

```bash
cd backend
uv sync --extra dev
uv run pytest -v
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
curl http://localhost:8000/health
```

Docker:

```bash
cd backend
docker compose up -d
curl http://localhost:8000/health
docker compose down
```

Expected health response:

```json
{"status":"ok"}
```

## Documentation

- [Design Spec (tech selection & system design)](./docs/superpowers/specs/2026-07-03-v-rag-tech-selection-design.md)

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](./CONTRIBUTING.md). By participating, you agree to abide by the [Code of Conduct](./CODE_OF_CONDUCT.md).

## License

Apache License 2.0 — see [LICENSE](./LICENSE).
