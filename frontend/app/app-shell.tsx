"use client";

import { useCallback, useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { ApiError, apiGet, apiPost, setSignedOutHandler } from "../lib/api";
import { SessionContext } from "../lib/session";
import type { CurrentUser } from "../lib/types";

type NavLink = { href: string; label: string; adminOnly?: boolean };

const NAV_LINKS: NavLink[] = [
  { href: "/bags", label: "Bags" },
  { href: "/bags/create/spawn", label: "Create Spawn Records" },
  { href: "/events/spawn-inoculation", label: "Spawn Inoculation" },
  { href: "/bags/create/substrate", label: "Create Substrate Records" },
  { href: "/events/incubation", label: "Incubation Start" },
  { href: "/events/ready", label: "Ready" },
  { href: "/events/inoculation", label: "Substrate Inoculation" },
  { href: "/events/fruiting", label: "Fruiting Start" },
  { href: "/events/harvest", label: "Harvest" },
  { href: "/events/disposal", label: "Disposal" },
  { href: "/reports", label: "Reports" },
  { href: "/species", label: "Species", adminOnly: true },
  { href: "/reference/species", label: "Species Reference" },
  { href: "/liquid-cultures", label: "Liquid Cultures" },
  { href: "/pasteurization-runs", label: "Pasteurization" },
  { href: "/sterilization-runs", label: "Sterilization" },
  { href: "/mix-lots", label: "Mix Lots" },
  { href: "/users", label: "Users", adminOnly: true },
];

function goToSignIn() {
  const here = window.location.pathname + window.location.search;
  const next = here && here !== "/" ? `?next=${encodeURIComponent(here)}` : "";
  window.location.assign(`/login${next}`);
}

/**
 * Everything around a page: who is signed in, the menu, and sign-out.
 *
 * No page inside the shell is drawn until the API has confirmed a session
 * (SRS USR-1). The API enforces the same rule on every request; this only
 * keeps a signed-out browser from seeing empty screens.
 */
export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const onSignInPage = pathname === "/login";
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  // On a small screen the menu is closed until asked for (styles.css).
  const [menuOpen, setMenuOpen] = useState(false);

  const loadUser = useCallback(async () => {
    try {
      setUser(await apiGet<CurrentUser>("/auth/me"));
      setProblem(null);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        goToSignIn();
      } else {
        setProblem("The app could not reach its server. Check the connection and reload the page.");
      }
    }
  }, []);

  useEffect(() => {
    if (onSignInPage) return;
    // A session that ends while a page is open sends the next request here.
    setSignedOutHandler(goToSignIn);
    loadUser();
    return () => setSignedOutHandler(null);
  }, [onSignInPage, loadUser]);

  // A password set by someone else (the first administrator's, or a reset)
  // is replaced before anything else is done.
  useEffect(() => {
    if (user?.must_change_password && pathname !== "/account") {
      window.location.assign("/account");
    }
  }, [user, pathname]);

  async function signOut() {
    try {
      await apiPost("/auth/logout", {});
    } catch {
      // Signed out or not, the next screen is the sign-in page.
    }
    window.location.assign("/login");
  }

  if (onSignInPage) {
    return <main className="container">{children}</main>;
  }

  if (!user) {
    return (
      <main className="container">
        <p className={problem ? "error" : "shellStatus"} role="status">
          {problem ?? "Loading…"}
        </p>
      </main>
    );
  }

  const links = NAV_LINKS.filter((link) => !link.adminOnly || user.role === "admin");

  return (
    <SessionContext.Provider value={user}>
      <header className="header">
        <div className="container row headerTop">
          <a className="brand" href="/">Mushroom Farm App</a>
          <div className="userBar">
            <a href="/account" className="userBarName" title="Your account">
              {user.display_name}
              <span className="userBarRole">{user.role === "admin" ? "Administrator" : "Operator"}</span>
            </a>
            <button type="button" className="btn btnSmall" onClick={signOut}>Sign out</button>
            <button
              type="button"
              className="btn btnSmall menuToggle"
              aria-expanded={menuOpen}
              aria-controls="main-menu"
              onClick={() => setMenuOpen((open) => !open)}
            >
              {menuOpen ? "Close menu" : "Menu"}
            </button>
          </div>
        </div>
        <div className="container">
          <nav id="main-menu" className={menuOpen ? "nav navOpen" : "nav"} aria-label="Main">
            {links.map((link) => (
              <a key={link.href} href={link.href}>{link.label}</a>
            ))}
          </nav>
        </div>
      </header>
      <main className="container">{children}</main>
    </SessionContext.Provider>
  );
}
