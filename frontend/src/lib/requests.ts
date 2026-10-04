import type { DietItem } from "../components/WeeklyDietPlan";

export type RequestType = "meal" | "workout" | "injury" | "query";
export type RequestStatus = "pending" | "approved" | "rejected" | "resolved";

export interface RequestedMeal {
  day: string;
  session: string;
  items: string[];
  /** Present on pending requests: the change compared with the current plan. */
  kept?: string[];
  added?: string[];
  removed?: string[];
}

export interface CustomerRequest {
  id: string;
  customer_id: string;
  customer_name: string;
  plan_id: string | null;
  plan_title: string | null;
  request_type: RequestType;
  status: RequestStatus;
  description: string;
  requested_meals: RequestedMeal[] | null;
  approved_meals: { day: string; session: string; items: DietItem[] }[] | null;
  coach_note: string;
  created_at: string;
  resolved_at: string | null;
}

export const REQUEST_TYPE_LABELS: Record<RequestType, string> = {
  meal: "Meal",
  workout: "Workout",
  injury: "Injury",
  query: "Query",
};

export const STATUS_LABELS: Record<RequestStatus, string> = {
  pending: "Pending",
  approved: "Approved",
  rejected: "Declined",
  resolved: "Answered",
};

export const STATUS_STYLES: Record<RequestStatus, string> = {
  pending: "bg-amber-100 text-amber-800",
  approved: "bg-emerald-100 text-emerald-800",
  rejected: "bg-slate-200 text-slate-700",
  resolved: "bg-indigo-100 text-indigo-800",
};

export const TYPE_STYLES: Record<RequestType, string> = {
  meal: "bg-emerald-50 text-emerald-700",
  workout: "bg-indigo-50 text-indigo-700",
  injury: "bg-rose-50 text-rose-700",
  query: "bg-sky-50 text-sky-700",
};

export const requestLink = (id: string) => `/requests?highlight=${id}`;

export const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });

export const formatTime = (iso: string) =>
  new Date(iso).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });

export const formatDateTime = (iso: string) => `${formatDate(iso)}, ${formatTime(iso)}`;
