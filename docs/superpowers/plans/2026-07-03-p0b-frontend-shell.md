# P0-B: 前端管理端壳 (Admin Console Shell) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking. Frontend UI must follow the confirmed Design Brief, PRODUCT.md, DESIGN.md, and impeccable design laws.

**Goal:** 构建 v-rag 管理端 P0 前端壳（high-fi 可用，真实对接 P0-A 后端），并补齐后端 3 个配套端点，跑通"上传文档 → 提问 → 流式回答 + 看见检索命中"的完整闭环。

**Architecture:** 后端 3 个小扩展（`/chat` 返回 retrieved chunks、`GET /documents` 列表 + DELETE、`GET /config` 只读）。前端 Next.js 16 App Router 单体，承载于 Linear-like 的 App shell（左 rail + 主区），双主题（OKLCH tokens），Geist + Geist Mono，shadcn/ui 定制组件，TanStack Query 管服务端状态，Zustand 管 UI/主题状态，Motion 做克制动效。

**Tech Stack:** 后端扩展现有 FastAPI；前端 Next.js 16 / React 19 / TypeScript / Tailwind v4 / shadcn/ui / Geist / Phosphor Icons / TanStack Query / Zustand / Motion；测试 Vitest + @testing-library/react。

**Spec / Brief 参考:**
- Design Brief（本会话确认）：标准 P0 壳 / high-fi / 真实对接 / 扩展 /chat 返回 chunks
- `PRODUCT.md`（战略）、`DESIGN.md`（视觉 tokens）、spec §8（前端 6 模块，P0 取 Chat/知识库/配置/健康）

**相关 skills:** @impeccable（前端设计与实现原则）@frontend-design:frontend-design @python:test-first（后端）

---

## File Structure

### 后端扩展（在现有 `backend/app/` 上）
```
backend/app/api/routes/
├── chat.py            # Modify: 流式前先发 event: retrieved
├── documents.py       # Modify: 加 GET 列表 + DELETE
└── config.py          # Create: GET /config 只读
backend/app/api/schemas/
└── chat.py            # Create: RetrievedChunk / ChatEvent 响应模型
backend/tests/
├── unit/test_chat_chunks.py
├── integration/test_documents_list.py
└── integration/test_config_read.py
```

### 前端（新建 `frontend/`）
```
frontend/
├── package.json
├── next.config.ts
├── tsconfig.json
├── postcss.config.mjs
├── components.json              # shadcn config
├── app/
│   ├── layout.tsx               # root: providers + theme init
│   ├── globals.css              # OKLCH tokens (light + dark), base
│   ├── page.tsx                 # redirect -> /chat
│   └── (shell)/
│       ├── layout.tsx           # App shell: rail + main + cmdk
│       ├── chat/page.tsx
│       ├── knowledge/page.tsx
│       ├── config/page.tsx
│       └── health/page.tsx
├── components/
│   ├── shell/{rail,theme-toggle,command-palette,backend-status}.tsx
│   ├── chat/{chat-view,message,composer,retrieval-panel}.tsx
│   ├── knowledge/{doc-list,upload-dropzone,doc-status-badge}.tsx
│   ├── config/config-view.tsx
│   └── ui/                       # shadcn primitives (button, dialog, ...)
├── lib/
│   ├── api.ts                   # typed fetch wrappers
│   ├── sse.ts                   # useChatStream hook (parsed SSE events)
│   ├── theme.ts                 # Zustand theme store
│   └── types.ts
└── tests/ (vitest)
```

**职责边界：** `lib/` 只含纯逻辑与数据访问（可单测）；`components/` 按域分组；`(shell)` 路由组共享 App shell 布局。组件不直接 fetch，统一走 `lib/api` 与 `lib/sse`。

---

## Task 1: 后端 `/chat` 返回 retrieved chunks

**Files:** Modify `backend/app/api/routes/chat.py`；Create `backend/app/api/schemas/chat.py`；Test `backend/tests/unit/test_chat_chunks.py`

- [ ] **Step 1: 写 schema**
`app/api/schemas/chat.py`:
```python
"""Chat SSE 事件的数据模型。"""
from pydantic import BaseModel


class RetrievedChunkOut(BaseModel):
    """单条检索命中，发给前端渲染检索面板与 citation。"""
    chunk_id: str
    text: str
    score: float
    page: int | None = None
    document_id: str | None = None
```

