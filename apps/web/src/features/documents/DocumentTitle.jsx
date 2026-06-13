export default function DocumentTitle({ title, file }) {
  return <span title={file}>{title || file}</span>;
}
