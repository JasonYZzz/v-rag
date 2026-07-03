# P1-B: 前端可视化编排 (Visual Orchestration) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans. Frontend UI MUST follow PRODUCT.md / DESIGN.md / impeccable design laws (Linear-like, Restrained, dual-theme, no AI-violet, no em-dash).

**Goal:** 让用户在管理端拖拽编辑意图路由图（React Flow + Node Registry 白名单），配节点参数与条件边，dry-run / test-run / publish / rollback；并在 Playground 看节点级 trace，解释"为什么走了这条链"。这是 v-rag "show the thinking" 的核心交互，区别于普通 RAG 平台。

**Architecture:** 前端在 P0-B 的 Next.js shell 上加 `/orchestrate` 路由组。React Flow（`@xyflow/react`）渲染图，节点类型与 config schema 从后端 `GET /graphs/registry` 拉取（白名单单一来源）。TanStack Query 对接 `/graphs`（CRUD/版本/publish/rollback）与 `/runs/{trace_id}`（trace）。Zustand 管编辑器 transient 状态（选中节点、未保存改动）。

**Tech Stack:** Next.js 16 / React 19 / TS / Tailwind v4 / shadcn-ui（已有）+ `@xyflow/react` / `zustand` / `@tanstack/react-query` / Phosphor。后端小扩展 1 个端点。

**参考:** spec §8（可视化编排）/ §6.3（Node Registry 白名单 / 版本管理）/ §11（受控 UI 不开放 DSL）；PRODUCT.md / DESIGN.md；P1-A 的 `/graphs` `/runs` API。

**相关 skills:** @impeccable @frontend-design:frontend-design

---

## File Structure

```
backend/app/api/routes/graphs.py        # Modify: + GET /graphs/registry (节点类型 + config schema)
frontend/
├── app/(shell)/orchestrate/
│   ├── page.tsx                        # 图列表 + 进入编辑器
│   ├── [configId]/page.tsx             # 编辑器（画布 + 侧栏）
│   └── components/
│       ├── canvas.tsx                  # React Flow 画布封装
│       ├── nodes/{classifier,retrieve,generate,...}-node.tsx  # 按 type 渲染
│       ├── node-palette.tsx            # 白名单节点拖拽源
│       ├── node-param-form.tsx         # 按 config_schema 动态表单
│       ├── edge-condition-editor.tsx   # 受控 field=value
│       ├── version-panel.tsx           # draft/published/archived + publish/rollback
│       └── test-run-panel.tsx          # 样例 query + trace 结果
├── components/playground/
│   └── trace-view.tsx                  # /runs/{trace_id} 节点级 trace 可视化
├── lib/
│   ├── graphs-api.ts                   # /graphs /runs fetch 封装
│   ├── flow-graph.ts                   # React Flow <-> GraphConfig JSON 互转
│   └── orchestration-store.ts          # Zustand 编辑器状态
└── tests/unit/{flow-graph,orchestration-store}.test.ts
```

---

## Task 1: 后端 `GET /graphs/registry`（白名单单一来源）

**Files:** Modify `backend/app/api/routes/graphs.py`；Test `tests/integration/test_graphs_api.py`

- [ ] **Step 1: 端点** 返回 `registry.list()` 每项的 `{type, description, config_schema}`（schema 序列化为 JSON Schema）。
- [ ] **Step 2: 测试**（返回所有注册类型；config_schema 可空）+ lint + mypy + Commit `feat(api): GET /graphs/registry exposes node whitelist`

---

## Task 2: React Flow 依赖 + 画布 + GraphConfig 互转

**Files:** `package.json`(+`@xyflow/react`)；`lib/flow-graph.ts`；`app/(shell)/orchestrate/[configId]/components/canvas.tsx`；Test `tests/unit/flow-graph.test.ts`

- [ ] **Step 1:** `pnpm add @xyflow/react`
- [ ] **Step 2: `flow-graph.ts`** —— React Flow `{nodes, edges}` ↔ 后端 `GraphConfig{nodes, edges, entry, exits}` 双向转换（含 condition → edge.data.condition）。**单测覆盖双向、丢失 entry/exits 时恢复、condition 序列化。**
- [ ] **Step 3: `canvas.tsx`** —— `<ReactFlow>` 基础画布（暗/亮主题适配、背景 grid克制、Controls 极简）。节点/边的 add/remove/connect 受控于 store。
- [ ] **Step 4:** Commit `feat(orchestrate): React Flow canvas + flow<->config conversion`

