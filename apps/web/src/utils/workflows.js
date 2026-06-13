const PARAMETER_TYPEAHEAD_KIND = {
  file: "file",
  organization_id: "organization",
  involves_organization_id: "organization",
  participant_id: "organization",
  person_id: "person",
  involves_person_id: "person",
  signatory_person_id: "person",
  subject_id: "subject"
};

function initialValue(parameter) {
  if (parameter.default !== undefined && parameter.default !== null) {
    return parameter.default;
  }
  if (parameter.multiple) {
    return [];
  }
  if (parameter.kind === "boolean") {
    return false;
  }
  return "";
}

export function initialParameters(workflow) {
  return Object.fromEntries((workflow?.parameters || []).map((parameter) => [parameter.name, initialValue(parameter)]));
}

export function typeaheadKindForParameter(parameter) {
  return PARAMETER_TYPEAHEAD_KIND[parameter.name] || null;
}
