/** Helpers for the pre-gig readiness check (service `gig-readiness`). */
export type ReadinessIssue = {code: string; severity: 'blocker' | 'warning' | 'info'; message: string; fix: {action: string; label: string; cue_id?: string; path?: string}};
export type ReadinessRow = {track_id: string; title: string | null; artist: string | null; status: 'ready' | 'check' | 'blocked'; issues: ReadinessIssue[]};
export type ReadinessScope = {kind: 'selection'; ids: string[]} | {kind: 'playlist'; name: string} | {kind: 'set'; id: string};

export function readinessParams(scope: ReadinessScope, verifyAudio: boolean) {
  const base = verifyAudio ? {verify_audio: true} : {};
  if (scope.kind === 'selection') return {...base, track_ids: scope.ids};
  if (scope.kind === 'playlist') return {...base, playlist: scope.name};
  return {...base, set_id: scope.id};
}

const rank = {blocked: 0, check: 1, ready: 2} as const;
const severityRank = {blocker: 0, warning: 1, info: 2} as const;

/** Blocked tracks first, then those to check, then ready ones; within a status the
 * service's order (the set's or playlist's) is kept. Issues inside a row by severity. */
export function orderRows(rows: ReadinessRow[]): ReadinessRow[] {
  return rows.map((row, index) => ({row, index}))
    .sort((a, b) => rank[a.row.status] - rank[b.row.status] || a.index - b.index)
    .map(({row}) => ({...row, issues: [...row.issues].sort((a, b) => severityRank[a.severity] - severityRank[b.severity])}));
}

/** Which issue codes appear most often, so the DJ can fix one kind at a time. */
export function issueCounts(rows: ReadinessRow[]): {code: string; message: string; count: number}[] {
  const counts = new Map<string, {code: string; message: string; count: number}>();
  for (const row of rows) for (const issue of row.issues) {
    if (issue.severity === 'info') continue;
    const entry = counts.get(issue.code) || {code: issue.code, message: issue.fix.label, count: 0};
    entry.count += 1;
    counts.set(issue.code, entry);
  }
  return [...counts.values()].sort((a, b) => b.count - a.count || a.code.localeCompare(b.code));
}
