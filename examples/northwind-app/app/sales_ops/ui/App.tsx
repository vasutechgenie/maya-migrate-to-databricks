// Legacy Sales Ops Console UI (reference source). MAYA rebuilds these screens as a
// Databricks App served UI and parity-checks each render against the golden screenshots.
import { useEffect, useState } from "react";

function Grid({ url }: { url: string }) {
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => {
    fetch(url)
      .then((r) => r.json())
      .then((d) => setRows(d.data || []));
  }, [url]);
  if (!rows.length) return <p>No rows.</p>;
  const cols = Object.keys(rows[0]);
  return (
    <table>
      <thead>
        <tr>{cols.map((c) => <th key={c}>{c}</th>)}</tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>{cols.map((c) => <td key={c}>{String(r[c])}</td>)}</tr>
        ))}
      </tbody>
    </table>
  );
}

export default function App() {
  return (
    <div>
      <h1>Sales Ops Console</h1>
      <section><h2>Orders Queue</h2><Grid url="/api/orders" /></section>
      <section><h2>Customer 360 Lookup</h2><Grid url="/api/customers" /></section>
      <section><h2>Reorder Alerts</h2><Grid url="/api/reorder-alerts" /></section>
    </div>
  );
}