---

## Task 3: Node Registry palette + 自定义节点

**Files:** `node-palette.tsx`；`nodes/*-node.tsx`；`orchestration-store.ts`

- [ ] **Step 1: `orchestration-store.ts`**（Zustand：选中节点 id、未保存 dirty、节点/边局部状态、参数 patch）。
- [ ] **Step 2: `node-palette.tsx`** —— 拉 `/graphs/registry`，渲染白名单节点列表（Phosphor 图标 + type + description），拖到画布即添加（只允许白名单类型，禁止自定义）。
- [ ] **Step 3: 自定义节点组件** —— 按 type 渲染（classifier/retrieve/generate/clarification/unsupported/...），显示标题 + 入口/出口 handle + 选中态；entry 节点标 accent 微指示。
- [ ] **Step 4:** 测试 + Commit `feat(orchestrate): node palette and typed node components`

---

## Task 4: 节点参数表单（受控，按 config_schema）

**Files:** `node-param-form.tsx`

- [ ] **Step 1:** 选中节点时，右侧栏渲染表单：字段按后端 `config_schema`（JSON Schema）动态生成（number/text/enum/select）。无 schema 的节点（stub）显示只读说明。
- [ ] **Step 2:** 改动写回 store（dirty=true），不直接存后端（save 在 Task 6）。
- [ ] **Step 3:** 受控：禁止任意字段名，只接受 schema 声明字段（spec §11 不开放 DSL）。
- [ ] **Step 4:** 测试 + Commit `feat(orchestrate): schema-driven node param form`

---

## Task 5: 边 + 条件（受控 field=value）

**Files:** `edge-condition-editor.tsx`；`flow-graph.ts`（条件序列化已在 Task 2，此处补 UI）

- [ ] **Step 1:** 连边时弹受控编辑器：`field` 下拉（限定 state 字段：intent 等）+ `value` 下拉（限定该字段 enum，如 Intent 7 值）。生成 `condition: "intent=knowledge_qa"`。
- [ ] **Step 2:** 条件边在画布上用 accent 虚线 + 标签显示 `intent=knowledge_qa`。
- [ ] **Step 3:** 校验：condition 必须是 `<whitelist_field>=<whitelist_value>` 形式，否则编辑器拒绝（前端校验 + 后端 compiler 兜底）。
- [ ] **Step 4:** 测试 + Commit `feat(orchestrate): controlled conditional edges`

---

## Task 6: 图 load / save（对接 /graphs）

**Files:** `lib/graphs-api.ts`；`app/(shell)/orchestrate/[configId]/page.tsx`

- [ ] **Step 1: `graphs-api.ts`** —— `listGraphs / getGraph / saveDraft(configId, graphConfig) / publish / rollback / testRun / getRegistry`。
- [ ] **Step 2:** 编辑器页 load `getGraph(configId)` → 转 React Flow → 画布。`Save draft` → `flow-graph.ts` 转 GraphConfig → `saveDraft`。dirty 守卫（未保存离开提示）。
- [ ] **Step 3:** 顶部状态条：当前 config 名 + 版本号 + dirty 指示 + Save/Publish 按钮。
- [ ] **Step 4:** 测试（load→编辑→save 往返）+ Commit `feat(orchestrate): load and save graph drafts`

---

## Task 7: 版本面板（draft/published/archived + publish + rollback）

**Files:** `version-panel.tsx`

- [ ] **Step 1:** 侧栏列出某 graph 的所有版本，按 status 分组（draft / published / archived），published 高亮（accent 微指示，非侧条纹）。
- [ ] **Step 2:** 操作：`Publish`（draft→published，旧 published→archived，调 `/graphs/{id}/publish`）、`Rollback`（回滚到历史版本）、`Test run`（进入 Task 8）。
- [ ] **Step 3:** PublishHistory 时间线（可选，简短）。
- [ ] **Step 4:** 测试 + Commit `feat(orchestrate): version panel with publish/rollback`

---

## Task 8: Test-run 面板（样例 query + trace）

