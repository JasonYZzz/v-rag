# P4-A: 多模态文档引擎 (Multimodal Document Engine) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans. TDD throughout.

**Goal:** 实装 v-rag 第四大差异化特性——多模态文档 RAG。让 v-rag 能问答图文 PDF / 表格 / 扫描件：DocumentProfiler 按质量路由解析器，Canonical DocumentBlock 统一输出，多粒度 chunking + 表格三表示，**ColPali 二阶段视觉检索**（免 OCR 保版式），**OCR 插件化**处理扫描件，VLM 生成，knowledge_qa 文本优先 fallback 视觉，`multimodal_doc` 分支接入默认图。

**Architecture:** 扩展 P0-A `core/document`（Profiler + 路由 + Canonical Block + 多粒度 + 表格三表示 + Citation + 统一 source id）。新建 `core/multimodal`（ColPali 视觉索引 + 二阶段检索 + VLM provider + 视觉向量库）与 `core/ocr`（插件协议 + PaddleOCR-VL 默认 + 分层 + 回灌 DocumentBlock）。`/documents` 升级支持 PDF + DocumentProfiler + **双索引**（文本 + 视觉，统一 source id）+ 异步任务状态。默认图加 `multimodal_doc` 分支（classifier → memory_recall → colpali_retrieve → vlm_generate → reflect）。

**Tech Stack:** 现有后端栈 + `colpali-engine` + `paddleocr`（或 paddleocr-vl）+ `Pillow` + `torch`。Docling / Unstructured 可选（占位，P4-A 主用 PyMuPDF + OCR + ColPali）。

**参考:** spec §7（文档处理 + 多模态 + OCR 全部设计）、§7.2（ColPali 二阶段 / knowledge_qa 文本优先）、§6.2.1（multimodal_doc intent）；用户第 3 段 15 条补强（DocumentProfiler / Canonical Block / 表格三表示 / Citation / 统一 source id / ColPali 二阶段 / OCR 协议增强 + 回灌 / 解析任务队列）。

**相关 skills:** @python:test-first @python:lint @python:typecheck @fastapi:endpoint @fastapi:module

---

## File Structure

```
backend/app/core/document/               # P0-A 已有, P4 扩展
├── models.py             # Modify: Canonical DocumentBlock (扩展 block_type/table 三表示/bbox/heading_path/parent_id/confidence)
├── profiler.py           # Create: DocumentProfiler
├── parser.py             # Modify: 路由 (PyMuPDF/Docling/Unstructured/OCR)
├── chunker.py            # Modify: 多粒度 (parent-child/section/page/table/image)
├── citation.py           # Create: Citation + 统一 source id
└── parsers/
    ├── pymupdf_parser.py        # 纯文本/数字 PDF
    ├── docling_parser.py         # 复杂版式 (占位/可选)
    ├── unstructured_parser.py    # 异构格式 (占位/可选)
    └── ocr_pipeline.py           # 扫描件 -> OCR -> 回灌 DocumentBlock
backend/app/core/multimodal/            # P4 新建
├── __init__.py
├── colpali.py            # ColPali 视觉索引 + 二阶段检索 (page retrieve -> region crop -> VLM)
├── vlm_provider.py       # VLM provider 抽象 (OpenAI GPT-4V / Ollama Qwen2-VL)
└── visual_store.py       # 页面级视觉向量索引 (复用 storage 抽象)
backend/app/core/ocr/                    # P4 新建
├── __init__.py
├── protocol.py           # OCRPlugin/OCRResult/OCRBlock 协议 (bbox/confidence/engine_version)
├── registry.py            # 分层注册 (default/optional/cloud)
└── plugins/paddleocr_vl.py
backend/app/core/graph/nodes/
├── colpali_retrieve.py   # Create: 视觉检索节点
└── vlm_generate.py       # Create: VLM 生成节点
backend/app/core/provider/base.py      # Modify: + VLMProvider 协议
backend/app/api/routes/documents.py   # Modify: PDF + Profiler + 双索引 + 任务状态
backend/app/graph_seed.py              # Modify: multimodal_doc 分支
backend/tests/unit/{document,multimodal,ocr}/...
backend/tests/integration/test_multimodal_doc.py
```

---

## Task 1: Canonical DocumentBlock 扩展 + DocumentProfiler

**Files:** Modify `document/models.py`；Create `document/profiler.py`；Test `test_profiler.py`

