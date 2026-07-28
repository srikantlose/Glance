export type Priority = "high" | "normal" | "low";
export type SuggestedAction = "archive" | "reply_today" | "delegate" | "convert_to_task" | "none";

export interface InboxMessage {
  id: string;
  thread_id: string | null;
  from: string;
  subject: string;
  snippet: string;
  date: string;
  unread: boolean;
}

export interface CalendarEvent {
  id: string;
  title: string;
  start: string | null;
  end: string | null;
  attendees: string[];
  external: boolean;
  conflict_group: string | null;
}

export interface TaskItem {
  id: string;
  title: string;
  notes: string | null;
  due: string | null;
  status: string;
  overdue: boolean;
}

export interface ConflictGroup {
  group_id: string;
  event_ids: string[];
  summary: string;
}

export interface DashboardSnapshot {
  inbox: InboxMessage[];
  events: CalendarEvent[];
  tasks: TaskItem[];
  conflicts: ConflictGroup[];
}

export interface TriageVerdict {
  priority: Priority;
  suggested_action: SuggestedAction;
  reasoning: string;
  cited_policy_id: string | null;
  cited_policy_text: string | null;
  cached: boolean;
  latency_ms: number;
}

export interface ActionDescriptor {
  tool: "gmail" | "calendar" | "tasks";
  operation: string;
  params: Record<string, unknown>;
  agent_name?: string | null;
}

export interface Authorization {
  type: "policy" | "instruction" | "approval";
  ref?: string | null;
}

export interface ExecuteResult {
  status: "executed" | "queued" | "needs_approval";
  action_id?: string;
  approval_id?: string;
  result?: unknown;
}

export interface SchedulerOption {
  rank: number;
  action: "event.move" | "event.delete" | "event.create" | "none";
  event_changes: {
    event_id: string | null;
    new_start: string;
    new_end: string;
    title?: string | null;
    attendees?: string[];
  } | null;
  justification: string;
  cited_episode_or_policy: string | null;
  descriptor: ActionDescriptor | null;
}

export type EntityKind = "message" | "event" | "task";

export interface EntityTarget {
  kind: EntityKind;
  id: string;
  label: string;
  /** the whole conflict group, when the pointer is on a clashing event */
  eventIds?: string[];
}

export type CommandResponse =
  | { type: "executed"; summary: string; actions: { action_id: string; tool: string; operation: string; status: string }[] }
  | { type: "clarification"; clarification_id: string; question: string }
  | { type: "approval_pending"; approval_id: string; preview: unknown; saved_policy_id?: string }
  | { type: "options"; conflict_summary: string; options: SchedulerOption[]; saved_policy_id?: string };

export interface PiiFinding {
  type: string;
  original: string;
  redacted: string;
  flagged_by: string;
}

export interface Approval {
  id: string;
  created_at: string;
  preview: { actions: ActionDescriptor[]; rendered: string };
  pii_findings: PiiFinding[];
  status: "pending" | "approved" | "rejected";
}

export interface LedgerRowData {
  id: string;
  created_at: string;
  actor: string;
  agent_name: string | null;
  tool: string;
  operation: string;
  params_json: Record<string, unknown>;
  authorization_type: "policy" | "instruction" | "approval";
  authorization_ref: string | null;
  lyzr_trace_id: string | null;
  idempotency_key: string;
  status: string;
  result_json: Record<string, unknown> | null;
  inverse_operation: string | null;
  inverse_params_json: Record<string, unknown> | null;
  irreversible: boolean;
  undone_at: string | null;
  undone_by: string | null;
}

export interface Policy {
  id: string;
  text: string;
  scope: "email" | "calendar" | "tasks" | "global";
  confidence: number;
  provenance: "explicit" | "learned";
  times_applied: number;
  created_at: string;
}

export interface AccountService {
  name: string;
  granted: boolean;
  scope: string | null;
}

export interface AccountInfo {
  email: string | null;
  connected: boolean;
  error: string | null;
  services: AccountService[];
}

export interface HealthInfo {
  ok: boolean;
  db: boolean;
  qdrant: boolean;
}
