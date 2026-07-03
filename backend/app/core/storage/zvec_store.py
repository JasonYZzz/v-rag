"""Zvec vector store adapter."""

from contextlib import suppress
from pathlib import Path

import zvec

from app.core.storage.base import VectorHit

_VECTOR_FIELD = "embedding"
_OUTPUT_FIELDS = ["doc", "page"]
_zvec_initialized = False


class ZvecVectorStore:
    """Zvec-backed vector store.

    P0 keeps the schema narrow: vectors plus the filterable scalar fields used
    by the API tests (`doc` and `page`). PostgreSQL remains the source of truth
    for chunk text and rich metadata.
    """

    def __init__(self, path: str, dim: int) -> None:
        self.path = path
        self.dim = dim
        _init_zvec_once()
        collection_path = Path(path)
        collection_path.parent.mkdir(parents=True, exist_ok=True)
        if collection_path.exists():
            self._collection = zvec.open(str(collection_path))
        else:
            schema = zvec.CollectionSchema(
                name="chunks",
                fields=[
                    zvec.FieldSchema("doc", zvec.DataType.STRING, nullable=True),
                    zvec.FieldSchema("page", zvec.DataType.STRING, nullable=True),
                ],
                vectors=zvec.VectorSchema(
                    _VECTOR_FIELD,
                    data_type=zvec.DataType.VECTOR_FP32,
                    dimension=dim,
                    index_param=zvec.FlatIndexParam(),
                ),
            )
            self._collection = zvec.create_and_open(str(collection_path), schema)

    async def add(
        self,
        ids: list[str],
        vectors: list[list[float]],
        metadata: list[dict[str, object]],
    ) -> None:
        """Upsert vectors into Zvec."""

        docs = [
            zvec.Doc(
                id=id_,
                vectors={_VECTOR_FIELD: vector},
                fields=_zvec_fields(meta),
            )
            for id_, vector, meta in zip(ids, vectors, metadata, strict=True)
        ]
        if docs:
            self._collection.upsert(docs)
            self._collection.flush()

    async def search(
        self,
        query: list[float],
        top_k: int,
        filter: dict[str, object] | None = None,
    ) -> list[VectorHit]:
        """Search vectors in Zvec."""

        docs = self._collection.query(
            queries=zvec.Query(field_name=_VECTOR_FIELD, vector=query),
            topk=top_k,
            filter=_filter_expression(filter),
            include_vector=False,
            output_fields=_OUTPUT_FIELDS,
        )
        return [
            VectorHit(
                id=doc.id,
                score=float(doc.score if doc.score is not None else 0.0),
                metadata=dict(doc.fields),
            )
            for doc in docs
        ]

    async def delete(self, ids: list[str]) -> None:
        """Delete vectors from Zvec."""

        if ids:
            self._collection.delete(ids)
            self._collection.flush()


def _init_zvec_once() -> None:
    global _zvec_initialized
    if _zvec_initialized:
        return
    with suppress(RuntimeError):
        zvec.init(log_level=zvec.LogLevel.ERROR)
    _zvec_initialized = True


def _zvec_fields(metadata: dict[str, object]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for key in _OUTPUT_FIELDS:
        value = metadata.get(key)
        if value is not None:
            fields[key] = str(value)
    return fields


def _filter_expression(filter: dict[str, object] | None) -> str | None:
    if not filter:
        return None
    clauses = []
    for key, value in filter.items():
        if key not in _OUTPUT_FIELDS:
            continue
        clauses.append(f"{key} = {_quote(str(value))}")
    return " AND ".join(clauses) if clauses else None


def _quote(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"