- [ ] **Step 1: DocumentBlock 扩展**（spec §7.1.3）
```python
@dataclass
class DocumentBlock:
    """Canonical Block: 所有 parser/OCR/ColPali 输出归一化为此结构。"""
    id: str
    document_id: str
    page: int | None = None
    block_type: str = "paragraph"   # title|paragraph|table|image|figure|formula|list|header|footer
    text: str | None = None
    html: str | None = None         # 表格/结构化 HTML
    markdown: str | None = None     # 表格 markdown
    table_json: dict | None = None  # 表格结构化 (程序处理 + citation)
    bbox: list[float] | None = None
    heading_path: tuple[str, ...] = ()
    parent_id: str | None = None
    metadata: dict = field(default_factory=dict)
    confidence: float = 1.0
```

- [ ] **Step 2: DocumentProfiler**（spec §7.1.1，路由不只看扩展名）
```python
@dataclass
class DocumentProfile:
    file_type: str
    page_count: int
    is_scanned_pdf: bool
    text_extractable_ratio: float
    image_area_ratio: float
    table_density: float
    formula_density: float
    language: str | None
    layout_complexity: float        # 0-1
    quality_score: float            # 0-1


def profile(path: str) -> DocumentProfile:
    """解析前画像, 决定路由到哪个 parser。"""
    import pymupdf
    with pymupdf.open(path) as doc:
        pages = doc.page_count
        text_chars = sum(len(p.get_text()) for p in doc)
        img_areas = sum(_img_area(p) for p in doc)
        # is_scanned: 文本极少但有图
        is_scanned = pages > 0 and text_chars / max(pages, 1) < 50
        text_ratio = text_chars / max(sum(p.rect.width * p.rect.height for p in doc), 1)
        return DocumentProfile(
            file_type=path.rsplit(".", 1)[-1].lower(), page_count=pages,
            is_scanned_pdf=is_scanned, text_extractable_ratio=text_ratio,
            image_area_ratio=img_areas, table_density=_table_density(doc),
            formula_density=0.0, language=None,
            layout_complexity=min(1.0, img_areas + _table_density(doc)),
            quality_score=0.0 if is_scanned else min(1.0, text_ratio * 10),
        )


def route_parser(profile: DocumentProfile) -> str:
    """按画像选 parser: 扫描->ocr; 纯文本->pymupdf; 复杂版式->docling; 异构->unstructured。"""
    if profile.is_scanned_pdf:
        return "ocr"
    if profile.layout_complexity > 0.6 or profile.table_density > 0.3:
        return "docling"     # P4-A 占位, 降级 pymupdf (Task 2)
    return "pymupdf"
```

- [ ] **Step 3: 测试**（纯文本 PDF → pymupdf；扫描件 → ocr；复杂版式 → docling）+ Commit `feat(document): Canonical Block + DocumentProfiler with routing`

---

## Task 2: 解析器路由 + PyMuPDF 实装（Docling/Unstructured 占位）

**Files:** Create `document/parsers/{pymupdf_parser,docling_parser,unstructured_parser,ocr_pipeline}.py`；Modify `parser.py`（调 profiler + route）；Test `test_parsers.py`

- [ ] **Step 1: PyMuPDF 解析器**（纯文本 + 表格提取）
```python
def parse_pymupdf(path: str) -> list[DocumentBlock]:
    """纯文本/数字 PDF: 逐页提取文本 + 表格 (PyMuPDF find_tables)。"""
    import pymupdf
    blocks = []
    with pymupdf.open(path) as doc:
        for page_num, page in enumerate(doc, 1):
            text = page.get_text().strip()
            if text:
                blocks.append(DocumentBlock(id=..., document_id=..., page=page_num,
                                            block_type="paragraph", text=text))
            for t in page.find_tables():  # 表格三表示
                blocks.append(_table_block(t, page_num))
    return blocks
```
- [ ] **Step 2: Docling / Unstructured 占位**（注册但 P4-A 降级 pymupdf，标注 TODO；按需实装）
- [ ] **Step 3: `parser.py` 路由** —— `parse(path) = profile → route_parser → 对应 parser`
- [ ] **Step 4: 测试**（纯文本 PDF 走 pymupdf；表格提取三表示；扫描件走 ocr_pipeline）+ Commit `feat(document): parser routing with PyMuPDF (Docling/Unstructured stubbed)`

---

## Task 3: 多粒度 chunking + 表格三表示 + Citation（统一 source id）

**Files:** Modify `document/chunker.py`；Create `document/citation.py`；Test `test_chunker.py` + `test_citation.py`

