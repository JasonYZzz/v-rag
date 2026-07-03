# P3-A: 自主记忆引擎 (Self-built Long-term Memory) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans. TDD throughout.

**Goal:** 实装 v-rag 自研长期记忆模块（spec §6.1 差异化核心），替换 P1/P2 一直 stub 的 `memory_recall` / `memory_write`，让 agent 具备跨会话记忆与个性化能力。三类记忆（episodic/semantic/procedural）+ PG source of truth + Policy Gate（写入）+ Memory Gate + Context Builder（读取）+ 巩固/遗忘 + graph-ready 结构。

**Architecture:** `core/memory/` 自治模块，对外暴露 `MemoryService`（remember/recall/consolidate/forget + list/update/feedback）。**PG 是所有记忆的 source of truth**（memory_event/fact/procedure/feedback/consolidation_log），向量库（复用 P0-A storage 抽象）仅作 embedding 索引层。写入经 Policy Gate（禁写模型生成内容为事实）；读取经 Memory Gate + Context Builder（召回不直塞 prompt）。`graph_adapter` 接口占位（graph-ready，图谱推理 P0.2+ 接 Cognee/Graphiti）。接入默认图替换两个 memory stub。新增 `/memories` API（前端记忆查看器 P3-B 用）。

**Tech Stack:** 现有后端栈 + `rank-bm25`（读取 hybrid BM25）。

**参考:** spec §6.1（记忆全部设计）、§6.1.8（graph-ready）、§9（memory_trace）、§11（PG source of truth）；P1-A graph 节点；P0-A storage 抽象。

**相关 skills:** @python:test-first @python:lint @python:typecheck @fastapi:endpoint @fastapi:module

---

## File Structure

```
backend/app/core/memory/
├── __init__.py
├── models.py             # SQLAlchemy: MemoryEvent/Fact/Procedure/Feedback/ConsolidationLog
├── schemas.py            # Pydantic: MemoryIn/Out, MemoryFilter, MemoryPatch, MemoryFeedback, Scope/Status/Sensitivity enum
├── store.py              # 向量索引层 (复用 storage 抽象, add/search/delete by memory_id)
├── bm25.py               # rank-bm25 封装 (文本召回)
├── writer.py             # 写入路径: Candidate -> Importance -> TypeClassifier -> PolicyGate -> Dedup -> PG -> Vector -> Trace
├── reader.py             # 读取路径: query rewrite -> vector+BM25+recent -> rerank -> MemoryGate -> ContextBuilder
├── consolidation.py      # consolidate (合并/重算/衰减) + forget
├── graph_adapter.py      # graph-ready 接口 (占位, P0.2+ 接 Cognee/Graphiti)
└── service.py            # MemoryService: public API
backend/app/api/routes/memories.py     # Create: /memories list/update/feedback/forget
backend/app/core/graph/nodes/
├── memory_recall.py      # Modify: stub -> MemoryService.recall
└── memory_write.py       # Modify: stub -> MemoryService.remember
backend/app/core/db/models.py          # Modify: + memory tables
backend/app/deps.py                    # Modify: + MemoryService 依赖
backend/alembic/versions/<ts>_memory.py
backend/tests/unit/memory/{test_writer,test_reader,test_consolidation,test_service,test_bm25}.py
backend/tests/integration/test_memory_flow.py
```

---

## Task 1: 记忆数据模型 + Schemas + 迁移

**Files:** Modify `db/models.py`；Create `memory/schemas.py`；Create Alembic migration；Test `test_memory_models.py`

