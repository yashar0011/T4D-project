import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

// easily add more points later
const POINTS = ["KB-UMP-010", "MP-GMP-B006"];

export default function Dashboard() {
  const [point, setPoint] = useState(POINTS[0]);

  /* -------------- main query (v5 object form) -------------- */
  const { data, isLoading, error } = useQuery({
    queryKey: ["deltas", point],
    queryFn: () =>
      api.get(`/deltas`, { params: { point, hours: 24 } }).then((r) => r.data),
    refetchInterval: 10_000, // 10 s live refresh
  });

  /* --------------------- ui --------------------- */
  if (isLoading) return <p className="p-4">Loading…</p>;
  if (error) return <p className="p-4 text-red-600">Error – {(error as Error).message}</p>;

  return (
    <div className="grid gap-4">
      {/* point selector */}
      <select
        className="border p-2 rounded w-64"
        value={point}
        onChange={(e) => setPoint(e.target.value)}
      >
        {POINTS.map((p) => (
          <option key={p}>{p}</option>
        ))}
      </select>

      {/* line chart */}
      {data?.rows?.length ? (
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={data.rows} margin={{ top: 20, right: 30 }}>
            <XAxis
              dataKey="TIMESTAMP"
              tickFormatter={(t) => new Date(t).toLocaleTimeString()}
            />
            <YAxis domain={["dataMin", "dataMax"]} />
            <Tooltip labelFormatter={(l) => new Date(l).toLocaleString()} />
            <Line
              type="monotone"
              dataKey="Delta_H_mm"
              stroke="currentColor"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <p>No data for last 24 h.</p>
      )}
    </div>
  );
}