- [ ] **Step 2: 写失败测试**（用 httpx AsyncClient + ASGITransport，断言 SSE 含 `event: retrieved` 且其后是 token 流）
```python
# test_chat_chunks.py: 注入 fake llm（固定 stream "Hi"）+ fake retrieval（固定 1 条 hit），
# POST /chat，逐行读 SSE，断言：
# 1) 首个事件 event: retrieved，data 含 chunk_id/text/score
# 2) 之后出现 data: Hi
# 3) 以 [DONE] 结束
```
Run: `uv run pytest tests/unit/test_chat_chunks.py -v` → FAIL

- [ ] **Step 3: 改 chat.py**：在 token 流之前 `yield` 一个 `event: retrieved` 行：
```python
async def event_stream() -> AsyncIterator[bytes]:
    import json
    payload = [
        {
            "chunk_id": h.chunk_id, "text": h.text, "score": h.score,
            "page": (h.metadata or {}).get("page"),
            "document_id": (h.metadata or {}).get("doc"),
        }
        for h in hits
    ]
    yield f"event: retrieved\ndata: {json.dumps(payload)}\n\n".encode()
    async for token in llm.stream(prompt, system="You are the v-rag assistant."):
        yield f"data: {token}\n\n".encode()
    yield b"data: [DONE]\n\n"
```
（`hits` 已在闭包中由 `retrieval.search` 得到。）

- [ ] **Step 4: 测试通过 + ruff + mypy**
Run: `uv run pytest tests/unit/test_chat_chunks.py -v && uv run ruff check . && uv run mypy app`
Expected: PASS, clean。

- [ ] **Step 5: Commit**
`feat(api): /chat emits retrieved chunks before token stream`

---

## Task 2: `GET /documents` 列表 + `DELETE /documents/{id}`

**Files:** Modify `backend/app/api/routes/documents.py`；Test `backend/tests/integration/test_documents_list.py`

- [ ] **Step 1: 写失败测试**（sqlite 内存库 + inmemory store，上传 1 文档后 GET 列表返回 1 条；DELETE 后再 GET 返回 0 条；同时断言向量库对应条目删除）
Run → FAIL。

- [ ] **Step 2: 实现 GET + DELETE**
```python
from sqlalchemy import select
from app.core.db.session import get_session_factory
from app.deps import get_store  # 需在 deps 暴露 VectorStore

@router.get("")
async def list_documents() -> list[dict]:
    """列出所有文档及其 chunk 数。"""
    sf = get_session_factory()
    async with sf() as session:
        docs = (await session.execute(select(Document).order_by(Document.created_at.desc()))).scalars().all()
        return [
            {"id": d.id, "filename": d.filename, "chunks": len(d.chunks),
             "created_at": d.created_at.isoformat()}
            for d in docs
        ]

@router.delete("/{document_id}")
async def delete_document(document_id: str) -> dict[str, str]:
    """删除文档及其 chunk（级联）+ 向量库对应条目。"""
    sf = get_session_factory()
    store = get_store()
    async with sf() as session:
        doc = await session.get(Document, document_id)
        if doc is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="document not found")
        chunk_ids = [c.id for c in doc.chunks]
        await session.delete(doc)
        await session.commit()
    if chunk_ids:
        await store.delete(chunk_ids)
    return {"deleted": document_id}
```
> deps.py 需在 `init_deps` 中把 `store` 存入 `_globals` 并暴露 `get_store()`。

- [ ] **Step 3: 测试通过 + lint + mypy** → Commit `feat(api): add GET /documents list and DELETE`

---

## Task 3: `GET /config` 只读

**Files:** Create `backend/app/api/routes/config.py`；Modify `router.py` include；Test `backend/tests/integration/test_config_read.py`

- [ ] **Step 1: 端点返回非密配置**（脱敏 SecretStr）
```python
@router.get("/config")
async def get_config() -> dict:
    """返回当前非敏感配置，供前端配置中心只读展示。"""
    s = get_settings()
    return {
        "llm_provider": s.llm_provider,
        "embed_provider": s.embed_provider,
        "openai_base_url": s.openai_base_url,
        "ollama_base_url": s.ollama_base_url,
        "ollama_llm_model": s.ollama_llm_model,
        "ollama_embed_model": s.ollama_embed_model,
        "embed_dim": s.embed_dim,
        "vector_store": s.vector_store,
        "database_url": s.database_url,  # 内部工具只读展示；若含密码可考虑掩码
        "has_openai_key": s.openai_api_key.get_secret_value() != "",
    }
```

- [ ] **Step 2: 测试**（断言返回上述字段、密钥不泄露原值）→ lint → mypy → Commit `feat(api): add GET /config read-only`

---

