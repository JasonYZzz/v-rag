# P2-A: 自主规划引擎 (Autonomous Planning Engine) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans. TDD throughout.

**Goal:** 实装 `complex_task` 分支的自主规划能力（Plan-and-Execute + ReAct 循环）与真实 reflect（质量自检 + 分支回退，限次），让 v-rag 能处理"对比三款产品并给建议"这类多步任务。配套自有 Tool Registry 供 executor 调用。

**Architecture:** 在 P1-A graph 上新增 `planner` / `executor` / `synthesizer` 节点 + 把 `reflect` stub 升级为真实实现。executor 用 LangGraph `conditional_edges` 实现循环（`current_step` 递增，未完回 executor，完则转 synthesizer）。reflect 用 LLM-as-judge 判质量，低则按分支回退（受 `max_reflect_rounds=2` 约束）。自有 Tool Registry（白名单，spec §11）；MCP Adapter 留 P2-B。`complex_task` 分支接入默认图。`/chat` 流式 generation 透传（收尾 P1 的 open question）。

**Tech Stack:** 现有后端栈（LangGraph 已有），无新依赖。

**参考:** spec §6.2（planner/executor/reflect 图）、§10（P2）、§11（自有 Tool Registry，MCP 在 P2-B = P2-B 范畴）；P1-A 的 graph 模块。

**相关 skills:** @python:test-first @python:lint @python:typecheck @fastapi:module

---

## File Structure

```
backend/app/core/graph/nodes/
├── planner.py            # Create: LLM 分解 query -> steps[]
├── executor.py           # Create: 循环执行 steps
├── synthesizer.py        # Create: 综合 step_results -> generation
├── reflect.py            # Modify: stub -> 真实 LLM-as-judge + 回退
└── __init__.py           # Modify: 注册新节点
backend/app/core/tools/
├── __init__.py
├── registry.py           # Create: ToolRegistry (自有白名单)
└── builtin.py            # Create: 内置 tool stubs (search/db 占位)
backend/app/core/graph/runner.py    # Modify: 流式 generation 透传
backend/app/core/graph/state.py     # Modify: + plan/current_step/step_results/reflect_rounds
backend/app/graph_seed.py           # Modify: 默认图加 complex_task 分支
backend/app/api/routes/graphs.py    # Modify: registry 暴露 planner/executor/synthesizer
backend/tests/unit/graph/test_planner.py
backend/tests/unit/graph/test_executor.py
backend/tests/unit/graph/test_synthesizer.py
backend/tests/unit/graph/test_reflect.py
backend/tests/unit/test_tool_registry.py
backend/tests/integration/test_chat_complex_task.py
```

---

## Task 1: `VragState` 扩展 + planner 节点

**Files:** Modify `state.py`（+ plan/current_step/step_results/reflect_rounds）；Create `nodes/planner.py`；Test `test_planner.py`

- [ ] **Step 1: state 扩展**
```python
# state.py 新增字段 (NotRequired)
plan: NotRequired[list[dict]]           # [{type, input}, ...]
current_step: NotRequired[int]
step_results: NotRequired[list[dict]]
reflect_rounds: NotRequired[int]
```

- [ ] **Step 2: planner 节点**（LLM 分解 query → 有序 steps）
```python
"""planner: Plan-and-Execute 分解。每步 {type: retrieve|tool|generate, input}。"""
import json
from typing import Any
from app.core.graph.registry import NodeDefinition
from app.core.graph.state import VragState


async def plan(state: VragState, config: dict[str, Any], services: Any) -> dict[str, Any]:
    """LLM 把 query 分解为有序 steps，初始化执行游标。"""
    llm = services.llm
    prompt = (
        'Decompose the query into ordered steps. Each step: '
        '{"type": "retrieve"|"tool"|"generate", "input": "..."}. '
        'Reply JSON {"steps": [...]}. Query: ' + state["query"]
    )
    raw = await llm.complete(prompt, system="You are a planning assistant.")
    data = json.loads(raw)
    return {"plan": data["steps"], "current_step": 0, "step_results": []}


DEFN = NodeDefinition(type="planner", description="Decompose query into steps",
                      config_schema=None, execute=plan)
```

- [ ] **Step 3: 测试**（FakeLLM 返回固定 steps JSON → plan 节点输出 plan + current_step=0）+ lint + mypy + Commit `feat(graph): planner node`

