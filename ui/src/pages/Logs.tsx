// ui/src/pages/Logs.tsx
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";

export default function Logs() {
  /* ----------------- v5 object signature -------------- */
  const { data, isLoading, error } = useQuery({
    queryKey: ["logs", 200],                 // key can include tail size
    queryFn: () =>
      api.get("/logs", { params: { tail: 200 } }).then((r) => r.data),
    refetchInterval: 2_000,                  // 2 s live refresh
  });

  if (isLoading) return <p className="p-4">Loading…</p>;
  if (error) return <p className="p-4 text-red-600">Failed to load logs.</p>;

  return (
    <pre className="bg-black text-green-400 p-4 h-[80vh] overflow-auto text-xs">
      {data?.lines.join("\n")}
    </pre>
  );
}