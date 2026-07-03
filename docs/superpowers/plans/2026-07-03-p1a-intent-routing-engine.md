# P1-A: 意图路由引擎 (Intent Routing Engine) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `/chat` 从 P0 的直线 `retrieve → generate` 升级为 LangGraph 驱动的意图路由图：7 类 intent taxonomy + 级联路由（规则 → 语义 → LLM）+ Node Registry 白名单 + 动态组装 + 图配置版本管理 + 节点级 trace。这是 v-rag 区别于普通 RAG 平台的差异化核心（spec ⭐）。

**Architecture:** LangGraph `StateGraph` 为大脑，`VragState`（TypedDict）在节点间传递。`NodeRegistry` 注册节点类型（白名单；前端 JSON 不可携带可执行代码）。`graph_config`（受控 JSON）描述图结构，PG 持久化（draft / published / archived 版本管理）。`graph-engine` 按配置动态组装 + 安全检查 + 编译缓存。`/chat` 按 published graph_config 执行并写 `run_trace`。新增 `/graphs` 与 `/runs` API。`memory_recall` / `memory_write` / `reflect` 在 P1 为 stub，P2/P3 实装。

**Tech Stack:** 现有后端栈 + `langgraph>=0.2` + `numpy`（语义相似度）。

**参考:**
- spec §6（路由 + LangGraph 图 + 可视化编排）、§9（trace）、§11（受控 UI 不开放 DSL / MCP 在 P2）
- PRODUCT.md / DESIGN.md
- P0-A plan 的 provider/storage/retrieval 抽象（复用）

**相关 skills:** @python:test-first @python:lint @python:typecheck @fastapi:endpoint @fastapi:module

---

## File Structure

```
backend/app/core/graph/
├── __init__.py
├── state.py                 # VragState + Intent enum
├── registry.py              # NodeDefinition + NodeRegistry (白名单)
├── config.py                # graph_config Pydantic 受控 schema
├── compiler.py              # 动态组装 + 安全检查 + 编译缓存
├── runner.py                # 执行 graph + 写 run_trace
├── persistence.py           # PG 持久化 + 版本管理
└── nodes/
    ├── __init__.py          # 注册所有节点到 registry
    ├── classifier.py        # 级联分类 (规则→语义→LLM) + route_trace
    ├── retrieve.py          # 复用 RetrievalEngine
    ├── generate.py          # 复用 LLMProvider
    ├── reflect.py           # P1 stub
    ├── memory_recall.py     # P1 stub
    ├── memory_write.py      # P1 stub
    ├── clarification.py     # 信息不足追问
    └── unsupported.py       # 拒绝/说明
backend/app/api/routes/
├── graphs.py                # Create: /graphs CRUD + 版本 + dry-run + publish + rollback
└── runs.py                  # Create: GET /runs/{trace_id} 节点级 trace
backend/app/api/routes/chat.py   # Modify: 按 graph_config 执行 + 写 trace
backend/app/core/db/models.py    # Modify: + AgentGraphConfig/Version/PublishHistory/RunTrace
backend/app/graph_seed.py        # Create: 默认路由图 seed
backend/alembic/versions/<ts>_graph_and_runs.py   # Create: 迁移
backend/tests/unit/graph/...
backend/tests/integration/test_graphs_api.py
backend/tests/integration/test_chat_routed.py
```

**职责边界：** `core/graph/` 对外只暴露 `compile_and_run(config, state)` 与 `registry.list()`；节点是纯函数 `(state, config) -> partial state`，不直接访问 DB/LLM（通过 deps 注入的 service 对象）。`/graphs`、`/runs` 只编排。

---

## Task 1: LangGraph 依赖 + `VragState` + Intent 枚举

**Files:** Modify `backend/pyproject.toml`；Create `app/core/graph/state.py`；Test `tests/unit/graph/test_state.py`

- [ ] **Step 1: 加依赖**
```bash
cd backend && uv add "langgraph>=0.2" "numpy>=2.0"
```