---

## Task 2: 自有 Tool Registry

**Files:** Create `core/tools/registry.py` + `builtin.py`；Test `test_tool_registry.py`

- [ ] **Step 1: ToolRegistry**（白名单，executor 调用）
```python
"""自有 Tool Registry (spec §11: P0/P1 自有, P2 接 MCP 在 P2-B)。"""
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Protocol


class ToolFunc(Protocol):
    async def __call__(self, args: dict[str, Any], services: Any) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: type | None
    execute: ToolFunc


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, defn: ToolDefinition) -> None:
        if defn.name in self._tools:
            raise ValueError(f"tool already registered: {defn.name}")
        self._tools[defn.name] = defn

    def get(self, name: str) -> ToolDefinition:
        if name not in self._tools:
            raise KeyError(f"unknown tool: {name}")
        return self._tools[name]

    def list(self) -> list[str]:
        return sorted(self._tools)


tool_registry = ToolRegistry()
```

- [ ] **Step 2: 内置 stub tools**（P2-A 占位：`search_web` / `query_db` 返回 mock；P2-B 接真实/MCP）
- [ ] **Step 3: 测试**（注册/获取/重复报错/未知报错）+ Commit `feat(tools): self-hosted Tool Registry with builtin stubs`

---

## Task 3: executor 节点（循环执行 steps）

**Files:** Create `nodes/executor.py`；Modify `nodes/__init__.py` 注册；Test `test_executor.py`

- [ ] **Step 1: executor 节点**（每次调用执行一步；LangGraph 用 conditional 实现循环）
```python
"""executor: 执行 current_step 指向的 step, 推进游标。循环由 conditional_edges 驱动。"""
from typing import Any
from app.core.graph.state import VragState


async def execute_step(state: VragState, config: dict[str, Any], services: Any) -> dict[str, Any]:
    """执行一步并推进 current_step; 未完时由 conditional 回到自身。"""
    plan_steps = state.get("plan", [])
    i = state.get("current_step", 0)
    if i >= len(plan_steps):
        return {}  # done, conditional 转 synthesizer
    step = plan_steps[i]
    result = await _run_step(step, services)
    results = state.get("step_results", []) + [result]
    return {"current_step": i + 1, "step_results": results}


async def _run_step(step: dict, services: Any) -> dict:
    t = step.get("type")
    inp = step.get("input", "")
    if t == "retrieve":
        hits = await services.retrieval.search(inp, top_k=4)
        return {"step": step, "docs": [{"text": h.text, "score": h.score} for h in hits]}
    if t == "tool":
        # input 形如 {"tool": "search_web", "args": {...}}
        tool_name = inp.get("tool") if isinstance(inp, dict) else str(inp)
        tool = services.tools.get(tool_name)
        out = await tool.execute(inp.get("args", {}), services) if tool else {"error": "unknown tool"}
        return {"step": step, "result": out}
    if t == "generate":
        text = await services.llm.complete(inp)
        return {"step": step, "text": text}
    return {"step": step, "error": f"unknown step type: {t}"}


def should_continue(state: VragState) -> str:
    """conditional: 未完回 executor, 完则转 synthesizer。"""
    plan_steps = state.get("plan", [])
    return "executor" if state.get("current_step", 0) < len(plan_steps) else "synthesizer"
```

- [ ] **Step 2: 测试**（3 步 plan → executor 调 3 次 → step_results 长度 3 + current_step=3；should_continue 正确返回；未知 step type 记 error 不崩）+ lint + mypy + Commit `feat(graph): executor node with loop via conditional`

---

## Task 4: synthesizer 节点

**Files:** Create `nodes/synthesizer.py`；Test `test_synthesizer.py`

- [ ] **Step 1: synthesizer**
```python
"""synthesizer: 综合 step_results 为最终 generation。"""
async def synthesize(state, config, services):
    results = state.get("step_results", [])
    parts = [r.get("text") or r.get("result") or str(r) for r in results]
    summary = "\n---\n".join(parts)
    final = await services.llm.complete(
        f"Synthesize a final answer from these step results.\nResults:\n{summary}\n\nOriginal query: {state['query']}",
        system="You are the v-rag assistant.",
    )
    return {"generation": final}
```