**Files:** `test-run-panel.tsx`

- [ ] **Step 1:** 输入样例 query → `POST /graphs/{id}/test-run`（用当前 draft）→ 返回 trace。
- [ ] **Step 2:** 渲染 trace：命中的路由路径（高亮走过的节点/边）+ route_trace（rule/semantic/llm/clarify + 置信度 + reason）+ 最终 intent + generation。
- [ ] **Step 3:** 复用 Task 9 的 `trace-view` 组件渲染路径。
- [ ] **Step 4:** 测试 + Commit `feat(orchestrate): test-run panel with routed trace`

---

## Task 9: Playground 节点级 trace（/runs/{trace_id}）

**Files:** `components/playground/trace-view.tsx`；Modify `app/(shell)/chat/page.tsx`

- [ ] **Step 1: `trace-view.tsx`** —— 输入 trace，渲染：路由路径（节点序列 + 走过的边 accent 高亮）+ route_trace 分解（rule_result / semantic_result / llm_result / final_intent / confidence / reason）+ 每节点 IO 摘要（折叠）。
- [ ] **Step 2:** Chat 完成后，从响应拿 trace_id → `GET /runs/{trace_id}` → 在 Chat 右栏检索面板下方渲染 trace-view（"为什么走这条链"）。
- [ ] **Step 3:** 设计克制：trace 用 Geist Mono、折叠默认、accent 仅标路径。无花哨动效（仅 ease-out-quart 进入）。
- [ ] **Step 4:** 测试 + Commit `feat(playground): node-level trace view in chat`

---

## Task 10: 状态完善 + a11y + 响应式 + e2e

- [ ] **States:** 画布 loading（骨架）/ 空 graph（引导从 palette 拖节点）/ 保存失败（toast）/ 无 published graph（chat 提示去编排）。
- [ ] **a11y:** 画布键盘可达（Tab 节点、Delete 删、Enter 编辑参数）；对比度 AA；reduced-motion。
- [ ] **响应式:** 画布在 `< 1024px` 降为只读概览 + 侧栏抽屉；编辑建议桌面。
- [ ] **e2e 手动走查:** 创建 graph → 拖节点 → 连条件边 → save draft → test-run 看路径 → publish → 回 chat 提问看 trace-view 解释路由 → rollback。
- [ ] **Commit** `feat(orchestrate): states, a11y, responsive; e2e walkthrough`

---

## 验收标准（P1-B 完成 = 全部满足）

- [ ] `/orchestrate` 可视化编辑器：拖拽白名单节点、设参数、连条件边
- [ ] load/save draft 往返正确；React Flow ↔ GraphConfig 无损转换
- [ ] publish / rollback / test-run 全流可用
- [ ] Chat 右栏 trace-view 展示路由路径 + route_trace 解释
- [ ] 条件边受控（field=value），不接受任意 DSL
- [ ] 节点类型来自 `/graphs/registry`（白名单单一来源）
- [ ] 双主题、无 AI 紫、无 em-dash、对比度 AA
- [ ] `pnpm test` / `tsc --noEmit` / `pnpm lint` / `pnpm build` 全绿

## 不在 P1-B 范围（YAGNI / 后续）

- planner / complex_task 分支的可视化（节点已支持，但执行实装在 P2）
- 记忆查看器 = P3
- 评测面板 = P5
- 多 Agent 配置对比 / A-B 测试 = 后续
- 复杂条件表达式（AND/OR/嵌套）= 后续，P1 只 `field=value`

## 风险

1. **React Flow ↔ GraphConfig 转换**：React Flow 的 node/edge 模型与后端 GraphConfig 不 1:1（position 是前端专属、condition 在 edge.data）。Task 2 单测必须覆盖双向无损（position 存 node.data 或单独 map）。
2. **condition 受控**：前端编辑器 + 后端 compiler 双重校验；前端绕过（直接改 JSON）时后端必须拒绝。
3. **画布性能**：大图（>30 节点）受 P1-A MAX_NODES 限，无需虚拟化；但 React Flow 重渲染需 memo 节点组件。
4. **trace-view 数据**：依赖 P1-A `/runs/{trace_id}` 的 node_io 完整性；若 P1-A 未记录某节点 IO，trace-view 需优雅降级（显示"未记录"）。