- [ ] **Step 2: 写 `state.py`**（spec §6.2.4 字段）
```python
"""LangGraph 状态对象与意图枚举。"""
from enum import Enum
from typing import Annotated, NotRequired, TypedDict

from langgraph.graph.message import add_messages


class Intent(str, Enum):
    """7 类意图 (spec §6.2.1)。"""
    CHITCHAT = "chitchat"
    KNOWLEDGE_QA = "knowledge_qa"
    MULTIMODAL_DOC = "multimodal_doc"
    TOOL_ACTION = "tool_action"
    COMPLEX_TASK = "complex_task"
    CLARIFICATION = "clarification_needed"
    UNSUPPORTED = "unsupported_or_rejected"


class VragState(TypedDict, total=False):
    """节点间传递的契约。NotRequired 因部分节点只写部分字段。"""
    # 上下文标识
    query: str
    user_id: NotRequired[str]
    session_id: NotRequired[str]
    workspace_id: NotRequired[str]
    knowledge_base_id: NotRequired[str]
    # 图配置与版本 (可视化编排 / 灰度 / 回放)
    graph_config_id: NotRequired[str]
    graph_version: NotRequired[int]
    # 路由
    intent: NotRequired[Intent]
    confidence: NotRequired[float]
    route_trace: NotRequired[dict]
    # 中间产物
    memory_hits: NotRequired[list[dict]]
    retrieved_docs: NotRequired[list[dict]]
    context_blocks: NotRequired[list[dict]]
    # 输出
    generation: NotRequired[str]
    reflection: NotRequired[dict | None]
    # 工程治理
    errors: NotRequired[list[dict]]
    budget: NotRequired[dict]
    trace_id: NotRequired[str]
    messages: Annotated[list, add_messages]
```

- [ ] **Step 3: 测试**（Intent 枚举 7 值；state 可构造）
Run: `uv run pytest tests/unit/graph/test_state.py -v` → Step 2 前应 FAIL，之后 PASS。

- [ ] **Step 4: lint + mypy + Commit**
`feat(graph): add langgraph dep, VragState, Intent enum`

---

## Task 2: Node Registry（白名单）

**Files:** Create `app/core/graph/registry.py`；Test `tests/unit/graph/test_registry.py`

- [ ] **Step 1: 写失败测试**
```python
# test_registry.py: 注册一个 fake node defn，断言 has/get/list 工作；
# 重复 type 注册报错；get 未注册 type 报 KeyError。
```

- [ ] **Step 2: 写 `registry.py`**
```python
"""Node Registry: 后端注册节点类型，前端只能引用，不可注入可执行代码 (spec §6.3.1)。"""
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel

from app.core.graph.state import VragState


class NodeFunc(Protocol):
    """节点执行函数: (state, node_config, services) -> state patch (dict)。"""
    def __call__(
        self, state: VragState, config: dict[str, Any], services: Any
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class NodeDefinition:
    """节点类型定义 (白名单条目)。"""
    type: str
    description: str
    config_schema: type[BaseModel] | None  # 校验前端传的 node.config
    execute: NodeFunc


class NodeRegistry:
    """全局白名单注册表。"""

    def __init__(self) -> None:
        self._nodes: dict[str, NodeDefinition] = {}

    def register(self, defn: NodeDefinition) -> None:
        if defn.type in self._nodes:
            raise ValueError(f"node type already registered: {defn.type}")
        self._nodes[defn.type] = defn

    def has(self, type_: str) -> bool:
        return type_ in self._nodes

    def get(self, type_: str) -> NodeDefinition:
        if type_ not in self._nodes:
            raise KeyError(f"unknown node type: {type_}")
        return self._nodes[type_]

    def list(self) -> list[str]:
        return sorted(self._nodes)


registry = NodeRegistry()
```

- [ ] **Step 3: 测试通过 + lint + mypy + Commit** `feat(graph): NodeRegistry whitelist`

---

## Task 3: Intent classifier（级联：规则 → 语义 → LLM）

**Files:** Create `app/core/graph/nodes/classifier.py`；Test `tests/unit/graph/test_classifier.py`

