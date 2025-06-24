import {
  useQuery,
  useMutation,
  useQueryClient,
  QueryClient,
} from "@tanstack/react-query";
import { api } from "../api";
import {
  Card,
  CardHeader,
  CardContent,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Loader2Icon as Loader2 } from "lucide-react";
import { useState } from "react";

type Row = {
  id: number;
  Active: boolean;
  SensorID: number;
  Site: string;
  PointName: string;
  Type: "Reflective" | "Reflectless";
  BaselineH: number;
  StartUTC: string;
};

export default function Settings() {
  const qc = useQueryClient();

  /* ---------- GET all rows ---------- */
  const { data, isLoading } = useQuery<Row[]>({
    queryKey: ["settings"],
    queryFn: () => api.get("/settings").then((r) => r.data),
  });

  /* ---------- PUT one row ---------- */
  const [editing, setEditing] = useState<Row | null>(null);

  const save = useMutation({
  mutationFn: (row: Row) => api.put(`/settings/${row.id}`, row),
  onSuccess: () => qc.invalidateQueries({ queryKey: ["settings"] }),
});

  if (isLoading) return <Loader2 className="animate-spin" />;

  return (
    <Card>
      <CardHeader className="flex justify-between items-center">
        <h2 className="text-xl font-semibold">Settings</h2>
        {editing && (
          <Button
            onClick={() => save.mutate(editing)}
            disabled={save.isPending}     // ← was isLoading
          >
            {save.isPending ? "Saving…" : "Save"}
          </Button>
        )}
      </CardHeader>

      <CardContent className="space-y-4">
        {data?.map((row) => (
          <div
            key={row.id}
            className="grid grid-cols-[repeat(7,minmax(0,1fr))] gap-2 items-center"
          >
            <input
              type="checkbox"
              checked={row.Active}
              onChange={(e) =>
                setEditing({ ...row, Active: e.target.checked })
              }
            />
            <span>{row.SensorID}</span>
            <span>{row.Site}</span>
            <Input
              value={row.PointName}
              onChange={(e) =>
                setEditing({ ...row, PointName: e.target.value })
              }
            />
            <span>{row.Type}</span>
            <Input
              type="number"
              value={row.BaselineH}
              onChange={(e) =>
                setEditing({
                  ...row,
                  BaselineH: parseFloat(e.target.value),
                })
              }
            />
            <span>{row.StartUTC}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}