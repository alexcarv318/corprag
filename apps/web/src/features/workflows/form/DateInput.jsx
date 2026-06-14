function ClearIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
      <path d="M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export default function DateInput({ parameter, value, onChange }) {
  const label = parameter.label || parameter.name;
  return (
    <span className="date-input-wrap">
      <input
        type="date"
        name={parameter.name}
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value)}
      />
      <button
        type="button"
        className="date-clear-btn"
        title={`Clear ${label}`}
        aria-label={`Clear ${label}`}
        onClick={() => onChange("")}
      >
        <ClearIcon />
      </button>
    </span>
  );
}