- [ ] **Step 1: 写级联分类器**（spec §6.2.2）
```python
"""意图分类器: 规则 -> 语义 -> LLM 级联，写 route_trace。阈值 P1 用默认，待真实数据校准。"""
from typing import Any

from app.core.graph.registry import NodeDefinition
from app.core.graph.state import Intent, VragState

DIRECT_THRESHOLD = 0.85   # >= 直走
LOW_THRESHOLD = 0.60      # < 进 clarification 或 LLM

# 规则: 关键词 -> intent (P1 极简，可配置化在 P1-B)
RULES: dict[Intent, list[str]] = {
    Intent.UNSUPPORTED: ["密码", "信用卡", "删除账号"],  # 示例敏感/不支持
}

# 语义路由意图原型: 每 intent 几条 few-shot query，embed 后取平均 (Task 3 step 3 注入)
INTENT_EXEMPLARS: dict[Intent, list[str]] = {
    Intent.CHITCHAT: ["你好", "你是谁", "嗨"],
    Intent.KNOWLEDGE_QA: ["产品怎么配置", "文档里说", "请解释"],
    Intent.CLARIFICATION: ["帮我看看", "那个东西"],  # 模糊
    # MULTIMODAL_DOC / TOOL_ACTION / COMPLEX_TASK 在 P2/P4 补 exemplar
}


def _rule_route(query: str) -> Intent | None:
    for intent, kws in RULES.items():
        if any(k in query for k in kws):
            return intent
    return None


async def _semantic_route(query: str, embedder: Any) -> tuple[Intent | None, float]:
    """query embed 与各意图原型 embed 的余弦相似度最高者。返回 (intent, confidence)。"""
    import numpy as np
    qv = np.array((await embedder.embed([query]))[0])
    best, best_score = None, 0.0
    for intent, exemplars in INTENT_EXEMPLARS.items():
        evs = np.array(await embedder.embed(exemplars))
        proto = evs.mean(axis=0)
        score = float(qv @ proto / (np.linalg.norm(qv) * np.linalg.norm(proto) + 1e-9))
        if score > best_score:
            best, best_score = intent, score
    return best, best_score


async def _llm_route(query: str, llm: Any) -> tuple[Intent, float]:
    """LLM 兜底判定。"""
    import json
    options = ", ".join(i.value for i in Intent)
    prompt = (f"Classify the user query into one of: {options}. "
              f'Reply JSON {{"intent": "...", "confidence": 0.0-1.0, "reason": "..."}}.\n'
              f"Query: {query}")
    raw = await llm.complete(prompt, system="You are an intent classifier.")
    data = json.loads(raw)
    return Intent(data["intent"]), float(data.get("confidence", 0.5))


async def classify(state: VragState, config: dict[str, Any], services: Any) -> dict[str, Any]:
    """级联分类节点: 规则 -> 语义 -> LLM，置信度分层。"""
    query = state["query"]
    embedder = services.embedder
    llm = services.llm
    trace: dict[str, Any] = {}

    # 1) 规则
    rule_intent = _rule_route(query)
    trace["rule_result"] = rule_intent.value if rule_intent else None
    if rule_intent:
        return _finish(rule_intent, 1.0, trace, "rule")

    # 2) 语义
    sem_intent, sem_score = await _semantic_route(query, embedder)
    trace["semantic_result"] = (sem_intent.value if sem_intent else None, sem_score)
    if sem_intent and sem_score >= DIRECT_THRESHOLD:
        return _finish(sem_intent, sem_score, trace, "semantic-direct")

    # 3) 低置信 -> LLM 复核
    if sem_intent and sem_score >= LOW_THRESHOLD:
        llm_intent, llm_score = await _llm_route(query, llm)
        trace["llm_result"] = (llm_intent.value, llm_score)
        return _finish(llm_intent, llm_score, trace, "semantic-then-llm")

    # 极低置信 -> clarification
    trace["llm_result"] = None
    return _finish(Intent.CLARIFICATION, sem_score, trace, "low-confidence-clarify")


def _finish(intent: Intent, conf: float, trace: dict, reason: str) -> dict[str, Any]:
    trace.update(final_intent=intent.value, confidence=conf, reason=reason)
    return {"intent": intent, "confidence": conf, "route_trace": trace}
```

- [ ] **Step 2: 写测试**（用 FakeEmbedder + FakeLLM，覆盖：规则命中直走、语义高置信直走、中置信走 LLM、低置信 clarification）
Run: `uv run pytest tests/unit/graph/test_classifier.py -v` → PASS。

- [ ] **Step 3: lint + mypy + Commit** `feat(graph): cascade intent classifier with route_trace`

---

## Task 4: 节点实现（retrieve / generate / clarification / unsupported + stubs）

**Files:** `nodes/{retrieve,generate,reflect,memory_recall,memory_write,clarification,unsupported}.py` + `nodes/__init__.py`（注册）；Test `tests/unit/graph/test_nodes.py`