- [ ] **Step 1: PG 模型**（spec §6.1.3：PG source of truth）
```python
# db/models.py 新增
class MemoryEvent(Base):
    """情景记忆: 时序对话/工具/文档事件。"""
    __tablename__ = "memory_event"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4)
    user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    workspace_id: Mapped[str] = mapped_column(String, default="default")
    scope: Mapped[str] = mapped_column(String, default="user")  # user|session|project|workspace|agent|org
    content: Mapped[str] = mapped_column(Text)
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    status: Mapped[str] = mapped_column(String, default="active")  # active|candidate|superseded|deleted|expired
    sensitivity: Mapped[str] = mapped_column(String, default="normal")  # normal|private|sensitive
    source_event_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source_type: Mapped[str] = mapped_column(String, default="user")  # user|tool|document|llm_generated
    valid_from: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ttl: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MemoryFact(Base):
    """语义记忆: 抽取的事实三元组 (graph-ready, spec §6.1.8)。"""
    __tablename__ = "memory_fact"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4)
    user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    workspace_id: Mapped[str] = mapped_column(String, default="default")
    subject: Mapped[str] = mapped_column(String)
    predicate: Mapped[str] = mapped_column(String)
    object: Mapped[str] = mapped_column(String)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    status: Mapped[str] = mapped_column(String, default="active")
    source_event_id: Mapped[str | None] = mapped_column(String, nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MemoryProcedure(Base):
    """程序记忆: 技能/工作流。"""
    __tablename__ = "memory_procedure"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4)
    user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    workspace_id: Mapped[str] = mapped_column(String, default="default")
    skill_name: Mapped[str] = mapped_column(String)
    trigger: Mapped[str] = mapped_column(Text)
    action_spec: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MemoryFeedback(Base):
    """用户对记忆的纠错反馈 (记忆查看器用)。"""
    __tablename__ = "memory_feedback"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4)
    memory_id: Mapped[str] = mapped_column(String)  # 指向 event/fact/procedure 之一
    memory_type: Mapped[str] = mapped_column(String)  # event|fact|procedure
    feedback: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ConsolidationLog(Base):
    """巩固日志 (审计)。"""
    __tablename__ = "memory_consolidation_log"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4)
    user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    action: Mapped[str] = mapped_column(String)  # merge|decay|supersede
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 2: Pydantic schemas**（`MemoryIn/Out`、`MemoryFilter`、`MemoryPatch`、`MemoryFeedbackIn`；`Scope`/`Status`/`Sensitivity`/`SourceType` enum）
- [ ] **Step 3: Alembic 迁移** `uv run alembic revision --autogenerate -m "memory tables" && uv run alembic upgrade head`
- [ ] **Step 4: 测试**（模型 CRUD + 三元组结构 + feedback 关联）+ lint + mypy + Commit `feat(memory): PG models for event/fact/procedure/feedback/consolidation`

---

## Task 2: 向量索引层 + BM25

**Files:** Create `memory/store.py` + `memory/bm25.py`；Test `test_bm25.py`

- [ ] **Step 1: `store.py`** —— 复用 P0-A `VectorStore` 抽象：`index_memories(ids, texts, metadata)` → embedder.embed → store.add；`search_memories(query, top_k, filter)` → embed → store.search。metadata 含 `memory_type/scope/workspace_id`。
- [ ] **Step 2: BM25** `uv add rank-bm25`
```python
"""BM25 文本召回 (spec §6.1.5 hybrid: vector + BM25)。"""
from rank_bm25 import BM25Okapi


class BM25Index:
    """内存 BM25 (P3 简单版; 规模化后换 PG 全文或专用引擎)。"""
    def __init__(self) -> None:
        self._ids: list[str] = []
        self._corpus: list[list[str]] = []

    def add(self, ids: list[str], texts: list[str]) -> None:
        tokenized = [t.lower().split() for t in texts]
        self._ids.extend(ids)
        self._corpus.extend(tokenized)

    def search(self, query: str, top_k: int) -> list[tuple[str, float]]:
        if not self._corpus:
            return []
        bm25 = BM25Okapi(self._corpus)
        scores = bm25.get_scores(query.lower().split())
        ranked = sorted(zip(self._ids, scores, strict=True), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]