## Task 4: 前端项目初始化

**Files:** `frontend/package.json`, `next.config.ts`, `tsconfig.json`, `postcss.config.mjs`, `components.json`, `app/globals.css`(占位), `app/layout.tsx`(占位)

- [ ] **Step 1: 脚手架**
```bash
cd /Users/mac/ai-project/v-rag/frontend
npx create-next-app@latest . --ts --tailwind --app --no-src-dir --import-alias "@/*" --use-pnpm
pnpm add @tanstack/react-query zustand motion phosphor-react @geist/network @geist-ui/core 2>/dev/null || pnpm add geist
pnpm add -D vitest @testing-library/react @testing-library/jest-dom jsdom @vitejs/plugin-react
```
> Geist 字体用 `geist` 包（`import { GeistSans } from 'geist'`）。Phosphor 用 `@phosphor-icons/react`。shadcn 初始化：`npx shadcn@latest init`（选 New York / 定制 radii 与色板到 DESIGN.md tokens）。

- [ ] **Step 2: `next.config.ts`** 加 `rewrites` 把 `/api/*` 代理到 `http://localhost:8000/*`（开发期避免 CORS）。

- [ ] **Step 3: vitest 配置**（`vitest.config.ts` + `tests/setup.ts`）。

- [ ] **Step 4: 冒烟**（`pnpm dev` 起得来，`/` 渲染）→ Commit `feat(frontend): scaffold Next.js 16 + tooling`

---

## Task 5: Design tokens（OKLCH 双主题）

**Files:** `app/globals.css`

- [ ] **Step 1: 写 token CSS**（完整，来自 DESIGN.md）
```css
@import "tailwindcss";

@custom-variant dark (&:where(.dark, .dark *));

:root {
  --bg: oklch(0.99 0.005 250);
  --surface: oklch(0.975 0.006 250);
  --border: oklch(0.92 0.008 250);
  --text: oklch(0.32 0.02 255);
  --muted: oklch(0.55 0.015 255);
  --accent: oklch(0.62 0.14 235);
  --accent-fg: oklch(0.99 0.005 250);
  --success: oklch(0.70 0.15 155);
  --warn: oklch(0.78 0.14 75);
  --danger: oklch(0.65 0.18 25);
  --radius: 10px;
}
.dark {
  --bg: oklch(0.165 0.012 255);
  --surface: oklch(0.205 0.012 255);
  --border: oklch(0.27 0.015 255);
  --text: oklch(0.94 0.006 250);
  --muted: oklch(0.66 0.012 255);
  --accent: oklch(0.70 0.13 235);
  --accent-fg: oklch(0.16 0.012 255);
}
@theme inline {
  --color-bg: var(--bg); --color-surface: var(--surface);
  --color-border: var(--border); --color-text: var(--text);
  --color-muted: var(--muted); --color-accent: var(--accent);
  --color-accent-fg: var(--accent-fg);
  --font-sans: var(--font-geist-sans); --font-mono: var(--font-geist-mono);
}
html, body { background: var(--bg); color: var(--text); }
body { font-family: var(--font-geist-sans); -webkit-font-smoothing: antialiased; }
/* 无花哨：减少动效默认尊重 */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}
```
- [ ] **Step 2: `app/layout.tsx`** 加载 Geist 字体、`ThemeProvider`、TanStack QueryProvider，`<body>` 按 theme 切换 `.dark` class。

- [ ] **Step 3: Commit** `feat(frontend): OKLCH dual-theme tokens + providers`

---

## Task 6: App shell + rail + 主题切换

**Files:** `app/(shell)/layout.tsx`, `components/shell/{rail,theme-toggle,backend-status}.tsx`, `lib/theme.ts`

- [ ] **Step 1: `lib/theme.ts`** Zustand store（system | light | dark，apply 到 `<html class>`），单测切换逻辑。
- [ ] **Step 2: `rail.tsx`** 左侧固定导航（Chat / 知识库 / 配置 / 健康），Phosphor 图标 + 标签，active 态用 accent 微指示（非侧条纹 ban，用左侧 2px accent 短线仅在 active 项是可接受的语义状态，或用背景 tint + accent 文字）。底部 theme-toggle + version。
- [ ] **Step 3: `backend-status.tsx`** 轮询 `/api/health`（5s），显示徽章（ok/degraded/down），后端不可达时顶部细条提示。
- [ ] **Step 4: `(shell)/layout.tsx`** 组装 rail + main（max-w  generous + 真留白）。
- [ ] **Step 5: 测试**（rail 渲染 4 项、theme 切换加 `.dark`）→ Commit `feat(frontend): app shell with rail, theme, backend status`

