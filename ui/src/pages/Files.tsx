import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { Link, Route, Routes, useParams } from "react-router-dom";

export default function Files() {
  return (
    <Routes>
      <Route path="/" element={<Tree />} />
      <Route path="/*" element={<File />} />
    </Routes>
  );
}

function Tree() {
  const { data } = useQuery(["sites"], () =>
    api.get("/outputs/sites").then((r) => r.data)
  );
  if (!data) return null;
  return (
    <ul className="pl-4 list-disc">
      {data.sites.map((s: string) => (
        <li key={s}>
          <Link className="text-blue-600" to={s}>
            {s}
          </Link>
        </li>
      ))}
    </ul>
  );
}

function File() {
  const { "*": path } = useParams();
  if (!path) return null;
  return (
    <a
      href={`/api/outputs/file?path=${encodeURIComponent(path)}`}
      className="text-blue-600 underline"
    >
      Download {path}
    </a>
  );
}