- [ ] **Step 1: retrieve 节点**（复用 P0 RetrievalEngine）
```python
async def retrieve(state, config, services):
    top_k = config.get("top_k", 4)
    hits = await services.retrieval.search(state["query"], top_k=top_k)
    return {"retrieved_docs": [{"chunk_id": h.chunk_id, "text": h.text,
            "score": h.score, "metadata": h.metadata} for h in hits]}
```

- [ ] **Step 2: generate 节点**（拼 context + LLM complete，写 generation）
```python
async def generate(state, config, services):
    docs = state.get("retrieved_docs", [])
    ctx = "\n---\n".join(d["text"] for d in docs)
    prompt = f"Context:\n{ctx}\n\nQuestion: {state['query']}"
    text = await services.llm.complete(prompt, system="You are the v-rag assistant.")
    return {"generation": text}
```

- [ ] **Step 3: clarification / unsupported 节点**
```python
async def clarification(state, config, services):
    return {"generation": config.get("message", "需要更多信息: 能否说明具体的知识库/对象/时间范围?")}

async def unsupported(state, config, services):
    return {"generation": config.get("message", "该请求暂不支持或超出允许范围。")}
```

- [ ] **Step 4: stub 节点**（memory_recall / memory_write / reflect 直接透传，留 TODO）
```python
async def memory_recall(state, config, services):
    # TODO(P3): 接自研记忆
    return {"memory_hits": []}

async def memory_write(state, config, services):
    # TODO(P3): 经 Policy Gate 写记忆
    return {}

async def reflect(state, config, services):
    # TODO(P2): 质量自检 + 分支回退 (受 max_reflect_rounds)
    return {"reflection": {"quality": "unchecked"}}
```

- [ ] **Step 5: `nodes/__init__.py` 注册全部到 `registry`**
```python
from app.core.graph.registry import NodeDefinition, registry
from app.core.graph.nodes import classifier as cls
# ... 用 NodeDefinition(type="classifier", execute=cls.classify, ...) 注册每个
def register_all() -> None: ...
```

- [ ] **Step 6: 测试**（每节点输入输出契约；stubs 透传）+ lint + mypy + Commit `feat(graph): node implementations + registry registration`

---

## Task 5: `graph_config` 受控 JSON schema

**Files:** Create `app/core/graph/config.py`；Test `tests/unit/graph/test_config_schema.py`

- [ ] **Step 1: 写 Pydantic schema**
```python
"""graph_config 受控 schema (spec §11: 不开放自由 DSL)。前端 React Flow <-> 此 JSON。"""
from pydantic import BaseModel, Field, model_validator


class GraphNodeSpec(BaseModel):
    id: str
    type: str               # 必须命中 registry 白名单 (compiler 校验)
    config: dict = {}


class GraphEdgeSpec(BaseModel):
    model_config = {"populate_by_name": True}
    src: str = Field(alias="from")
    dst: str = Field(alias="to")
    condition: str | None = None   # 引用 state 字段的受控键 (如 "intent=knowledge_qa")


class GraphConfig(BaseModel):
    """一张可执行路由图。"""
    version: int = 1
    nodes: list[GraphNodeSpec]
    edges: list[GraphEdgeSpec]
    entry: str
    exits: list[str]

    @model_validator(mode="after")
    def _check_refs(self):
        ids = {n.id for n in self.nodes}
        if self.entry not in ids:
            raise ValueError(f"entry {self.entry} not in nodes")
        for e in self.edges:
            if e.src not in ids or e.dst not in ids:
                raise ValueError(f"edge references unknown node: {e.src}->{e.dst}")
        for x in self.exits:
            if x not in ids:
                raise ValueError(f"exit {x} not in nodes")
        return self
```

- [ ] **Step 2: 测试**（合法图通过；entry/edge/exit 引用错误时抛错）+ lint + mypy + Commit `feat(graph): graph_config controlled schema`

---

## Task 6: PG 模型 + Alembic 迁移

**Files:** Modify `app/core/db/models.py`；Create `alembic/versions/<ts>_graph_and_runs.py`

