export function syncWorkflowToUrl(workflowId) {
  const url = new URL(window.location.href);
  url.pathname = "/workflows";
  if (workflowId) {
    url.searchParams.set("workflow", workflowId);
  } else {
    url.searchParams.delete("workflow");
  }
  window.history.replaceState({}, "", url);
}

export function workflowFromUrl() {
  return new URL(window.location.href).searchParams.get("workflow");
}
