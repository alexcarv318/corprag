import { X } from "lucide-react";

import Button from "./Button.jsx";

export default function Modal({ title, children, onClose }) {
  if (!children) {
    return null;
  }

  return (
    <aside className="drawer" aria-label={title}>
      <div className="drawer-header">
        <h2>{title}</h2>
        <Button aria-label="Close" variant="ghost" onClick={onClose}>
          <X size={18} />
        </Button>
      </div>
      <div className="drawer-body">{children}</div>
    </aside>
  );
}
