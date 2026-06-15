from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Path

from corporate_rag.app.dependencies import current_user, workflow_engine
from corporate_rag.auth.models import AuthUser
from corporate_rag.logger import log_user_ran_workflow
from corporate_rag.workflows.engine import WorkflowEngine
from corporate_rag.workflows.models import (
    Workflow,
    WorkflowCatalogResponse,
    WorkflowDisclaimerResponse,
    WorkflowResponse,
    WorkflowResultResponse,
    WorkflowRunRequest,
)
from corporate_rag.workflows.repository import document_count
from corporate_rag.workflows.serializers import (
    workflow_public_payload,
    workflow_result_public_payload,
)

WORKFLOW_ID_DESCRIPTION = "Workflow id from the catalog, for example `find.subject`."

WORKFLOW_RUN_OPENAPI_EXAMPLES: dict[str, Any] = {
    "find_subject": {
        "summary": "Find Acer European Holdings",
        "value": {
            "parameters": {
                "subject_id": "b096e064-e1cb-4ab8-b5bc-0c0e3729c696",
            }
        },
    },
    "documents_search": {
        "summary": "Search documents",
        "description": "A low-risk example because this workflow has no required parameters.",
        "value": {
            "parameters": {
                "doc_type": [],
                "signatory_person_id": "",
                "subject_id": "",
                "file": "",
                "text_query": "capital",
                "limit": 25,
            }
        },
    },
}

router = APIRouter(
    prefix="/workflows",
    tags=["workflows"],
    responses={503: {"description": "Workflow engine is not configured."}},
)


@router.get(
    "/catalog",
    response_model=WorkflowCatalogResponse,
    summary="List available workflows",
    description=(
        "Returns the clean public workflow catalog used by the React workflow "
        "console and generated MCP workflow tools. Internal Cypher templates are "
        "never exposed."
    ),
)
async def catalog(
    engine: Annotated[WorkflowEngine, Depends(workflow_engine)],
) -> dict[str, Any]:
    workflows = engine.list_workflows()
    return {
        "categories": workflow_categories(workflows),
        "workflows": [workflow_public_payload(workflow) for workflow in workflows],
    }


@router.get(
    "/disclaimer",
    response_model=WorkflowDisclaimerResponse,
    summary="Return workflow console disclaimer data",
    description="Returns lightweight graph metadata displayed by the workflow UI.",
)
async def disclaimer(
    engine: Annotated[WorkflowEngine, Depends(workflow_engine)],
) -> dict[str, int]:
    return {"document_count": document_count(engine.client)}


@router.get(
    "/{workflow_id:path}",
    response_model=WorkflowResponse,
    summary="Get workflow definition",
    description=(
        "Returns one workflow definition with parameters, output columns, notes, "
        "and use cases. Internal query text is intentionally omitted."
    ),
)
async def workflow_definition(
    engine: Annotated[WorkflowEngine, Depends(workflow_engine)],
    workflow_id: Annotated[
        str,
        Path(description=WORKFLOW_ID_DESCRIPTION, examples=["find.subject"]),
    ],
) -> dict[str, Any]:
    try:
        workflow = engine.get_workflow(workflow_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"unknown workflow {workflow_id!r}",
        ) from exc

    return workflow_public_payload(workflow)


@router.post(
    "/{workflow_id:path}/run",
    response_model=WorkflowResultResponse,
    summary="Run a workflow",
    description=(
        "Executes a parameterized workflow against the corporate graph and returns "
        "the public result tables expected by the workflow UI."
    ),
)
async def run_workflow(
    engine: Annotated[WorkflowEngine, Depends(workflow_engine)],
    user: Annotated[AuthUser, Depends(current_user)],
    workflow_id: Annotated[
        str,
        Path(description=WORKFLOW_ID_DESCRIPTION, examples=["find.subject"]),
    ],
    payload: Annotated[
        WorkflowRunRequest,
        Body(openapi_examples=WORKFLOW_RUN_OPENAPI_EXAMPLES),
    ],
) -> dict[str, Any]:
    try:
        result = engine.run(workflow_id, payload.parameters)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"unknown workflow {workflow_id!r}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    log_user_ran_workflow(user, workflow_id, payload.parameters)
    return workflow_result_public_payload(result)


def workflow_categories(workflows: list[Workflow]) -> list[str]:
    categories: list[str] = []
    for workflow in workflows:
        category = str(workflow.category)
        if category not in categories:
            categories.append(category)
    return categories
