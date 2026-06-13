import { Database } from "lucide-react";

import { compactNumber } from "../../utils/format.js";

export default function Disclaimer({ documentCount, loading }) {
  return (
    <div className="disclaimer">
      <Database size={16} />
      <span>{loading ? "Counting source documents..." : `${compactNumber(documentCount)} documents indexed`}</span>
    </div>
  );
}