- [ ] **Step 1: 多粒度 chunking**（spec §7.1.4）
```python
# chunker.py 支持: paragraph / section / parent-child / table / page / image-figure
def chunk_blocks(blocks: list[DocumentBlock], *, granularity: str = "paragraph",
                 chunk_size: int = 500, overlap: int = 50) -> list[DocumentBlock]:
    """按粒度切分; table 保留三表示不切; parent-child 保留父子关系。"""
    # paragraph: 按文本长度 (P0-A 已有)
    # section: 按 heading_path 分组
    # parent-child: 父块 + 子块引用 (parent_id)
    # table: 整块保留 (markdown/html/json)
    # page: 每页一块
```
- [ ] **Step 2: 表格三表示**（`_table_block` 生成 `table_markdown` + `table_html` + `table_json`，存 block.markdown/html/table_json）
- [ ] **Step 3: Citation + 统一 source id**
```python
@dataclass
class Citation:
    document_id: str
    source_file: str
    page: int | None
    bbox: list[float] | None
    heading_path: tuple[str, ...]
    block_id: str
    parser_name: str
    parser_version: str


# 统一 id: document_id / page_id / block_id / text_chunk_id / visual_page_id 共享
# 文本索引与视觉索引用同一组 id, 前端 trace 能并排展示同页文本命中 + 视觉命中。
def make_block_id(document_id: str, page: int, idx: int) -> str:
    return f"{document_id}:p{page}:b{idx}"
```
- [ ] **Step 4: 测试**（parent-child 保留 parent_id；table 三表示并存；Citation 回溯字段全）+ Commit `feat(document): multi-granularity chunking + table triple-repr + citation`

---

## Task 4: OCR 插件协议 + PaddleOCR-VL 默认 + 回灌 DocumentBlock

**Files:** Create `ocr/{protocol,registry}.py` + `ocr/plugins/paddleocr_vl.py` + `document/parsers/ocr_pipeline.py`；Test `test_ocr.py`

- [ ] **Step 1: 协议**（spec §7.3.1，含 bbox/confidence/engine_version）
```python
@dataclass
class OCRBlock:
    text: str
    bbox: list[float]
    confidence: float
    block_type: str | None = None


@dataclass
class OCRResult:
    text: str
    blocks: list[OCRBlock]
    language: str | None
    confidence: float
    engine: str
    engine_version: str
    metadata: dict = field(default_factory=dict)


class OCRPlugin(Protocol):
    name: str
    supported_langs: list[str]
    async def recognize(self, image: bytes) -> OCRResult: ...
```
- [ ] **Step 2: 分层 registry**（default: paddleocr_vl；optional: 第三方；cloud: adapter；`Unlimited-OCR` 不作默认强依赖）
- [ ] **Step 3: PaddleOCR-VL 插件**（调 paddleocr；若不可用，registry 返回 None，ocr_pipeline 标 block 为 unsupported）
- [ ] **Step 4: ocr_pipeline 回灌** —— OCR 结果归一化为 DocumentBlock（OCRBlock.bbox → block.bbox，text → block.text），与文本/视觉路径统一
- [ ] **Step 5: 测试**（mock OCR plugin → 回灌 DocumentBlock；bbox/confidence/engine_version 保留；plugin 不可用降级）+ Commit `feat(ocr): plugin protocol + PaddleOCR-VL + rehydrate to DocumentBlock`

---

## Task 5: ColPali 视觉索引 + 二阶段检索

**Files:** Create `multimodal/{colpali,visual_store}.py`；Test `test_colpali.py`

- [ ] **Step 1: 视觉向量索引**（页面级 patch embedding，存 visual_store 复用 storage 抽象，metadata 含 page_id/document_id）
- [ ] **Step 2: ColPali 索引** —— PDF 每页 → 图像 → ColPali encode → 存 visual_store（`uv add colpali-engine pillow torch`）
```python
class ColPaliIndexer:
    """页面级视觉索引 (免 OCR, 保版式/表格/图表)。"""
    async def index_document(self, path: str, document_id: str) -> list[str]:
        """每页 -> 图像 -> ColPali embedding -> 存 visual_store; 返回 visual_page_ids (与 text 索引共享 document_id/page_id)。"""
        ...
```
- [ ] **Step 3: 二阶段检索**（spec §7.2.1）
```python
async def retrieve(query: str, *, top_k: int = 4, do_crop: bool = True) -> list[VisualHit]:
    """page-level retrieve -> top-k page candidates -> optional region/crop -> VLM/rerank。"""
    pages = await visual_store.search(await colpali_embed(query), top_k=top_k)
    if do_crop:
        pages = [_crop_region(p) for p in pages]   # 复杂页面局部裁剪, 不整页丢 VLM
    return pages
```
- [ ] **Step 4: 测试**（mock ColPali embed → 索引/检索；二阶段 crop 逻辑）+ Commit `feat(multimodal): ColPali page-level index + two-stage retrieval`

