import { ParameterPairField } from "./ParameterField.jsx";

export default function ParameterPairRow({ left, right, leftLabel, rightLabel, renderInput }) {
  return (
    <div className="param-pair-row">
      <ParameterPairField parameter={left} label={leftLabel}>
        {renderInput(left)}
      </ParameterPairField>
      <ParameterPairField parameter={right} label={rightLabel}>
        {renderInput(right)}
      </ParameterPairField>
    </div>
  );
}
