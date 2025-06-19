import { Link, useLocation } from "react-router-dom";

export default function NavBar() {
  const loc = useLocation();
  const link = (to: string, label: string) => (
    <Link
      to={to}
      className={`px-4 py-2 hover:bg-gray-200 rounded-md ${
        loc.pathname.startsWith(to) ? "bg-gray-200" : ""
      }`}
    >
      {label}
    </Link>
  );
  return (
    <header className="flex items-center gap-2 shadow p-2 bg-white">
      <span className="font-bold mr-4">T4D Dashboard</span>
      {link("/dashboard", "Dashboard")}
      {link("/settings", "Settings")}
      {link("/files", "Files")}
      {link("/logs", "Logs")}
    </header>
  );
}