```
> 注：BM25 内存版适合 P3；规模化（万级记忆）后换 PG tsvector 或专用引擎，接口不变。

- [ ] **Step 3: 测试**（BM25 召回相关性；store add/search 走 InMemory VectorStore）+ Commit `feat(memory): vector index layer + BM25`

---

## Task 3: 写入路径（含 Policy Gate）

**Files:** Create `memory/writer.py`；Test `test_writer.py`

- [ ] **Step 1: 写入管线**（spec §6.1.4）
```python
"""写入路径: Candidate -> Importance -> TypeClassifier -> Policy Gate -> Dedup -> PG -> Vector -> Trace。

关键约束 (spec §6.1.4): 禁止把模型生成内容当事实写入。只写:
- 用户明确陈述 (source_type=user)
- 工具返回结构化结果 (source_type=tool)
- 文档可溯源事实 (source_type=document)
llm_generated 的降级或拒绝。
"""
from dataclasses import dataclass
from typing import Any

from app.core.memory.schemas import MemoryIn, SourceType


@dataclass
class WriteDecision:
    accept: bool
    reason: str
    importance: float
    memory_type: str   # event|fact|procedure


def _importance_score(content: str, source_type: SourceType) -> float:
    """启发式重要性 (P3; LLM 打分可选)。用户陈述 > 工具/文档 > llm_generated。"""
    base = {"user": 0.7, "tool": 0.6, "document": 0.5, "llm_generated": 0.2}[source_type]
    length_bonus = min(0.2, len(content) / 1000)
    return min(1.0, base + length_bonus)


def policy_gate(decision_input: MemoryIn, importance: float) -> WriteDecision:
    """Policy Gate: 长期价值/敏感/冲突/确认 (P3 启发式; LLM 判定可选)。"""
    # 1) llm_generated 不写为事实 (核心约束)
    if decision_input.source_type == "llm_generated":
        return WriteDecision(False, "reject: llm_generated not written as fact", importance, "")
    # 2) 低价值不写
    if importance < 0.3:
        return WriteDecision(False, "reject: low long-term value", importance, "")
    # 3) 敏感需确认 (P3: 标记 pending, 不阻塞写入但记 sensitivity; 真实确认 UI 在 P3-B)
    # 4) 类型分类 (P3 简单: 有 subject/predicate/object -> fact; 否则 event)
    mtype = "fact" if (decision_input.subject and decision_input.predicate) else "event"
    return WriteDecision(True, "accepted", importance, mtype)


async def write(input_: MemoryIn, services: Any) -> dict:
    """完整写入管线。"""
    # 1. Candidate Extractor: 输入已结构化 (P3; LLM 抽取在 P3 增强或 P3-B)
    # 2. Importance Scorer
    importance = _importance_score(input_.content, input_.source_type)
    # 3. Type Classifier (policy_gate 内)
    decision = policy_gate(input_, importance)
    if not decision.accept:
        return {"accepted": False, "reason": decision.reason}
    # 4. Dedup / Merge (P3: 按 workspace+user+content 前缀查近 N 条, 相似度高则 merge)
    #    P3 简单: 暂不 merge, 全写; consolidation 后台合并 (Task 5)
    # 5. Write PG (source of truth)
    memory_id = await services.memory_persist(input_, decision, importance)
    # 6. Write Vector Index
    await services.memory_store.index_memories([memory_id], [input_.content],
                                                [{"memory_type": decision.memory_type,
                                                  "scope": input_.scope,
                                                  "workspace_id": input_.workspace_id}])
    # 7. Trace Log
    return {"accepted": True, "memory_id": memory_id, "memory_type": decision.memory_type,
            "importance": importance}
```

- [ ] **Step 2: 测试**（user/document/tool 通过；llm_generated 拒绝；低价值拒绝；有三元组→fact 否则 event）+ Commit `feat(memory): write path with Policy Gate (reject llm_generated as fact)`

---

## Task 4: 读取路径（含 Memory Gate + Context Builder）

**Files:** Create `memory/reader.py`；Test `test_reader.py`

- [ ] **Step 1: 读取管线**（spec §6.1.5）
```python
"""读取路径: query rewrite -> vector+BM25+recent episodic -> rerank -> Memory Gate -> Context Builder。
召回结果不直接进 prompt, 经 Gate 过滤 + Builder 压缩。
"""
from typing import Any


