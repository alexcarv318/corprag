import { friendlyDefaultHint } from "./parameterUtils.js";

export function ParameterLabel({ parameter, label }) {
  return (
    <div className="param-label">
      <div>
        {label ?? parameter.label}
        {parameter.required ? <span className="req-mark">*</span> : null}
      </div>
    </div>
  );
}

export function ParameterField({ parameter, className, style, children }) {
  const hint = friendlyDefaultHint(parameter);
  return (
    <div className={className || "field"} style={style}>
      {children}
      {parameter.description ? <div className="desc">{parameter.description}</div> : null}
      {hint ? <div className="default-hint">{hint}</div> : null}
    </div>
  );
}

export function ParameterPairField({ parameter, label, children }) {
  return (
    <div className="param-pair-field">
      <ParameterLabel parameter={parameter} label={label} />
      <ParameterField parameter={parameter}>{children}</ParameterField>
    </div>
  );
}
