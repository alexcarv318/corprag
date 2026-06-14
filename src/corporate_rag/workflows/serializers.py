from typing import Any

from corporate_rag.workflows.models import Workflow, WorkflowResult


def workflow_public_payload(workflow: Workflow) -> dict[str, Any]:
    return {
        "workflow_id": workflow.workflow_id,
        "title": workflow.title,
        "category": workflow.category,
        "description": workflow.description,
        "cypher": workflow.cypher,
        "parameters": [parameter.to_dict() for parameter in workflow.parameters],
        "output_columns": list(workflow.output_columns),
        "notes": workflow.notes,
        "use_cases": list(workflow.use_cases),
        "dev_only": workflow.dev_only,
    }


def workflow_result_public_payload(result: WorkflowResult) -> dict[str, Any]:
    return result.to_dict()
