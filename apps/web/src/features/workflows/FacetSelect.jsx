import { useEffect, useState } from "react";

import { getFacet } from "../../api/workflows.js";

export default function FacetSelect({ parameter, workflowId, parameters, value, onChange }) {
  const [facetValues, setFacetValues] = useState([]);

  useEffect(() => {
    let mounted = true;
    getFacet({ workflowId, parameterName: parameter.name, parameters })
      .then((payload) => {
        if (mounted) {
          setFacetValues(payload.values || []);
        }
      })
      .catch(() => {
        if (mounted) {
          setFacetValues([]);
        }
      });

    return () => {
      mounted = false;
    };
  }, [parameter.name, parameters, workflowId]);

  const options = facetValues.length
    ? facetValues.map((item) => ({
        label: item.value ? `${item.value} (${item.count})` : `Blank (${item.count})`,
        value: item.value
      }))
    : (parameter.options || []).map((option) => ({ label: option, value: option }));

  return (
    <select
      id={parameter.name}
      multiple={parameter.multiple}
      onChange={(event) => {
        if (parameter.multiple) {
          onChange(Array.from(event.target.selectedOptions).map((option) => option.value));
          return;
        }
        onChange(event.target.value);
      }}
      value={value || (parameter.multiple ? [] : "")}
    >
      {!parameter.multiple ? <option value="">Any</option> : null}
      {options.map((option) => (
        <option key={option.value || "blank"} value={option.value || ""}>
          {option.label}
        </option>
      ))}
    </select>
  );
}
