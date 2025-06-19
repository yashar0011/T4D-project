import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export default function Dashboard() {
  const [point, setPoint] = useState("KB-UMP-010");
  const { data } = useQuery([
    "deltas",
    point,
  ], () => api.get(`/deltas?point=${point}&hours=24`).then(r => r.data), {
    refetchInterval: 10000, // 10 s
  });

  return (
    <div className="grid gap-4">
      <select
        className="border p-2 rounded w-64"
        value={point}
        onChange={e => setPoint(e.target.value)}
      >
        <option>KB-UMP-010</option>
        <option>MP-GMP-B006</option>
        {/* TODO: load list from /settings */}
      </select>

      {data && (
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={data.rows} margin={{ top: 20, right: 30 }}>
            <XAxis dataKey="TIMESTAMP" tickFormatter={t => new Date(t).toLocaleTimeString()} />
            <YAxis domain={["dataMin", "dataMax"]} />
            <Tooltip labelFormatter={l => new Date(l).toLocaleString()} />
            <Line type="monotone" dataKey="Delta_H_mm" stroke="var(--fallback-color, black)" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}