- [ ] **Step 1: 加模型**（spec §6.3.2 / §9.3）
```python
class AgentGraphConfig(BaseModel_table):  # 用现有 Base
    __tablename__ = "agent_graph_config"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String)
    workspace_id: Mapped[str] = mapped_column(String, default="default")
    current_published_version: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class AgentGraphVersion(Base):
    __tablename__ = "agent_graph_version"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4)
    config_id: Mapped[str] = mapped_column(ForeignKey("agent_graph_config.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer)
    graph: Mapped[dict] = mapped_column(JSON)   # GraphConfig 序列化
    status: Mapped[str] = mapped_column(String, default="draft")  # draft|published|archived
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class PublishHistory(Base):
    __tablename__ = "agent_graph_publish_history"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4)
    config_id: Mapped[str] = mapped_column(ForeignKey("agent_graph_config.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String)  # publish|rollback
    at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class RunTrace(Base):
    __tablename__ = "run_trace"
    id: Mapped[str] = mapped_column(String, primary_key=True)  # = trace_id
    graph_config_id: Mapped[str | None] = mapped_column(String, nullable=True)
    graph_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    query: Mapped[str] = mapped_column(Text)
    route_trace: Mapped[dict] = mapped_column(JSON, default=dict)
    node_io: Mapped[list] = mapped_column(JSON, default=list)  # 每节点 in/out 摘要
    intent: Mapped[str | None] = mapped_column(String, nullable=True)
    budget: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 2: 生成迁移**
```bash
uv run alembic revision --autogenerate -m "graph config and run trace"
uv run alembic upgrade head
```
> 若 P0-A 未启用 Alembic（用了 `create_all`），此 task 顺带把 Alembic 接上（`alembic init` + `env.py` 接 `DATABASE_URL` + `Base.metadata`），首个迁移包含既有 + 新表。

- [ ] **Step 3: 测试**（模型 CRUD + 级联）+ Commit `feat(db): graph config/version/publish_history/run_trace models + migration`

---

## Task 7: compiler（动态组装 + 安全检查 + 缓存）

**Files:** Create `app/core/graph/compiler.py`；Test `tests/unit/graph/test_compiler.py`

- [ ] **Step 1: 写 compiler**（spec §6.3.3）
```python
"""按 graph_config 动态组装 LangGraph + 安全检查 + 编译缓存。"""
from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.core.graph.config import GraphConfig
from app.core.graph.registry import registry
from app.core.graph.state import VragState

MAX_NODES = 30
MAX_REFLECT_ROUNDS = 2


class GraphSafetyError(ValueError):
    """图结构不安全。"""


def validate(config: GraphConfig) -> None:
    if len(config.nodes) > MAX_NODES:
        raise GraphSafetyError(f"too many nodes: {len(config.nodes)} > {MAX_NODES}")
    for n in config.nodes:
        if not registry.has(n.type):
            raise GraphSafetyError(f"node type not in registry: {n.type}")
    _check_reachable(config)
    _check_terminates(config)


def _check_reachable(config: GraphConfig) -> None:
    # BFS from entry, 所有节点应可达; exits 应被引用
    ...

def _check_terminates(config: GraphConfig) -> None:
    # 反向 BFS from exits, 所有节点应能到 exit; 反射类节点受 MAX_REFLECT_ROUNDS 约束
    ...


@lru_cache(maxsize=64)
def _compile_cached(config_json: str) -> "CompiledGraph":
    config = GraphConfig.model_validate_json(config_json)
    validate(config)
    g = StateGraph(VragState)
    for n in config.nodes:
        defn = registry.get(n.type)
        g.add_node(n.id, _wrap(defn, n.config))
    g.add_edge(START, config.entry)
    for e in config.edges:
        if e.condition:
            g.add_conditional_edges(e.src, _make_router(e.condition), {True: e.dst, False: ...})
        else:
            g.add_edge(e.src, e.dst)
    for x in config.exits:
        g.add_edge(x, END)
    return g.compile()


def compile(config: GraphConfig) -> "CompiledGraph":
    return _compile_cached(config.model_dump_json())


def _wrap(defn, node_config):
    """把节点函数包装成 LangGraph 接受的 runnable + 记录 IO (runner 注入 services)。"""
    ...
