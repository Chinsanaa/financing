'use client';

import { useEffect, useState } from 'react';
import { api } from './api';
import { createClient } from './supabase';

/**
 * Onboarding-tour state, shared by the tour UI and the tabs whose actions
 * complete a step. The source of truth is the account (GET /dashboard/tour —
 * profiles.tour_step / tour_finished_at), NOT localStorage and NOT inferred
 * from data: the tour moves forward only when a tab reports that the user
 * just did the current step, and the server re-checks that (compare-and-set),
 * so a step can never be skipped.
 */

export const TOUR_STEPS = ['upload', 'categories', 'label', 'train'] as const;
export type TourStep = (typeof TOUR_STEPS)[number];
export type TourState = { finished: boolean; step: TourStep | null };

let state: TourState | null = null; // null = not loaded yet
let loading: Promise<void> | null = null;
const listeners = new Set<(s: TourState | null) => void>();

function set(next: TourState) {
  state = next;
  listeners.forEach((l) => l(state));
}

function load(): Promise<void> {
  if (!loading) {
    loading = api
      .get('/dashboard/tour')
      .then((res) => set(res.data))
      // If the tour can't be loaded, don't show it (never block the app).
      .catch(() => set({ finished: true, step: null }));
  }
  return loading;
}

/** Report that the user just completed `step`. No-op unless it's the
 * current step — safe to call after every upload / label / training run. */
export async function advanceTour(step: TourStep): Promise<void> {
  if (!state || state.finished || state.step !== step) return;
  try {
    const res = await api.post('/dashboard/tour/advance', { completed: step });
    set(res.data);
  } catch {
    // Tour progress is non-critical; the next successful action retries.
  }
}

/** "Skip tour" — ends it for good on this account. */
export async function skipTour(): Promise<void> {
  set({ finished: true, step: null }); // hide immediately
  try {
    await api.post('/dashboard/tour/skip');
  } catch {
    // Already hidden; worst case it returns on the next visit.
  }
}

export function useTour(): TourState | null {
  const [s, setS] = useState<TourState | null>(state);
  useEffect(() => {
    listeners.add(setS);
    load();
    setS(state);
    return () => {
      listeners.delete(setS);
    };
  }, []);
  return s;
}

// Tour state belongs to the signed-in account: forget it on sign-out so a
// different account on the same tab loads its own.
if (typeof window !== 'undefined') {
  createClient().auth.onAuthStateChange((event) => {
    if (event === 'SIGNED_OUT') {
      state = null;
      loading = null;
    }
  });
}
