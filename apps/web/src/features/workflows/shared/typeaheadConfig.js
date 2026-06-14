export const TYPEAHEAD_SUFFIX_MAP = [
  ["subject_id", "subject"],
  ["person_id", "person"],
  ["phase_id", "phase"],
  ["event_id", "event"],
  ["work_id", "work"],
  ["file", "file"],
  ["organization_id", "organization"],
  ["participant_id", "organization"],
  ["class_id", "class"],
  ["from_class_id", "class"],
  ["to_class_id", "class"],
  ["module", "module"]
];

export const TYPEAHEAD_LIMITS = {
  subject: 12,
  person: 12,
  organization: 12,
  file: 12,
  event: 10,
  phase: 10,
  work: 10,
  class: 12,
  module: 12
};