> 风险：ColPali 需 torch + 模型权重。若环境不可用，Task 5 提供文本 fallback（visual_store 空时 retrieve 返回 []，multimodal_doc 降级 unsupported 或文本检索）。降级路径在 Task 9 接入图时处理。

---

## Task 6: VLM provider 抽象 + 实现

**Files:** Modify `provider/base.py`（+ VLMProvider 协议）；Create `multimodal/vlm_provider.py`；Modify `provider/factory.py`；Test `test_vlm_provider.py`

- [ ] **Step 1: VLMProvider 协议**
```python
class VLMProvider(Protocol):
    """视觉语言模型: 输入图像 + 文本 query -> 回答。"""
    async def describe(self, images: list[bytes], query: str, *, system: str = "") -> str: ...
```
- [ ] **Step 2: 实现** —— OpenAI GPT-4V（httpx，vision input）/ Ollama Qwen2-VL（本地）。经 provider 抽象切换（spec §7.2.3）。
- [ ] **Step 3: factory** —— `build_vlm_provider(kind, ...)`
- [ ] **Step 4: 测试**（mock httpx → OpenAI vision 调用；Ollama vision）+ Commit `feat(provider): VLM provider abstraction with OpenAI + Ollama`

---

## Task 7: knowledge_qa 文本优先 fallback 视觉

**Files:** Modify `graph/nodes/retrieve.py` + 新增 fallback 逻辑；Test `test_knowledge_fallback.py`

- [ ] **Step 1: 文本优先**（spec §7.2.2）
```python
async def retrieve(state, config, services):
    """knowledge_qa 默认文本检索; 文本置信低或文档含大量表格/图片/扫描页时 fallback 视觉。"""
    hits = await services.retrieval.search(state["query"], top_k=config.get("top_k", 4))
    if _text_confidence(hits) >= TEXT_THRESHOLD or not _has_visual_content(state):
        return {"retrieved_docs": [h... for h in hits]}
    # fallback ColPali 视觉检索
    visual = await services.colpali.retrieve(state["query"], top_k=config.get("top_k", 4))
    return {"retrieved_docs": [v... for v in visual], "multimodal_hits": visual}
```
- [ ] **Step 2: `_text_confidence`**（top hit score 阈值）+ `_has_visual_content`（文档 profile 含表格/图/扫描）
- [ ] **Step 3: 测试**（高置信→纯文本；低置信+有图→fallback 视觉；高置信+有图→仍文本）+ Commit `feat(graph): knowledge_qa text-first with visual fallback`

---

## Task 8: `/documents` 升级（PDF + Profiler + 双索引 + 任务状态）

**Files:** Modify `api/routes/documents.py`；Create 异步任务状态；Test `test_documents_pdf.py`

- [ ] **Step 1: PDF 上传** —— 接 PDF → profile → route_parser → 解析 → chunk → **双索引**（文本 embedding + ColPali 视觉，共享 document_id/page_id/block_id）+ PG 元数据（含 parser_name/version、profile 摘要）
- [ ] **Step 2: 解析任务状态**（spec §8 知识库管理：uploading→profiling→parsing→ocr_running→chunking→embedding→visual_indexing→completed/failed）—— P4-A 同步返回（P0-B 现状），状态字段预留异步（P4-B 前端用）
- [ ] **Step 3: 重建索引** —— `POST /documents/{id}/reindex`（text / visual 分别重建）
- [ ] **Step 4: 测试**（PDF 上传 → 双索引 → 列表含 chunk 数 + parser；reindex）+ Commit `feat(api): /documents PDF upload with profiler + dual index + task status`

---

## Task 9: multimodal_doc 分支接入默认图

**Files:** Create `graph/nodes/{colpali_retrieve,vlm_generate}.py`；Modify `graph_seed.py` + `nodes/__init__.py`；Test `test_multimodal_doc.py`

- [ ] **Step 1: colpali_retrieve 节点**（调 ColPali 二阶段检索，返回 visual_hits + citation page+bbox）
- [ ] **Step 2: vlm_generate 节点**（调 VLM，输入页面图 + query → generation）
```python
async def vlm_generate(state, config, services):
    hits = state.get("multimodal_hits", [])
    images = [h.image_bytes for h in hits]
    text = await services.vlm.describe(images, state["query"], system="You are the v-rag assistant.")
    return {"generation": text}
```
- [ ] **Step 3: 默认图扩展** —— classifier → memory_recall → 按 intent：multimodal_doc → colpali_retrieve → vlm_generate；knowledge_qa → retrieve（含 fallback）；complex_task → planner...
- [ ] **Step 4: 测试 + 集成**（multimodal_doc query → ColPali 检索 → VLM 生成；citation 含 page+bbox）+ Commit `feat(graph): multimodal_doc branch with ColPali + VLM`