```

- [ ] **Step 2: 测试**（合法图编译成功；超节点数/未注册类型/不可达/无终止 → GraphSafetyError；缓存命中）+ lint + mypy + Commit `feat(graph): compiler with safety checks and cache`

> 注：`_wrap` 与 `_make_router` 的 services 注入 + condition 解析（受控键 `intent=knowledge_qa`）在实现时定；condition 只支持 `state_field=value` 形式（受控，非任意 DSL）。

---

## Task 8: `/graphs` API（CRUD + 版本 + dry-run + publish + rollback）

**Files:** Create `app/api/routes/graphs.py` + `app/core/graph/persistence.py`；Modify `router.py`；Test `tests/integration/test_graphs_api.py`

- [ ] **Step 1: `persistence.py`** —— PG CRUD：`create_graph`, `save_draft_version`, `list_graphs`, `get_version`, `publish_version`（draft→published，旧 published→archived，写 PublishHistory）, `rollback_to`, `get_published`。
- [ ] **Step 2: `graphs.py` 端点**
```python
@router.post("/graphs")              # 创建 + 初版 draft
@router.get("/graphs")               # 列表
@router.get("/graphs/{config_id}")   # 详情 (含版本列表)
@router.put("/graphs/{config_id}/draft")   # 保存新 draft 版本
@router.post("/graphs/{config_id}/test-run")  # 用样例 query 跑 draft (不持久化)
@router.post("/graphs/{config_id}/publish")   # 发布某版本
@router.post("/graphs/{config_id}/rollback")  # 回滚到某历史版本
@router.delete("/graphs/{config_id}")
```
- [ ] **Step 3: test-run** 用 `compiler.compile` + `runner.run`（Task 9）执行样例，返回 trace；不写 RunTrace。
- [ ] **Step 4: 测试**（创建→draft→test-run→publish→rollback 全流）+ lint + mypy + Commit `feat(api): /graphs CRUD with versioning, test-run, publish, rollback`

---

## Task 9: runner + `/chat` 升级（按 graph 执行 + 写 trace）

**Files:** Create `app/core/graph/runner.py`；Modify `app/api/routes/chat.py`；Test `tests/integration/test_chat_routed.py`

- [ ] **Step 1: `runner.py`**
```python
async def run(config: GraphConfig, state: VragState, services) -> dict:
    """编译并执行图, 收集每节点 IO 到 node_io, 返回最终 state + node_io。"""
    compiled = compile(config)
    # 用 services 注入 (services 通过 configurable 或闭包传给 _wrap)
    final_state = await compiled.ainvoke(state, config={"configurable": {"services": services}})
    return final_state