- [ ] **Step 2: 测试**（FakeLLM + 2 步 results → synthesizer 调用含两段 + generation）+ Commit `feat(graph): synthesizer node`

---

## Task 5: reflect 真实化（LLM-as-judge + 分支回退）

**Files:** Modify `nodes/reflect.py`；Test `test_reflect.py`

- [ ] **Step 1: 真实 reflect**
```python
"""reflect: LLM-as-judge 质量自检 + 分支回退 (受 max_reflect_rounds)。"""
import json
from typing import Any
from app.core.graph.state import VragState

MAX_REFLECT_ROUNDS = 2


async def reflect(state: VragState, config: dict[str, Any], services: Any) -> dict[str, Any]:
    """判定 generation 质量; 低质且未超限时, 由 conditional 回退到对应分支节点。"""
    rounds = state.get("reflect_rounds", 0)
    if rounds >= MAX_REFLECT_ROUNDS:
        return {"reflection": {"quality": "capped", "retry": False}, "reflect_rounds": rounds}
    verdict = await services.llm.complete(
        'Is this answer good for the query? Reply JSON '
        '{"quality": "good"|"poor", "reason": "..."}.\n'
        f"Query: {state['query']}\nAnswer: {state.get('generation', '')}"
    )
    data = json.loads(verdict)
    return {"reflection": data, "reflect_rounds": rounds + 1}


def retry_target(state: VragState) -> str:
    """conditional: 质量差且未超限 -> 按当前 intent 回退; 否则 -> memory_write。

    knowledge_qa -> retrieve; complex_task -> planner; 其余 -> memory_write (不重试)。
    """
    refl = state.get("reflection", {})
    if refl.get("quality") == "poor" and state.get("reflect_rounds", 0) < MAX_REFLECT_ROUNDS:
        intent = state.get("intent")
        if intent and intent.value == "knowledge_qa":
            return "retrieve"
        if intent and intent.value == "complex_task":
            return "planner"
    return "memory_write"
```

- [ ] **Step 2: 测试**（good → retry=False；poor+rounds<max → retry=True + 回退目标正确；超限 → capped）+ Commit `feat(graph): real reflect with LLM judge and branch-aware retry`

---

## Task 6: complex_task 分支接入默认图

**Files:** Modify `graph_seed.py`；Modify `nodes/__init__.py`（注册 planner/executor/synthesizer）；Test `tests/integration/test_chat_complex_task.py`

- [ ] **Step 1: 注册新节点** 到 `registry`（planner/executor/synthesizer）。
- [ ] **Step 2: 默认图扩展**（classifier → memory_recall → 按 intent 分支；complex_task → planner → executor(loop) → synthesizer → reflect → memory_write）
```python
# graph_seed.py DEFAULT_GRAPH 新增节点与边:
{"id": "planner", "type": "planner"},
{"id": "executor", "type": "executor"},
{"id": "synthesizer", "type": "synthesizer"},
# edges:
{"from": "memory_recall", "to": "planner", "condition": "intent=complex_task"},
{"from": "planner", "to": "executor"},
# executor 自循环 + 转 synthesizer 由 conditional 驱动 (compiler 需支持节点级 conditional)
{"from": "executor", "to": "synthesizer"},          # 默认/完成边
{"from": "synthesizer", "to": "reflect"},
# reflect 回退: poor 且未超限 -> 回 retrieve/planner; 否则 memory_write
{"from": "reflect", "to": "memory_write"},
```
> 注：executor 自循环 + reflect 分支回退需 compiler 支持节点级 `conditional_edges`（P1-A compiler 已支持 `condition`；此处需扩展支持"无条件回边 + 条件转出"并存）。实现时在 compiler 补 `add_conditional_edges` 的回边支持，并单测覆盖。

- [ ] **Step 3: 集成测试**（complex_task query → 路由到 planner → executor 多步 → synthesizer → reflect → memory_write；route_trace 记录 complex_task）+ Commit `feat(graph): complex_task branch in default graph`

---

## Task 7: `/chat` 流式 generation 透传

**Files:** Modify `runner.py` + `chat.py`；Test 更新

