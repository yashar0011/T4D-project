import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { Link, Route, Routes, useParams } from "react-router-dom";

/* ------------------------------------------------------------------ */
export default function Files() {
  return (
    <Routes>
      <Route index element={<Tree />} />
      <Route path="/*" element={<File />} />
    </Routes>
  );
}

/* --------- 1. Folder tree ------------------------------------------------ */
function Tree() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["sites"],
    queryFn: () => api.get("/outputs/sites").then((r) => r.data),
    staleTime: 60_000,
  });

  if (isLoading) return <p className="p-4">Loading…</p>;
  if (error) return <p className="p-4 text-red-600">Failed to load</p>;

  return (
    <ul className="pl-4 list-disc space-y-1">
      {data?.sites.map((s: string) => (
        <li key={s}>
          <Link className="text-blue-600 hover:underline" to={s}>
            {s}
          </Link>
        </li>
      ))}
    </ul>
  );
}

/* --------- 2. Single file download -------------------------------------- */
function File() {
  const { "*": path } = useParams();          // catch-all route
  if (!path) return null;

  const url = `/api/outputs/file?path=${encodeURIComponent(path)}`;

  return (
    <div className="p-4">
      <a href={url} className="text-blue-600 underline">
        Download {path}
      </a>
    </div>
  );
}