---

## Task 10: 端到端验证

- [ ] **Step 1: e2e 清单**
  - 上传图文 PDF → DocumentProfiler → 双索引（文本 + 视觉）→ 列表
  - `knowledge_qa` 文本命中高置信 → 纯文本回答
  - `knowledge_qa` 低置信 + 含表格 → fallback ColPali → VLM
  - `multimodal_doc`（"这张表的数据"）→ ColPali 检索 → VLM 读图 → citation 含 page+bbox
  - 扫描件 PDF → OCR 插件 → 回灌 DocumentBlock → 文本索引
  - 表格三表示（markdown/html/json）在 chunk 元数据
  - 统一 source id：前端能并排展示同页文本命中 + 视觉命中（P4-B）
  - ColPali/VLM 不可用时降级（multimodal_doc → unsupported 或文本）
- [ ] **Step 2: 全量 pytest + ruff + mypy 全绿**
- [ ] **Step 3:** Commit `test(multimodal): e2e multimodal doc with ColPali + OCR + VLM`

---

## 验收标准（P4-A 完成 = 全部满足）

- [ ] DocumentProfiler 按质量路由（扫描→OCR、纯文本→PyMuPDF、复杂→Docling 占位）
- [ ] Canonical DocumentBlock 统一所有 parser/OCR/ColPali 输出
- [ ] 多粒度 chunking + 表格三表示（markdown/html/json）+ Citation（回溯全字段）
- [ ] 统一 source id（document/page/block 跨文本&视觉索引共享）
- [ ] ColPali 二阶段检索（page retrieve → region crop → VLM）
- [ ] OCR 插件协议（bbox/confidence/engine_version）+ 回灌 DocumentBlock + 分层注册
- [ ] VLM provider（OpenAI GPT-4V + Ollama Qwen2-VL）
- [ ] knowledge_qa 文本优先，低置信/复杂版式 fallback 视觉
- [ ] multimodal_doc 分支接入默认图（ColPali → VLM）
- [ ] `/documents` 支持 PDF + 双索引 + 任务状态
- [ ] pytest / ruff / mypy 全绿
- [ ] ColPali/OCR 不可用时的降级路径

## 不在 P4-A 范围（YAGNI / P4-B / 后续）

- **前端知识库管理增强**（解析任务队列视图 + Citation 回溯 + chunk 预览 + 双索引并排展示）= **P4-B**
- Docling / Unstructured 真实实装（P4-A 占位，按需）
- 公式识别（formula_density 检测但 P4-A 不实装解析）
- BM25 规模化（P3 已有内存版）
- 视觉索引规模化（Milvus 视觉 collection）

## Open Questions

1. **ColPali 依赖重量**：colpali-engine + torch + 模型权重（GB 级）。Docker 镜像会大。可选：ColPali 作为可选依赖（`pip install v-rag[multimodal]`），不可用时 multimodal_doc 降级文本/unsupported。
2. **PaddleOCR vs PaddleOCR-VL**：spec 提 PaddleOCR-VL-1.6。若该版本不可用，用 paddleocr（OCR-VL 可选增强）。
3. **VLM 成本**：商业 VLM（GPT-4V）按调用计费；本地 Qwen2-VL 需 GPU。provider 抽象已支持切换，默认按配置。
4. **异步任务**：P4-A 解析/索引同步返回（P0-B 现状）。大 PDF 同步会阻塞；真正异步（任务队列）在 P4-B 或后续。
5. **Docling/Unstructured 占位深度**：P4-A 路由能选它们但实装降级 pymupdf。真实实装按需（若文档复杂版式多）。

## 风险

1. **重依赖**：ColPali(torch) + PaddleOCR(paddlepaddle) 体积大、可能 GPU。Task 5/4 提供降级（不可用→文本/unsupported）。docker-compose 镜像需注意。
2. **ColPali 与 LangGraph 集成**：colpali_retrieve 节点调 ColPali 异步检索，需 services 注入。Task 9 测试用 mock ColPali。
3. **双索引一致性**：文本与视觉索引共享 source id，forget/reindex 需同步两索引。Task 8 测试验证。
4. **OCR 回灌**：OCRBlock → DocumentBlock 归一化需保留 bbox/confidence。Task 4 测试覆盖。
5. **PDF 解析稳定性**：PyMuPDF find_tables 在某些 PDF 不稳定。Task 2 容错（表格提取失败→降级纯文本 block）。
