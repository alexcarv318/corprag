export default function Tabs({ tabs, active, onChange }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((tab) => (
        <button
          aria-selected={tab === active}
          className={tab === active ? "active" : ""}
          key={tab}
          onClick={() => onChange(tab)}
          role="tab"
          type="button"
        >
          {tab}
        </button>
      ))}
    </div>
  );
}