async def recall(query: str, services: Any, *, top_k: int = 5, scope: str | None = None,
                 workspace_id: str = "default", user_id: str | None = None) -> dict:
    """混合召回 + Gate + 压缩。"""
    # 1. query rewrite (P3 简单: 原样; LLM rewrite 增强可选)
    rewritten = query
    # 2. 召回三路
    vec_hits = await services.memory_store.search_memories(rewritten, top_k=top_k * 2,
                                                            filter={"workspace_id": workspace_id})
    bm25_hits = services.bm25.search(rewritten, top_k=top_k * 2)
    recent = await services.memory_recent_episodic(user_id, workspace_id, limit=top_k)
    # 3. rerank (合并 + 去重 + 按分数归一)
    merged = _merge_and_rerank(vec_hits, bm25_hits, recent)
    # 4. Memory Gate: relevance/recency/confidence/importance/scope/conflict/sensitivity
    gated = _memory_gate(merged, query, scope, user_id)
    # 5. Context Builder: 压缩 (P3: top_k 截断 + 按重要性排序; LLM 摘要可选)
    context = _build_context(gated[:top_k])
    return {"memories": gated[:top_k], "context": context}


def _memory_gate(candidates: list[dict], query: str, scope: str | None, user_id: str | None) -> list[dict]:
    """过滤: scope 匹配 / 敏感(降权) / 冲突(取最新) / 时效(valid_to 未过期)。"""
    out = []
    for c in candidates:
        if c.get("status") not in (None, "active"):
            continue
        if scope and c.get("scope") != scope:
            continue
        # sensitive 降权 (不删, 但排序靠后)
        if c.get("sensitivity") in ("private", "sensitive"):
            c = {**c, "_score": c.get("_score", 0) * 0.5}
        out.append(c)
    # conflict: 同 subject 取最新 (supersede 旧)
    return _dedupe_conflicts(out)


def _build_context(memories: list[dict]) -> str:
    """压缩为注入 prompt 的文本块 (不塞全部)。"""
    return "\n".join(f"- [{m.get('memory_type')}] {m.get('content', m.get('subject', ''))}" for m in memories)


def _merge_and_rerank(vec, bm25, recent) -> list[dict]: ...
def _dedupe_conflicts(items) -> list[dict]: ...
```

- [ ] **Step 2: 测试**（三路召回合并；Gate 过滤 status/scope/敏感降权/冲突取新；Context Builder 截断）+ Commit `feat(memory): read path with Memory Gate and Context Builder`

---

## Task 5: 巩固与遗忘

**Files:** Create `memory/consolidation.py`；Test `test_consolidation.py`

- [ ] **Step 1: consolidate + forget**
```python
"""巩固 (合并近似/重算置信度/衰减过期) + 遗忘。仿'睡眠巩固'。"""
async def consolidate(user_id: str | None, workspace_id: str, services) -> dict:
    """后台巩固: 1) 近似 fact merge; 2) 过期 status=expired; 3) 低置信 supersede。"""
    # 1. 近似 fact 合并 (P3: 同 subject+predicate, object 相似度阈值)
    merged = await services.merge_similar_facts(user_id, workspace_id)
    # 2. 衰减: valid_to < now -> status=expired
    expired = await services.expire_overdue(user_id, workspace_id)
    # 3. 写 ConsolidationLog
    await services.log_consolidation(user_id, {"merged": merged, "expired": expired})
    return {"merged": merged, "expired": expired}


async def forget(filter_: dict, services) -> int:
    """显式遗忘: status=deleted (软删, 保留审计)。"""
    n = await services.mark_deleted(filter_)
    # 同步删向量索引
    await services.memory_store.delete_memories(filter_["ids"])
    return n
