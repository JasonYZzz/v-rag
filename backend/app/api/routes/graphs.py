"""Graph configuration API."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.db.session import get_session_factory
from app.core.graph.config import GraphConfig
from app.core.graph.nodes import register_all
from app.core.graph.persistence import (
    create_graph,
    delete_graph,
    get_version,
    list_graphs,
    list_versions,
    publish_version,
    rollback_to,
    save_draft_version,
)
from app.core.graph.registry import registry
from app.core.graph.runner import run
from app.core.graph.state import VragState
from app.deps import get_services

router = APIRouter(prefix="/graphs", tags=["graphs"])


class GraphCreateRequest(BaseModel):
    """Create graph request."""

    name: str
    graph: GraphConfig
    workspace_id: str = "default"


class GraphDraftRequest(BaseModel):
    """Save draft request."""

    graph: GraphConfig


class GraphVersionRequest(BaseModel):
    """Version operation request."""

    version: int


class GraphTestRunRequest(BaseModel):
    """Test-run request."""

    version: int
    query: str


@router.post("")
async def create_graph_endpoint(request: GraphCreateRequest) -> dict[str, Any]:
    """Create a graph config with initial draft."""

    async with get_session_factory()() as session:
        config, version = await create_graph(
            session, request.name, request.graph, request.workspace_id
        )
        return {"id": config.id, "name": config.name, "version": version.version}


@router.get("")
async def list_graphs_endpoint() -> list[dict[str, Any]]:
    """List graph configs."""

    async with get_session_factory()() as session:
        graphs = await list_graphs(session)
        return [
            {
                "id": graph.id,
                "name": graph.name,
                "workspace_id": graph.workspace_id,
                "current_published_version": graph.current_published_version,
            }
            for graph in graphs
        ]


@router.get("/registry")
async def get_graph_registry() -> list[dict[str, Any]]:
    """Return backend whitelisted node definitions."""

    register_all()
    return [
        {
            "type": defn.type,
            "description": defn.description,
            "config_schema": (
                defn.config_schema.model_json_schema() if defn.config_schema is not None else None
            ),
        }
        for defn in (registry.get(type_) for type_ in registry.list())
    ]


@router.get("/{config_id}")
async def get_graph_endpoint(config_id: str) -> dict[str, Any]:
    """Return graph detail and versions."""

    async with get_session_factory()() as session:
        versions = await list_versions(session, config_id)
        if not versions:
            raise HTTPException(status_code=404, detail="graph not found")
        return {
            "id": config_id,
            "versions": [
                {"version": version.version, "status": version.status, "graph": version.graph}
                for version in versions
            ],
        }


@router.put("/{config_id}/draft")
async def save_draft_endpoint(config_id: str, request: GraphDraftRequest) -> dict[str, Any]:
    """Save a new draft version."""

    async with get_session_factory()() as session:
        version = await save_draft_version(session, config_id, request.graph)
        return {"id": version.config_id, "version": version.version, "status": version.status}


@router.post("/{config_id}/test-run")
async def test_run_endpoint(
    config_id: str,
    request: GraphTestRunRequest,
    services: Annotated[object, Depends(get_services)],
) -> dict[str, Any]:
    """Run a graph version without persisting RunTrace."""

    async with get_session_factory()() as session:
        version = await get_version(session, config_id, request.version)
    state = await run(
        GraphConfig.model_validate(version.graph),
        VragState(
            query=request.query,
            graph_config_id=config_id,
            graph_version=version.version,
            messages=[],
        ),
        services,
    )
    return {"state": state}


@router.post("/{config_id}/publish")
async def publish_endpoint(config_id: str, request: GraphVersionRequest) -> dict[str, Any]:
    """Publish a graph version."""

    async with get_session_factory()() as session:
        version = await publish_version(session, config_id, request.version)
        return {"id": version.config_id, "version": version.version, "status": version.status}


@router.post("/{config_id}/rollback")
async def rollback_endpoint(config_id: str, request: GraphVersionRequest) -> dict[str, Any]:
    """Rollback to a historical graph version."""

    async with get_session_factory()() as session:
        version = await rollback_to(session, config_id, request.version)
        return {"id": version.config_id, "version": version.version, "status": version.status}


@router.delete("/{config_id}")
async def delete_graph_endpoint(config_id: str) -> dict[str, str]:
    """Delete a graph config."""

    async with get_session_factory()() as session:
        await delete_graph(session, config_id)
    return {"deleted": config_id}
