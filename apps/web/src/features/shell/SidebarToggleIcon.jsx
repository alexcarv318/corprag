export default function SidebarToggleIcon({ collapsed }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="3" y="4" width="18" height="16" rx="4" stroke="currentColor" strokeWidth="1.6" />
      <path d="M8.5 4.5v15" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d={collapsed ? "m13 9 3 3-3 3" : "m16 9-3 3 3 3"} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