---

## Task 7: API client + SSE hook

**Files:** `lib/api.ts`, `lib/sse.ts`, `lib/types.ts`

- [ ] **Step 1: `lib/types.ts`** TS 类型（`RetrievedChunk`, `DocOut`, `ConfigOut`, `ChatStreamEvent`）。
- [ ] **Step 2: `lib/api.ts`** fetch 封装：`listDocs()`, `uploadDoc(file)`, `deleteDoc(id)`, `getConfig()`, `getHealth()`。统一 base `/api`，错误抛 `ApiError`。
- [ ] **Step 3: `lib/sse.ts`** `useChatStream(query, top_k)` hook：
  - 用 `fetch` + `ReadableStream` 解析 SSE（不用 `EventSource`，因为 POST）
  - 区分 `event: retrieved`（解析 chunks，setState）与默认 `data:` token（append 到生成文本）
  - 暴露 `{ chunks, text, streaming, error, start() }`
  - 完整实现 + vitest 单测（mock fetch ReadableStream，断言 chunks 与 token 分流）
- [ ] **Step 4: Commit** `feat(frontend): typed api client + chat SSE hook`

```ts
// sse.ts 核心（完整在实现中）
export async function* parseSSE(resp: Response): AsyncGenerator<{event?: string; data: string}> {
  const reader = resp.body!.getReader(); const dec = new TextDecoder();
  let buf = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const frames = buf.split("\n\n"); buf = frames.pop()!;
    for (const f of frames) {
      let event: string | undefined, data = "";
      for (const line of f.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7);
        else if (line.startsWith("data: ")) data += line.slice(6);
      }
      yield { event, data };
    }
  }
}
```

---

## Task 8: Chat Playground

**Files:** `app/(shell)/chat/page.tsx`, `components/chat/{chat-view,message,composer,retrieval-panel}.tsx`

- [ ] **Step 1: `retrieval-panel.tsx`** 右栏渲染 `chunks`：每条 = source（文件名/页）+ score（mono）+ text（可展开）。空态"未检索到相关片段"。
- [ ] **Step 2: `message.tsx`** 用户/助手消息；助手消息 streaming 时尾部光标（克制，无闪烁动画当 reduced-motion）。
- [ ] **Step 3: `composer.tsx`** 输入框，Enter 发送 / Shift+Enter 换行，⌘/ 聚焦；禁用态（streaming 中）。
- [ ] **Step 4: `chat-view.tsx`** 组合 `useChatStream` + message 列表 + composer + retrieval-panel（双栏：左对话，右检索）。
- [ ] **Step 5: page** 接入 chat-view；空态"上传文档后即可开始问答"（检测 `listDocs()` 为空时）。
- [ ] **Step 6: 测试**（composer 发送触发 stream、retrieval-panel 渲染 chunks）→ Commit `feat(frontend): chat playground with retrieval panel`

---

## Task 9: 知识库管理

**Files:** `app/(shell)/knowledge/page.tsx`, `components/knowledge/{doc-list,upload-dropzone,doc-status-badge}.tsx`

- [ ] **Step 1: `upload-dropzone.tsx`** 拖拽 + 点击上传，调 `uploadDoc`，TanStack Query invalidation 刷新列表；上传中 / 失败态。
- [ ] **Step 2: `doc-list.tsx`** hairline 行表格：文件名 / 状态 / chunk 数（mono）/ 时间（mono）；行操作删除（确认后 `deleteDoc`）。
- [ ] **Step 3: `doc-status-badge.tsx`** P0 后端目前同步返回结果，状态为 `已就绪`/`失败`；预留 `解析中`/`索引中`（P4 异步任务对接）。
- [ ] **Step 4: 空态** "还没有文档，拖拽文本或 PDF 到这里" + 上传引导。
- [ ] **Step 5: 测试** → Commit `feat(frontend): knowledge base management`

---

## Task 10: 配置中心 + 健康

**Files:** `app/(shell)/config/page.tsx`, `components/config/config-view.tsx`, `app/(shell)/health/page.tsx`

- [ ] **Step 1: `config-view.tsx`** 只读展示 `getConfig()`：LLM Provider / Embedding / 向量库 / 数据库（值用 mono），密钥只显示 `has_openai_key`（已配置/未配置）。标注"P0 只读，修改需改后端环境变量"。
- [ ] **Step 2: health page** 详细健康（后端 `/health` + 关键配置概览）。
- [ ] **Step 3: loading / error 状态** → 测试 → Commit `feat(frontend): config center and health views`

