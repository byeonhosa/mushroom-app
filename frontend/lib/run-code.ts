"use client";

import { useEffect, useState } from "react";
import { apiGet } from "./api";

/**
 * The run code the server proposes for a run of this kind (SRS RUN-6): the
 * run's date as YYMMDD and the first letter not yet used that day, for
 * example 261109A.
 *
 * `unloadedAt` is the value of the form's datetime-local field. Its first ten
 * characters are the calendar day the operator chose, in the operator's own
 * time zone, which is the day the code should carry. When the field is empty
 * the server proposes a code for today. `refreshKey` changes when a run has
 * been created, so that the next proposal skips the letter just used.
 */
export function useProposedRunCode(
  kind: "sterilization" | "pasteurization",
  unloadedAt: string,
  refreshKey: number,
): string {
  const [code, setCode] = useState("");

  useEffect(() => {
    let cancelled = false;
    const day = unloadedAt ? unloadedAt.slice(0, 10) : "";
    const query = /^\d{4}-\d{2}-\d{2}$/.test(day) ? `?on=${day}` : "";
    apiGet<{ run_code: string }>(`/${kind}-runs/next-code${query}`)
      .then((result) => {
        if (!cancelled) setCode(result.run_code);
      })
      .catch(() => {
        // Leave the field as it is; the operator can still type a code.
      });
    return () => {
      cancelled = true;
    };
  }, [kind, unloadedAt, refreshKey]);

  return code;
}
