"use client";

import { createContext, useContext } from "react";
import type { CurrentUser } from "./types";

/** The signed-in user, provided by the app shell to every page inside it. */
export const SessionContext = createContext<CurrentUser | null>(null);

export function useCurrentUser(): CurrentUser {
  const user = useContext(SessionContext);
  if (!user) throw new Error("useCurrentUser was called outside the signed-in app shell");
  return user;
}

/** Where to go after signing in. Only a path inside this app is accepted. */
export function safeNextPath(value: string | null | undefined): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.startsWith("/login")) return "/";
  return value;
}