```

- [ ] **Step 2: 测试**（过期标记；近似 fact 合并；forget 软删 + 向量同步）+ Commit `feat(memory): consolidation and forget`

---

## Task 6: MemoryService（public API）

**Files:** Create `memory/service.py`；Modify `deps.py`（+ MemoryService 注入）；Test `test_service.py`

- [ ] **Step 1: MemoryService** 聚合 writer/reader/consolidation/persistence，暴露：
```python
class MemoryService:
    async def remember(self, input_: MemoryIn) -> dict: ...          # 调 writer.write
    async def recall(self, query, *, top_k=5, scope=None, ...) -> dict: ...  # 调 reader.recall
    async def consolidate(self, user_id, workspace_id) -> dict: ...
    async def forget(self, filter_: dict) -> int: ...
    # 内部/管理 (记忆查看器, P3-B 用)
    async def list_memories(self, filter_: MemoryFilter) -> list[MemoryOut]: ...
    async def update_memory(self, memory_id, patch: MemoryPatch) -> MemoryOut: ...
    async def feedback(self, memory_id, memory_type, fb: MemoryFeedbackIn) -> None: ...
```
- [ ] **Step 2: deps** —— `init_deps` 构建 MemoryService（依赖 embedder + storage + session_factory + bm25）。
- [ ] **Step 3: 测试**（remember→recall 闭环；list/update/feedback）+ Commit `feat(memory): MemoryService public API`

---

## Task 7: graph_adapter 占位（graph-ready）

**Files:** Create `memory/graph_adapter.py`；Test `test_graph_adapter.py`

- [ ] **Step 1: 接口占位**（spec §6.1.8：P0.1 不实现图谱，保留结构）
```python
"""graph_adapter: graph-ready 接口 (spec §6.1.8)。P3 只定义接口; Cognee/Graphiti 接入在 P0.2+。"""
from typing import Protocol


class GraphAdapter(Protocol):
    """将 semantic fact 三元组导出为图谱节点/边 (未来接 Cognee/Graphiti/Neo4j)。"""
    async def upsert_fact(self, fact: dict) -> None: ...
    async def query_neighbors(self, subject: str, depth: int = 1) -> list[dict]: ...


class NoopGraphAdapter:
    """P3 占位: 不做图谱, 只记 log。"""
    async def upsert_fact(self, fact: dict) -> None: return None
    async def query_neighbors(self, subject: str, depth: int = 1) -> list[dict]: return []
```
- [ ] **Step 2: writer 写 fact 时调 graph_adapter.upsert_fact**（Noop 不影响，预留接入点）。
- [ ] **Step 3: 测试** + Commit `feat(memory): graph-ready adapter interface (noop, for future Cognee/Graphiti)`

---

## Task 8: 接入默认图（替换 memory stub）

**Files:** Modify `nodes/memory_recall.py` + `nodes/memory_write.py`；Test `test_memory_nodes.py` + 集成

- [ ] **Step 1: memory_recall 真实化**
```python
async def memory_recall(state, config, services):
    """调 MemoryService.recall, 按 intent 决定召回 scope (spec §6.2.3)。"""
    intent = state.get("intent")
    scope = {"knowledge_qa": "project", "complex_task": "user",
             "chitchat": "session"}.get(intent.value if intent else "", "user")
    result = await services.memory.recall(state["query"], top_k=config.get("top_k", 5),
                                           scope=scope, user_id=state.get("user_id"),
                                           workspace_id=state.get("workspace_id", "default"))
    return {"memory_hits": result["memories"], "context_blocks": [result["context"]]}
