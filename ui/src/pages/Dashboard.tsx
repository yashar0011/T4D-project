import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Play } from "lucide-react";
import {
  Card,
  CardHeader,
  CardContent,
} from "@/components/ui/card"; // shadcn UI
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { api } from "../api";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

type Row = {
  TIMESTAMP: string;
  Delta_H_mm: number;
  Delta_N_mm?: number;
  Delta_E_mm?: number;
};

export default function Dashboard() {
  // —————————————————————————————————————————–
  // local state
  // —————————————————————————————————————————–
  const [point, setPoint] = useState<string | null>(null);
  const [hours, setHours] = useState(24);

  // Fetch available points ➟ select-box
  const { data: settings } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.get("/settings").then((r) => r.data as any[]),
  });

  // Fetch deltas (auto-refresh 10 s)
  const { data } = useQuery<Row[]>({
    queryKey: ["deltas", point, hours],
    queryFn: () =>
      point
        ? api
            .get("/deltas", { params: { point, hours } })
            .then((r) => r.data.rows as Row[])
        : [],
    enabled: !!point,
    refetchInterval: 10_000,
  });

  // Optional “trigger slice” button
  const trigger = useMutation({
    mutationFn: () =>
      api.post("/command", { run_once: true }).then((r) => r.data),
  });

  // —————————————————————————————————————————–
  // UI
  // —————————————————————————————————————————–
  return (
    <div className="mx-auto max-w-6xl space-y-6 py-6">
      <h2 className="text-3xl font-semibold">T4D Dashboard</h2>

      <Card>
        <CardHeader className="space-y-2">
          <p className="text-sm text-muted-foreground">
            Last {hours} h – live refresh every 10 s
          </p>

          {/* controls */}
          <div className="flex flex-wrap items-end gap-4">
            {/* point selector */}
            <div className="grid gap-1">
              <Label htmlFor="point">Measurement point</Label>
              <select
                id="point"
                className="border rounded-md px-2 py-1 bg-background"
                value={point ?? ""}
                onChange={(e) => setPoint(e.target.value || null)}
              >
                <option value="">Pick a point…</option>
                {settings?.map((s) => (
                  <option key={s.id} value={s.PointName}>
                    {s.PointName}
                  </option>
                ))}
              </select>
            </div>

            {/* hours back */}
            <div className="grid gap-1 w-24">
              <Label htmlFor="hrs">Hours back</Label>
              <Input
                id="hrs"
                type="number"
                min={1}
                max={168}
                value={hours}
                onChange={(e) => setHours(Number(e.target.value))}
              />
            </div>

            {/* trigger slice */}
            <Button onClick={() => trigger.mutate()} disabled={trigger.isPending}>
              <Play className="size-4 mr-1.5" />
              Trigger slice
            </Button>
          </div>
        </CardHeader>

        <CardContent>
          {data?.length ? (
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={data}>
                <XAxis
                  dataKey="TIMESTAMP"
                  tickFormatter={(t) =>
                    new Date(t).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })
                  }
                />
                <YAxis
                  label={{ value: "ΔH [mm]", angle: -90, position: "insideLeft" }}
                />
                <Tooltip
                  formatter={(v: number) => v.toFixed(1) + " mm"}
                  labelFormatter={(l) => new Date(l).toLocaleString()}
                />
                <Line
                  type="monotone"
                  stroke="hsl(var(--chart-1))"
                  strokeWidth={2}
                  dot={false}
                  dataKey="Delta_H_mm"
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-muted-foreground">No data in this window.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}