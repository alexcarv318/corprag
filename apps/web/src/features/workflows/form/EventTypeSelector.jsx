import { useMemo, useState } from "react";

import { displayOptionValue } from "../shared/displayUtils.js";
import { EVENT_TYPE_GROUPS } from "../shared/eventTypeGroups.js";

function SelectIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M9 22H15C20 22 22 20 22 15V9C22 4 20 2 15 2H9C4 2 2 4 2 9V15C2 20 4 22 9 22Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M7.75 12L10.58 14.83L16.25 9.17004" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function DeselectIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
      <path d="M9.16998 14.83L14.83 9.17004" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M14.83 14.83L9.16998 9.17004" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <path
        d="M9 22H15C20 22 22 20 22 15V9C22 4 20 2 15 2H9C4 2 2 4 2 9V15C2 20 4 22 9 22Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function isSentinel(option) {
  return option === "" || option === "all";
}

function selectedValues(value) {
  return Array.isArray(value) ? value.map(String) : value ? [String(value)] : [];
}

function GroupActions({ hasValues, onSelect, onDeselect, selectLabel, deselectLabel }) {
  return (
    <div className="event-type-actions">
      <button
        type="button"
        className={`event-type-select-action${hasValues ? " select-has-values" : ""}`}
        title={selectLabel}
        aria-label={selectLabel}
        onClick={onSelect}
      >
        <SelectIcon />
      </button>
      <button type="button" title={deselectLabel} aria-label={deselectLabel} onClick={onDeselect}>
        <DeselectIcon />
      </button>
    </div>
  );
}

export default function EventTypeSelector({ parameter, value, onChange }) {
  const selected = useMemo(() => new Set(selectedValues(value)), [value]);
  const concreteOptions = useMemo(
    () => new Set((parameter.options || []).map(String).filter((option) => !isSentinel(option))),
    [parameter.options]
  );
  const allOptions = useMemo(() => Array.from(concreteOptions), [concreteOptions]);

  const groups = useMemo(() => {
    const grouped = new Set();
    const result = [];
    for (const [domainLabel, eventTypes] of EVENT_TYPE_GROUPS) {
      const available = eventTypes.filter((eventType) => concreteOptions.has(eventType));
      if (!available.length) continue;
      for (const eventType of available) grouped.add(eventType);
      result.push({ domainLabel, eventTypes: available });
    }
    const ungrouped = allOptions.filter((eventType) => !grouped.has(eventType));
    if (ungrouped.length) result.push({ domainLabel: "Other", eventTypes: ungrouped, ungrouped: true });
    return result;
  }, [allOptions, concreteOptions]);

  const [expanded, setExpanded] = useState({});

  function emitSelection(next) {
    onChange(Array.from(next));
  }

  function setBoxes(eventTypes, checked) {
    const next = new Set(selected);
    for (const eventType of eventTypes) {
      if (checked) next.add(eventType);
      else next.delete(eventType);
    }
    emitSelection(next);
  }

  function toggleOption(eventType, checked) {
    const next = new Set(selected);
    if (checked) next.add(eventType);
    else next.delete(eventType);
    emitSelection(next);
  }

  const count = selected.size;
  const summary = count ? `${count} selected` : "No boxes selected = Any";

  return (
    <div className="event-type-panel" data-enum-multi="1" data-name={parameter.name}>
      <div className="event-type-toolbar">
        <div className="event-type-title-wrap">
          <div className="event-type-title">{parameter.label || "Event type"}</div>
          {parameter.description ? <div className="event-type-description">{parameter.description}</div> : null}
        </div>
        <div className="event-type-toolbar-right">
          <span className="event-type-summary">{summary}</span>
          <GroupActions
            hasValues={allOptions.some((eventType) => selected.has(eventType))}
            selectLabel="Select all event types"
            deselectLabel="Deselect all event types"
            onSelect={() => setBoxes(allOptions, true)}
            onDeselect={() => setBoxes(allOptions, false)}
          />
        </div>
      </div>

      <div className="event-type-groups">
        {groups.map(({ domainLabel, eventTypes, ungrouped }) => {
          const isExpanded = Boolean(expanded[domainLabel]);
          const hasValues = eventTypes.some((eventType) => selected.has(eventType));
          return (
            <div className={`event-type-group${isExpanded ? " expanded" : ""}`} key={domainLabel}>
              <div className="event-type-group-head">
                <button
                  type="button"
                  className="event-type-group-title"
                  aria-expanded={isExpanded}
                  onClick={() => setExpanded((current) => ({ ...current, [domainLabel]: !current[domainLabel] }))}
                >
                  {domainLabel}
                </button>
                {ungrouped ? null : (
                  <GroupActions
                    hasValues={hasValues}
                    selectLabel={`Select ${domainLabel}`}
                    deselectLabel={`Deselect ${domainLabel}`}
                    onSelect={() => setBoxes(eventTypes, true)}
                    onDeselect={() => setBoxes(eventTypes, false)}
                  />
                )}
              </div>
              <div className="event-type-grid" hidden={!isExpanded}>
                {eventTypes.map((eventType) => (
                  <label className="event-type-option" key={eventType}>
                    <input
                      type="checkbox"
                      value={eventType}
                      checked={selected.has(eventType)}
                      onChange={(event) => toggleOption(eventType, event.target.checked)}
                    />
                    <span>{displayOptionValue(eventType)}</span>
                  </label>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