```
- [ ] **Step 2: `chat.py` 升级**：取 `get_published(graph_id)` 或默认图 seed；构造 `VragState`（含 trace_id）；`run`；写 `RunTrace`（route_trace + node_io）；SSE：先发 `event: retrieved`（从 final_state.retrieved_docs），再发 `generation`（可改为流式 Task 9 step 3，P1 先 `complete` 整段返回，流式增强留 open）。
- [ ] **Step 3: 流式**（可选）—— 若保留 SSE token 流，generate 节点需支持流式回调把 token 经 runner 透传到 SSE。P1 若复杂，先整段返回 generation（前端一次显示），流式作为 P1 收尾增强（见 Open Question）。
- [ ] **Step 4: 测试**（上传文档 → /chat → 验证 route_trace 写入、intent 正确、retrieved 与 generation 出现）+ lint + mypy + Commit `feat(graph): runner + /chat executes published graph and writes run_trace`

---

## Task 10: 节点级 trace 暴露 `GET /runs/{trace_id}`

**Files:** Create `app/api/routes/runs.py`；Modify `router.py`；Test `tests/integration/test_runs_api.py`

- [ ] **Step 1: 端点**返回 RunTrace（route_trace + node_io + intent + budget）。为 P1-B playground 节点级 trace 准备数据源。
- [ ] **Step 2: 测试**（执行一次 /chat → GET /runs/{trace_id} 返回完整 trace）+ Commit `feat(api): GET /runs/{trace_id} node-level trace`

---

## Task 11: 默认图 seed + 端到端验证

**Files:** Create `app/graph_seed.py`；Modify `main.py` lifespan（首次启动 seed 默认图）

- [ ] **Step 1: 默认图**（classifier → memory_recall → 按 intent 分支 → retrieve → generate / clarification / unsupported → reflect → memory_write → exit）
```python
DEFAULT_GRAPH = {
  "version": 1,
  "entry": "classifier",
  "nodes": [
    {"id": "classifier", "type": "classifier"},
    {"id": "memory_recall", "type": "memory_recall"},
    {"id": "retrieve", "type": "retrieve"},
    {"id": "generate", "type": "generate"},
    {"id": "clarify", "type": "clarification"},
    {"id": "unsupported", "type": "unsupported"},
    {"id": "reflect", "type": "reflect"},
    {"id": "memory_write", "type": "memory_write"},
  ],
  "edges": [
    {"from": "classifier", "to": "memory_recall"},
    {"from": "memory_recall", "to": "retrieve", "condition": "intent=knowledge_qa"},
    {"from": "memory_recall", "to": "generate", "condition": "intent=chitchat"},
    {"from": "memory_recall", "to": "clarify", "condition": "intent=clarification_needed"},
    {"from": "memory_recall", "to": "unsupported", "condition": "intent=unsupported_or_rejected"},
    {"from": "retrieve", "to": "generate"},
    {"from": "generate", "to": "reflect"},
    {"from": "clarify", "to": "reflect"},
    {"from": "unsupported", "to": "reflect"},
    {"from": "reflect", "to": "memory_write"},
  ],
  "exits": ["memory_write"],
}
```
- [ ] **Step 2: lifespan seed**（若 DB 无 published graph，写入 DEFAULT_GRAPH 并 publish）。
- [ ] **Step 3: 端到端验证清单**
  - 启动 → 默认图自动 seed
  - 上传文档 → `/chat "你好"` → intent=chitchat → 不检索 → generate
  - `/chat "产品怎么配置"` → intent=knowledge_qa → retrieve → generate
  - `/chat "帮我看看那个东西"` → intent=clarification → 追问
  - `/chat "帮我删除账号"` → intent=unsupported → 拒绝
  - `GET /runs/{trace_id}` 返回 route_trace + node_io
  - `/graphs` test-run → publish → rollback 全流
  - Langfuse 仍记录 LLM 调用
- [ ] **Step 4:** Commit `feat(graph): default graph seed + e2e routed chat`

---

## 验收标准（P1-A 完成 = 全部满足）

- [ ] `/chat` 按 published graph_config 执行，7 类 intent 至少 4 类可路由（chitchat/knowledge_qa/clarification/unsupported）
- [ ] `route_trace` 解释每次路由决策（rule/semantic/llm/clarify + 置信度）
- [ ] Node Registry 白名单：未注册节点类型被 compiler 拒绝
- [ ] 图安全检查：超节点数/不可达/无终止 → GraphSafetyError
- [ ] `/graphs` 全流：create → draft → test-run → publish → rollback
- [ ] `GET /runs/{trace_id}` 返回节点级 trace
- [ ] `pytest`（含新增 graph 测试）全绿、ruff、mypy clean
- [ ] 默认图首次启动自动 seed

## 不在 P1-A 范围（YAGNI / 后续 Phase）

- 可视化编排前端（React Flow 编辑器、节点参数表单、playground trace UI）= **P1-B**
- planner / executor / complex_task 分支实装 = P2
- memory_recall / memory_write 真实实装 = P3
- multimodal_doc / tool_action 分支 = P4（P1 路由到 unsupported 或 generate 占位）
- graph condition 的复杂表达式语言（只支持 `field=value` 受控形式）

## Open Questions（plan 里标注，实现时定）

1. **流式 vs 整段返回**：LangGraph `ainvoke` 不天然兼容 SSE token 流。P1 先整段返回 generation；流式增强（generate 节点用异步生成器 + runner 透传）作为 P1 收尾或 P1-B 前置。
2. **LangSmith**：是否额外接入（增强可观测），还是只用 Langfuse + PG run_trace。建议 P1 只用后者，LangSmith 作为可选。
3. **意图原型 embedding**：exemplar 静态 vs 可在管理端维护。P1 用静态 `INTENT_EXEMPLARS`，P1-B 暴露为可编辑。
4. **reflect 节点**：默认图含 reflect stub（无实际重试，透传）。真实 reflect（质量自检 + 分支回退）在 P2。

## 风险

1. **LangGraph services 注入**：节点是纯函数但需访问 retrieval/llm/embedder。用 LangGraph 的 `configurable` config 或闭包注入；实现时验证可测性（测试用 fake services）。
2. **condition 解析**：受控 `field=value` 需在 compiler 的 `_make_router` 里安全解析，避免注入。单测覆盖边界。
3. **Alembic 接入**：P0-A 用 `create_all`，P1-A 接 Alembic 需把既有表纳入版本管理（首次 autogenerate 可能检测到"既有表新建"，需 `--sql` 或 stamp 处理）。