- [ ] **Step 1: runner 流式支持** —— generate / synthesizer 节点支持异步生成器（`async def stream(...) -> AsyncIterator[str]`），runner 用 `astream_events` 或回调把 token 透传到 SSE 队列。
- [ ] **Step 2: chat.py SSE** —— 先发 `event: retrieved`（如有），再流式发 generation token，最后 `[DONE]`。
- [ ] **Step 3: 测试**（FakeLLM stream → /chat SSE 含 retrieved + 逐 token + DONE）+ Commit `feat(graph): stream generation through runner to /chat SSE`

> 若 LangGraph `astream` 与节点异步生成器集成复杂，P2-A 可先保留整段返回（P1 现状），流式作为 P2 收尾；但优先尝试，因 SSE 流式是用户体验关键。

---

## Task 8: trace 增强（planner/executor 节点 IO）

**Files:** Modify `runner.py`（节点 IO 记录到 run_trace.node_io）；Modify `/runs/{trace_id}` 确保含新节点

- [ ] **Step 1: runner 记录** planner 的 steps / executor 的每步 result / synthesizer 的综合 / reflect 的 verdict。
- [ ] **Step 2: 测试**（complex_task 执行后 GET /runs/{trace_id} 含 planner/executor/synthesizer/reflect 的 IO）+ Commit `feat(graph): trace planner/executor/synthesizer IO`

---

## Task 9: 端到端验证

- [ ] **Step 1: e2e 清单**
  - `/chat "对比 A B C 三款产品并给建议"` → intent=complex_task → planner 分解 → executor 多步 → synthesizer 综合 → generation
  - reflect 判 poor → 回退 planner 重试（rounds 递增，≤2）
  - route_trace 含 complex_task + planner steps
  - GET /runs/{trace_id} 含完整节点 IO
  - tool step（search_web stub）被 executor 调用
  - 默认图首启 seed 含 complex_task 分支
- [ ] **Step 2: 全量 pytest + ruff + mypy 全绿**
- [ ] **Step 3:** Commit `test(graph): complex_task e2e with planning and reflect`

---

## 验收标准（P2-A 完成 = 全部满足）

- [ ] `complex_task` 分支可路由，planner 分解、executor 循环、synthesizer 综合、reflect 判定全可用
- [ ] reflect 限次（max_reflect_rounds=2）+ 分支感知回退（knowledge_qa→retrieve, complex_task→planner）
- [ ] 自有 Tool Registry 注册/调用可用，executor 能执行 tool step
- [ ] `/chat` 流式 generation（若 Task 7 完成）；否则整段返回不退化
- [ ] trace 含 planner/executor/synthesizer/reflect IO
- [ ] pytest / ruff / mypy 全绿
- [ ] 默认图含 complex_task 分支

## 不在 P2-A 范围（YAGNI / P2-B / 后续）

- **MCP Adapter**（接外部 MCP server）= **P2-B**
- 真实 tool 实现（search_web 接真实搜索、query_db 接真实 DB）= P2-B 或按需
- multimodal_doc / tool_action 分支实装 = P4（P2-A 路由到 unsupported 或 generate 占位）
- 前端：planner/executor 节点的可视化（P1-B React Flow 已支持任意白名单节点，无需前端改动；trace-view 自动展示新节点 IO）

## Open Questions

1. **planner 输出 schema 强度**：LLM 可能返回非法 JSON 或未知 step type。Task 1 测试需覆盖容错（解析失败 → 降级为单步 generate）。
2. **executor 循环与 LangGraph**：自循环需 compiler 支持节点回边。Task 6 实现时验证 LangGraph 对 `executor→executor` 回边的处理（需显式 conditional，不能 add_edge 自身）。
3. **reflect LLM-as-judge 成本**：每次回答多一次 LLM 调用。可配置开关（默认开，质量敏感时关）。
4. **流式 vs 整段**：Task 7 若 LangGraph astream 集成受阻，先保整段返回，流式延后但标注。

## 风险

1. **LangGraph 循环**：executor 自循环 + reflect 回退是 P2-A 技术难点。Task 6 compiler 扩展是关键，单测必须覆盖"回边不触发无限循环"（受 max_reflect_rounds + steps 长度双重约束）。
2. **planner 输出不稳定**：LLM 分解可能不符合 schema。Task 1 容错 + Task 3 未知 type 记 error 不崩。
3. **Tool Registry 与 MCP 边界**：P2-A 自有 registry，P2-B 接 MCP。设计 registry 接口时预留 MCP adapter 兼容（ToolDefinition 能包装 MCP tool）。
