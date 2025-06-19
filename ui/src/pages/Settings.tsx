import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";
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
  const { data, isLoading } = useQuery<Row[]>(["settings"], () =>
    api.get("/settings").then((r) => r.data)
  );

  const [editing, setEditing] = useState<Row | null>(null);
  const save = useMutation({
    mutationFn: (row: Row) => api.put(`/settings/${row.id}`, row),
    onSuccess: () => qc.invalidateQueries(["settings"]),
  });

  if (isLoading) return <Loader2 className="animate-spin" />;

  return (
    <Card>
      <CardHeader className="flex justify-between items-center">
        <h2 className="text-xl font-semibold">Settings</h2>
        {editing && (
          <Button onClick={() => save.mutate(editing)} disabled={save.isLoading}>
            {save.isLoading ? "Saving…" : "Save"}
          </Button>
        )}
      </CardHeader>

      <CardContent>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b">
              {[
                "Active",
                "SensorID",
                "Site",
                "PointName",
                "Type",
                "BaselineH",
                "StartUTC",
              ].map((c) => (
                <th key={c} className="p-2 text-left font-medium">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data!.map((row) => (
              <tr
                key={row.id}
                className="border-b hover:bg-gray-100 cursor-pointer"
                onClick={() => setEditing(row)}
              >
                <td className="p-2">{row.Active ? "✔" : ""}</td>
                <td className="p-2">{row.SensorID}</td>
                <td className="p-2">{row.Site}</td>
                <td className="p-2">{row.PointName}</td>
                <td className="p-2">{row.Type}</td>
                <td className="p-2">{row.BaselineH}</td>
                <td className="p-2">{new Date(row.StartUTC).toISOString()}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {editing && (
          <div className="grid grid-cols-3 gap-2 mt-4">
            <Input
              value={editing.BaselineH}
              onChange={(e) =>
                setEditing({ ...editing, BaselineH: +e.target.value })
              }
            />
            <Input
              value={editing.StartUTC}
              onChange={(e) =>
                setEditing({ ...editing, StartUTC: e.target.value })
              }
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}