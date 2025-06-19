import { useQuery } from "@tanstack/react-query";
import { api } from "../api";

export default function Logs() {
  const { data } = useQuery(
    ["logs"],
    () => api.get("/logs", { params: { tail: 200 } }).then((r) => r.data),
    { refetchInterval: 2000 }
  );
  return (
    <pre className="bg-black text-green-400 p-4 h-[80vh] overflow-auto text-xs">
      {data?.lines.join("\n")}
    </pre>
  );
}