import { apiFetch, toQueryString } from "./client.js";

export function getCatalog() {
  return apiFetch("/api/workflows/catalog");
}

export function getDisclaimer() {
  return apiFetch("/api/workflows/disclaimer");
}

export function getWorkflow(workflowId) {
  return apiFetch(`/api/workflows/${encodeURIComponent(workflowId)}`);
}

export function runWorkflow(workflowId, parameters) {
  return apiFetch(`/api/workflows/${encodeURIComponent(workflowId)}/run`, {
    method: "POST",
    body: JSON.stringify({ parameters })
  });
}

export function getTypeahead({ kind, q, limit = 12, subjectId }) {
  return apiFetch(
    `/api/workflows/typeahead${toQueryString({
      kind,
      q,
      limit,
      subject_id: subjectId
    })}`
  );
}

export function getFacet({ workflowId, parameterName, parameters = {} }) {
  return apiFetch(
    `/api/workflows/facet${toQueryString({
      workflow_id: workflowId,
      parameter_name: parameterName,
      ...parameters
    })}`
  );
}

export function getEvidence(payload) {
  return apiFetch("/api/workflows/evidence", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}
