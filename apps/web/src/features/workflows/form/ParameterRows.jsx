import { useMemo } from "react";

import { buildParameterRows } from "./buildParameterRows.js";
import DateRangeRow from "./DateRangeRow.jsx";
import ParameterInput from "./ParameterInput.jsx";
import { ParameterField, ParameterLabel } from "./ParameterField.jsx";
import ParameterPairRow from "./ParameterPairRow.jsx";

export default function ParameterRows({ workflow, parameters, labels, setParameter }) {
  const rows = useMemo(() => buildParameterRows(workflow), [workflow]);

  function renderInput(parameter) {
    return (
      <ParameterInput
        parameter={parameter}
        value={parameters[parameter.name]}
        label={labels[parameter.name]}
        subjectId={parameters.subject_id}
        onChange={(nextValue, nextLabel) => setParameter(parameter.name, nextValue, nextLabel)}
      />
    );
  }

  return rows.flatMap((row) => {
    if (row.type === "date-range") {
      return (
        <DateRangeRow
          key={row.key}
          since={row.since}
          until={row.until}
          limit={row.limit}
          renderInput={renderInput}
        />
      );
    }
    if (row.type === "pair") {
      return (
        <ParameterPairRow
          key={row.key}
          left={row.left}
          right={row.right}
          leftLabel={row.leftLabel}
          rightLabel={row.rightLabel}
          renderInput={renderInput}
        />
      );
    }
    if (row.type === "full-width") {
      if (row.variant === "event-type") {
        return (
          <div className="field" style={{ gridColumn: "1 / -1" }} key={row.key}>
            {renderInput(row.parameter)}
          </div>
        );
      }
      return (
        <ParameterField parameter={row.parameter} className="field" key={row.key} style={{ gridColumn: "1 / -1" }}>
          {renderInput(row.parameter)}
        </ParameterField>
      );
    }
    return [
      <ParameterLabel parameter={row.parameter} key={`${row.key}-label`} />,
      <ParameterField parameter={row.parameter} key={row.key}>
        {renderInput(row.parameter)}
      </ParameterField>
    ];
  });
}
