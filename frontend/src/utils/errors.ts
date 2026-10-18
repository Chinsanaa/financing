/**
 * User-facing message from a failed API call.
 *
 * FastAPI returns `detail` as a string for HTTPException, but as a LIST of
 * `{loc, msg, type}` objects for request-validation errors (422). Putting
 * that list straight into React state crashed the tab ("Objects are not
 * valid as a React child"), so every error path goes through here.
 */
export function errorDetail(err: unknown, fallback: string): string {
  const detail = (err as any)?.response?.data?.detail;
  if (typeof detail === 'string' && detail) return detail;
  if (Array.isArray(detail)) {
    return detail.map((d: any) => d?.msg).filter(Boolean).join('; ') || fallback;
  }
  return fallback;
}
