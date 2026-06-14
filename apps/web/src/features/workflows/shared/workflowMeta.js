export function workflowIconKey(workflow) {
  const text = `${workflow.workflow_id || ""} ${workflow.title || ""} ${workflow.category || ""}`.toLowerCase();
  if (text.includes("organization")) return "organization";
  if (text.includes("person")) return "person";
  if (text.includes("document")) return "document";
  if (text.includes("capital") || text.includes("share")) return "capital";
  if (text.includes("attorney") || text.includes("poa")) return "poa";
  if (text.includes("event") || text.includes("timeline")) return "event";
  if (text.includes("data_model") || text.includes("data model")) return "data";
  return "subject";
}
