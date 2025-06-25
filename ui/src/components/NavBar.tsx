import { Link, NavLink } from "react-router-dom";

export default function NavBar() {
  const base = "px-3 py-2 rounded-md text-sm font-medium";
  const active = "bg-primary text-primary-foreground";
  return (
    <header className="border-b border-border bg-card">
      <div className="mx-auto max-w-6xl flex items-center justify-between px-4">
        <Link to="/" className="text-xl font-bold py-4">
          T4D Dashboard
        </Link>

        <nav className="space-x-1">
          {["dashboard", "settings", "files", "logs"].map((p) => (
            <NavLink
              key={p}
              to={`/${p}`}
              className={({ isActive }) =>
                `${base} ${isActive ? active : "hover:bg-muted"}`
              }
              end
            >
              {p[0].toUpperCase() + p.slice(1)}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}