```
- [ ] **Step 2: memory_write 真实化**（从 state 抽取 candidate：用户 query + retrieved/generation 中的可溯源事实，source_type=user/document，调 MemoryService.remember；generation 不写为事实）
- [ ] **Step 3: 测试**（recall 按 intent 选 scope；write 写 user query 但不写 generation）+ Commit `feat(graph): wire memory_recall/write to MemoryService`

---

## Task 9: `/memories` API（记忆查看器后端）

**Files:** Create `api/routes/memories.py`；Modify `router.py`；Test `test_memories_api.py`

- [ ] **Step 1: 端点**
```python
@router.get("/memories")                 # 列表 (filter: type/scope/user/status, 分页)
@router.patch("/memories/{id}")          # update (改 status/importance/sensitivity)
@router.post("/memories/{id}/feedback")  # 用户纠错
@router.delete("/memories")              # forget (filter 批量软删)
```
- [ ] **Step 2: 测试**（list 过滤、update、feedback、forget 软删 + 向量同步）+ Commit `feat(api): /memories CRUD for memory viewer`

---

## Task 10: 端到端验证

- [ ] **Step 1: e2e 清单**
  - 会话 A：`/chat "我用 Python，团队是 Spring"` → memory_write 写 user 事实（source_type=user）
  - 会话 B：`/chat "我该用什么技术栈"` → memory_recall 召回 A 的事实 → generation 引用
  - Policy Gate：generation 内容不写入为事实（验证 source_type=llm_generated 拒绝）
  - Memory Gate：低相关/过期/敏感记忆被过滤或降权
  - consolidate：过期记忆标记 expired；近似 fact 合并
  - forget：软删 + 向量索引同步
  - GET /memories 列表 + PATCH + feedback
  - graph_adapter Noop 不影响写入
  - route_trace + memory_trace 记录
- [ ] **Step 2: 全量 pytest + ruff + mypy 全绿**
- [ ] **Step 3:** Commit `test(memory): e2e cross-session memory with Policy/Memory Gate`

---

## 验收标准（P3-A 完成 = 全部满足）

- [ ] 三类记忆（event/fact/procedure）PG 持久化，向量库仅索引
- [ ] Policy Gate：`llm_generated` 拒绝写为事实；低价值拒绝
- [ ] Memory Gate + Context Builder：召回不直塞 prompt；scope/status/sensitivity/冲突过滤
- [ ] hybrid 召回（vector + BM25 + recent episodic）
- [ ] consolidate（过期/合并）+ forget（软删 + 向量同步）
- [ ] 默认图 memory_recall/memory_write 真实化，跨会话记忆闭环
- [ ] `/memories` API（list/update/feedback/forget）
- [ ] graph_adapter 占位（graph-ready，Noop 不影响）
- [ ] pytest / ruff / mypy 全绿

## 不在 P3-A 范围（YAGNI / P3-B / 后续）

- **记忆查看器前端**（list/update/feedback/forget UI + 敏感标记）= **P3-B**
- LLM 抽取 Candidate（P3 用结构化输入；LLM 抽取作为增强）
- LLM query rewrite / Context Builder 摘要（P3 启发式；LLM 可选）
- 图谱推理（Cognee/Graphiti 接入）= P0.2+（spec §6.1.8）
- BM25 规模化（PG tsvector / 专用引擎）= 后续

## Open Questions

1. **Importance Scorer**：P3 启发式（source_type + 长度）。LLM 打分更准但贵；可配置开关（默认启发式）。
2. **Dedup/Merge 时机**：P3 写入时暂不 merge（全写），consolidation 后台合并。实时 merge 更准但增写入延迟。
3. **BM25 规模**：内存 BM25 适合 P3（千级记忆）；万级后换 PG 全文。接口不变。
4. **敏感记忆确认**：P3 标 sensitivity 但不阻塞写入（标 pending）；真实"需用户确认"UI 在 P3-B。

## 风险

1. **Policy Gate 误判**：启发式可能误拒用户重要陈述或误纳噪声。Task 3 测试覆盖边界；LLM 兜底可选。
2. **召回质量**：hybrid 三路融合的 rerank 权重需调参。Task 4 测试用确定性 case，真实质量在 P5 评测集校准。
3. **memory_write 抽取**：从 state 抽"可写事实"需谨慎（只写 user query + document chunk，不写 generation）。Task 8 测试必须验证 generation 不被写入。
4. **向量索引一致性**：forget 软删（status=deleted）+ 向量索引删除，两步需事务/补偿。Task 5 测试验证一致性。
