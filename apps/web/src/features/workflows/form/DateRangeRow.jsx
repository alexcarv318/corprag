export default function DateRangeRow({ since, until, limit, renderInput }) {
  return (
    <div className="date-range-row">
      <div className="date-range-main">
        <div className="date-range-label">Date range</div>
        <div className="date-range-controls">
          <label className="date-inline-field">
            <span>From</span>
            {renderInput(since)}
          </label>
          <label className="date-inline-field">
            <span>To</span>
            {renderInput(until)}
          </label>
        </div>
      </div>
      {limit ? (
        <label className="inline-limit-field">
          <span>{limit.label}</span>
          {renderInput(limit)}
        </label>
      ) : null}
    </div>
  );
}