---

## Task 11: 命令面板（⌘K）

**Files:** `components/shell/command-palette.tsx`

- [ ] **Step 1:** 用 shadcn `Dialog`/`Command`（或自建受控面板）。注册命令：导航到 4 页、新对话、上传文档（触发 dropzone）、切换主题、切换明暗。
- [ ] **Step 2:** 全局 `⌘K` / `Ctrl+K` 监听（在 `(shell)/layout` 注册），`Esc` 关闭。
- [ ] **Step 3:** 受控 UI（非自由 DSL），键盘上下选、Enter 执行。
- [ ] **Step 4:** 测试（打开、过滤、执行导航）→ Commit `feat(frontend): command palette (cmd+k)`

---

## Task 12: 状态完善 + 响应式 + a11y

**Files:** 各组件补全

- [ ] **全局:** 所有数据视图补 loading（骨架匹配布局）/ empty（构图引导）/ error（内联或 toast）。按钮 tactile（active `translate-y-px`）。
- [ ] **响应式:** 双栏 Chat 在 `< 1024px` 降为单栏（检索面板折叠为 drawer/tab）。rail 在 `< 768px` 折叠为图标或抽屉。
- [ ] **a11y:** 焦点环（accent）、对比度 WCAG AA、`prefers-reduced-motion`、`aria-*`、键盘可达。
- [ ] **i18n:** 全文无 em-dash（impeccable ban），文案功能化。
- [ ] **Commit** `feat(frontend): states, responsive, a11y pass`

---

## Task 13: 端到端对接验证

**Files:** `frontend/tests/e2e/rag-flow.spec.ts`（Playwright，可选）+ 手动验证脚本

- [ ] **Step 1: 起后端** `cd backend && docker compose up -d`（或 `uv run uvicorn`）
- [ ] **Step 2: 起前端** `cd frontend && pnpm dev`
- [ ] **Step 3: 手动走查清单**
  - 上传 `sample.txt` → 列表出现 → 状态已就绪 → chunk 数正确
  - Chat 提问 → 流式回答逐 token 出现 → 右侧检索面板显示命中 chunks + score
  - 切换主题（明/暗）→ 全站一致，无 #000/#fff 纯色
  - ⌘K 命令面板导航 + 上传
  - 关闭后端 → 顶部 backend-status 提示 down
  - 响应式：< 1024px 与 < 768px 布局正确
  - Lighthouse：LCP < 2.5s，对比度达标
- [ ] **Step 4:** 截图明/暗双主题存档；Commit `test(frontend): e2e rag flow walkthrough`

---

## 验收标准（P0-B 完成 = 全部满足）

- [ ] 后端 `/chat` 发 `event: retrieved` + token 流；`GET /documents`、`DELETE /documents/{id}`、`GET /config` 可用，全测试通过
- [ ] 前端 4 页（Chat / 知识库 / 配置 / 健康）+ App shell + ⌘K 命令面板全部可用
- [ ] Chat 真实对接：流式回答 + 右侧检索命中（show the thinking）
- [ ] 上传 → 列表 → 提问 闭环跑通
- [ ] 双主题（OKLCH，无 #000/#fff，无 AI 紫，无 em-dash）
- [ ] loading / empty / error / success 全状态；响应式；WCAG AA
- [ ] `pnpm test`、`pnpm lint`、`pnpm exec tsc --noEmit` 全绿
- [ ] 符合 DESIGN.md / PRODUCT.md / impeccable 设计法则（无侧条纹、无渐变文字、无装饰玻璃、无等大卡片网格）

## 不在 P0-B 范围（YAGNI）

- 可视化编排（React Flow 路由图编辑器）= P1
- 节点级 trace viewer = P1
- 记忆查看器 = P3
- 评测面板 = P5
- 认证 / 多租户 = P1+
- PDF 上传解析（P0 仅文本；PDF 在 P4 多模态）

## 风险与待定

1. **OKLCH 浏览器支持**：现代浏览器支持良好；若需旧浏览器兼容，降级到 sRGB 近似。
2. **SSE 解析鲁棒性**：`fetch + ReadableStream` 手写解析需覆盖分块边界（buf 拼接），Task 7 单测要含跨块用例。
3. **后端 CORS**：开发期用 next rewrite 代理规避；生产同源部署或后端开 CORS。
4. **shadcn 定制深度**：默认态被 ban，需按 DESIGN.md 调 radii/色板/字体，执行时务必 `init` 后立即改 token，勿用默认。
