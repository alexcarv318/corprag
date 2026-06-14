import { TYPEAHEAD_SUFFIX_MAP } from "../shared/typeaheadConfig.js";

export function typeaheadKind(parameter) {
  const name = parameter.name || "";
  for (const [suffix, kind] of TYPEAHEAD_SUFFIX_MAP) {
    if (name === suffix || name.endsWith("_" + suffix)) return kind;
  }
  return null;
}

export function friendlyDefaultHint(parameter) {
  if (parameter.required) return "";
  const def = parameter.default;
  if (def === null || def === undefined || def === "") return "";
  if (parameter.kind === "number") return `Default: ${def}`;
  if (parameter.kind === "select") return `Default: ${def === "all" ? "All" : def}`;
  if (parameter.kind === "date" && String(def).toLowerCase() === "today") return "Default: today";
  return "";
}

export function pairedFieldLabel(parameter) {
  if (
    parameter.name === "participant_id"
    || parameter.name === "organization_id"
    || parameter.name === "involves_organization_id"
  ) {
    return "Organization";
  }
  return parameter.label;
}

export function workflowPairingFlags(workflow) {
  const parameters = workflow.parameters || [];
  const names = new Set(parameters.map((parameter) => parameter.name));
  const stackAllParameters = workflow.workflow_id === "governance.poa.register";
  return {
    stackAllParameters,
    pairSubjectParticipant: names.has("subject_id") && names.has("participant_id"),
    pairSubjectOrganization:
      !stackAllParameters
      && names.has("subject_id")
      && (names.has("organization_id") || names.has("involves_organization_id")),
    pairFileKeyword: names.has("file") && names.has("q"),
    organizationParameterName: names.has("participant_id")
      ? "participant_id"
      : names.has("organization_id")
        ? "organization_id"
        : names.has("involves_organization_id")
          ? "involves_organization_id"
          : null,
  };
}

export function isPairedOrganizationParameter(name) {
  return name === "participant_id" || name === "organization_id" || name === "involves_organization_id";
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
