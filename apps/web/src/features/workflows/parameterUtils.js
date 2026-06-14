import { TYPEAHEAD_SUFFIX_MAP } from "./workflowConstants.js";

export function typeaheadKind(parameter) {
  const name = parameter.name || "";
  for (const [suffix, kind] of TYPEAHEAD_SUFFIX_MAP) {
    if (name === suffix || name.endsWith("_" + suffix)) return kind;
  }
  return null;
}

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

export function defaultParameterValue(parameter, showCancelled) {
  if (parameter.name === "include_cancelled") return showCancelled || Boolean(parameter.default);
  if (parameter.default !== undefined && parameter.default !== null) return parameter.default;
  if (parameter.multiple) return [];
  if (parameter.kind === "boolean") return false;
  return "";
}

export function initialParameters(workflow, showCancelled) {
  return Object.fromEntries((workflow.parameters || []).map((parameter) => [parameter.name, defaultParameterValue(parameter, showCancelled)]));
}

export function collectRunParameters(parameters, workflow) {
  const payload = {};
  for (const parameter of workflow.parameters || []) {
    const value = parameters[parameter.name];
    if (Array.isArray(value)) {
      if (value.length) payload[parameter.name] = value;
      continue;
    }
    if (parameter.kind === "boolean") {
      payload[parameter.name] = Boolean(value);
      continue;
    }
    if (value !== null && value !== undefined && value !== "") payload[parameter.name] = value;
  }
  return payload;
}
