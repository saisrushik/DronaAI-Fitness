import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import DietRequestReview from "../components/DietRequestReview";
import Modal from "../components/Modal";
import { useAuth } from "../context/AuthContext";
import { useNotifications } from "../context/NotificationsContext";
import { api } from "../lib/api";
import {
  REQUEST_TYPE_LABELS,
  STATUS_LABELS,
  STATUS_STYLES,
  TYPE_STYLES,
  formatDate,
  formatDateTime,
  formatTime,
  type CustomerRequest,
  type RequestType,
} from "../lib/requests";

type Sort = "newest" | "oldest";
type CreatableType = Exclude<RequestType, "meal">;

const CREATABLE: { value: CreatableType; label: string; hint: string }[] = [
  { value: "workout", label: "Workout change", hint: "e.g. Swap barbell squats for something knee-friendly" },
  { value: "injury", label: "Injury", hint: "e.g. Pain in my left knee during lunges since Monday" },
  { value: "query", label: "Query", hint: "e.g. How much water should I drink on training days?" },
];

function summary(request: CustomerRequest): string {
  if (request.description) return request.description;
  return (request.requested_meals ?? [])
    .map((meal) => `${meal.day} ${meal.session}: ${meal.items.join(", ")}`)
    .join(" · ");
}

function Badge({ className, children }: { className: string; children: string }) {
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${className}`}>
      {children}
    </span>
  );
}

function NewRequestForm({ onCreated, onCancel }: { onCreated: (id: string) => void; onCancel: () => void }) {
  const [type, setType] = useState<CreatableType>("workout");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setSaving(true);
    try {
      const created = await api.post<CustomerRequest>("/requests", {
        request_type: type,
        description,
      });
      onCreated(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the request");
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="card space-y-4 border-indigo-200">
      <h2 className="text-lg font-semibold">New request</h2>
      <div>
        <span className="label">Request type</span>
        <div className="grid gap-2 sm:grid-cols-3">
          {CREATABLE.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setType(option.value)}
              className={`rounded-xl border px-3 py-2 text-left text-sm font-medium transition ${
                type === option.value
                  ? "border-indigo-500 bg-indigo-50 text-indigo-800"
                  : "border-slate-300 text-slate-700 hover:bg-slate-50"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2 rounded-lg bg-slate-50 px-3 py-2">
          <p className="text-xs text-slate-600">Want different meals? Raise a meal request from your diet plan.</p>
          <Link to="/diet-plan" className="btn-soft btn-sm">
            Open diet plan
          </Link>
        </div>
      </div>
      <div>
        <label className="label" htmlFor="request-description">
          Description
        </label>
        <textarea
          id="request-description"
          rows={4}
          required
          minLength={5}
          maxLength={1000}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="input"
          placeholder={CREATABLE.find((o) => o.value === type)?.hint}
        />
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <button type="button" className="btn-secondary" onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? "Submitting…" : "Submit request"}
        </button>
      </div>
    </form>
  );
}

function RespondForm({ request, onDone }: { request: CustomerRequest; onDone: () => Promise<void> }) {
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<"resolve" | "reject" | null>(null);

  const run = async (action: "resolve" | "reject") => {
    setError("");
    setBusy(action);
    try {
      await api.post(`/requests/${request.id}/${action}`, { note });
      await onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save your response");
      setBusy(null);
    }
  };

  const canDecline = request.request_type === "workout";
  const canSend = busy === null && note.trim() !== "";

  return (
    <div className="space-y-3">
      <label className="label" htmlFor={`respond-${request.id}`}>
        {request.request_type === "query" ? "Your answer" : "Your response"}
      </label>
      <textarea
        id={`respond-${request.id}`}
        rows={3}
        maxLength={500}
        value={note}
        onChange={(e) => setNote(e.target.value)}
        onKeyDown={(e) => {
          // Enter sends; Shift+Enter adds a new line.
          if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault();
            if (canSend) void run("resolve");
          }
        }}
        className="input bg-white"
      />
      <p className="text-xs text-slate-500">Press Enter to send, Shift+Enter for a new line.</p>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        {canDecline && (
          <button
            type="button"
            className="btn-secondary"
            disabled={busy !== null}
            onClick={() => void run("reject")}
          >
            {busy === "reject" ? "Declining…" : "Decline"}
          </button>
        )}
        <button
          type="button"
          className="btn-primary"
          disabled={!canSend}
          onClick={() => void run("resolve")}
        >
          {busy === "resolve" ? "Sending…" : "Send response"}
        </button>
      </div>
    </div>
  );
}

function RequestDetail({
  request,
  isCoach,
  onDone,
}: {
  request: CustomerRequest;
  isCoach: boolean;
  onDone: () => Promise<void>;
}) {
  const pending = request.status === "pending";

  return (
    <div className="space-y-4 text-sm">
      {request.plan_title && <p className="text-xs text-slate-500">Plan: {request.plan_title}</p>}

      {request.description && (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {request.request_type === "meal" ? "Note" : "Description"}
          </h4>
          <p className="mt-1 whitespace-pre-line text-slate-800">{request.description}</p>
        </div>
      )}

      {request.requested_meals && !(pending && isCoach) && (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Requested changes
          </h4>
          <ul className="mt-1 space-y-2">
            {request.requested_meals.map((meal) => (
              <li key={`${meal.day}|${meal.session}`}>
                <span className="font-medium">
                  {meal.day} · {meal.session}
                </span>
                {meal.added ? (
                  <span className="mt-0.5 block text-slate-700">
                    {meal.added.length > 0 && (
                      <span className="block text-emerald-700">Add: {meal.added.join(", ")}</span>
                    )}
                    {meal.removed && meal.removed.length > 0 && (
                      <span className="block text-rose-700">
                        Remove: {meal.removed.join(", ")}
                      </span>
                    )}
                  </span>
                ) : (
                  <span className="block text-slate-700">{meal.items.join(", ")}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {request.approved_meals && (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            New foods approved by coach
          </h4>
          <ul className="mt-1 space-y-2">
            {request.approved_meals.map((meal) => (
              <li key={`${meal.day}|${meal.session}`}>
                <span className="font-medium">
                  {meal.day} · {meal.session}
                </span>
                <ul className="mt-1 space-y-0.5 text-slate-600">
                  {meal.items.map((item) => (
                    <li key={item.name}>
                      {item.name} ({item.quantity}) — {item.calories} kcal · P {item.protein_g}g ·
                      C {item.carbs_g}g · F {item.fat_g}g
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </div>
      )}

      {!pending && (
        <div className="rounded-xl bg-slate-50 p-3">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Coach response · {request.resolved_at && formatDateTime(request.resolved_at)}
          </h4>
          <p className="mt-1 whitespace-pre-line text-slate-800">
            {request.coach_note || <span className="text-slate-500">No note added.</span>}
          </p>
        </div>
      )}

      {pending && !isCoach && (
        <p className="rounded-xl bg-amber-50 px-3 py-2 text-amber-800">
          Waiting for your coach to review.
        </p>
      )}

      {pending && isCoach && request.request_type === "meal" && (
        <DietRequestReview request={request} onDone={onDone} />
      )}
      {pending && isCoach && request.request_type !== "meal" && (
        <RespondForm request={request} onDone={onDone} />
      )}
    </div>
  );
}

export default function RequestsPage() {
  const { user } = useAuth();
  const { refresh: refreshNotifications } = useNotifications();
  const [searchParams, setSearchParams] = useSearchParams();
  const highlight = searchParams.get("highlight");

  const [requests, setRequests] = useState<CustomerRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sort, setSort] = useState<Sort>("newest");
  const [typeFilter, setTypeFilter] = useState<RequestType | "all">("all");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string | null>(highlight);
  // Keeps the last viewed row outlined after its popup closes.
  const [recent, setRecent] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const isCoach = user?.role === "coach";
  const hasCoach = !!user?.customer?.coach_id;

  const load = useCallback(
    () =>
      api
        .get<CustomerRequest[]>("/requests")
        .then(setRequests)
        .catch((err) => setError(err instanceof Error ? err.message : "Could not load requests"))
        .finally(() => setLoading(false)),
    [],
  );

  useEffect(() => {
    void load();
  }, [load]);

  // Arriving from a notification: clear filters, bring the row into view and open its details.
  useEffect(() => {
    if (!highlight || loading) return;
    setTypeFilter("all");
    setSearch("");
    setSelected(highlight);
    const timer = window.setTimeout(
      () =>
        document
          .getElementById(`request-${highlight}`)
          ?.scrollIntoView({ behavior: "smooth", block: "center" }),
      50,
    );
    return () => window.clearTimeout(timer);
  }, [highlight, loading]);

  const visible = useMemo(() => {
    const query = search.trim().toLowerCase();
    const direction = sort === "newest" ? -1 : 1;
    return requests
      .filter((r) => typeFilter === "all" || r.request_type === typeFilter)
      .filter((r) => !query || r.description.toLowerCase().includes(query))
      .sort((a, b) => direction * (Date.parse(a.created_at) - Date.parse(b.created_at)));
  }, [requests, typeFilter, search, sort]);

  const pendingCount = requests.filter((r) => r.status === "pending").length;

  const afterChange = async () => {
    await Promise.all([load(), refreshNotifications().catch(() => undefined)]);
  };

  const openRequest = (id: string) => {
    setSelected(id);
    setRecent(id);
  };

  const closeRequest = () => {
    setSelected(null);
    // Clearing the param lets the same notification reopen this popup later.
    if (highlight) setSearchParams({}, { replace: true });
  };

  const selectedRequest = requests.find((r) => r.id === selected);
  const marked = highlight ?? recent;

  const columns = isCoach
    ? "md:grid-cols-[7rem_minmax(0,10rem)_6rem_minmax(0,1fr)_6.5rem_2rem]"
    : "md:grid-cols-[7rem_6rem_minmax(0,1fr)_6.5rem_2rem]";

  if (loading) return <p className="py-20 text-center text-slate-500">Loading requests…</p>;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold sm:text-3xl">Requests</h1>
          <p className="mt-1 text-slate-600">
            {isCoach
              ? "Meal changes, workout changes, injuries and questions from your customers."
              : "Everything you've asked your coach, and their responses."}
            {pendingCount > 0 && (
              <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                {pendingCount} pending
              </span>
            )}
          </p>
        </div>
        {!isCoach && !creating && (
          <button
            type="button"
            className="btn-primary w-full sm:w-auto"
            onClick={() => setCreating(true)}
            disabled={!hasCoach}
            title={hasCoach ? undefined : "You need a coach before you can send requests"}
          >
            + New request
          </button>
        )}
      </header>

      {!isCoach && !hasCoach && (
        <p className="rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-800">
          You don&apos;t have a coach yet. Share the code on your profile page with a coach to start
          sending requests.
        </p>
      )}

      {creating && (
        <NewRequestForm
          onCancel={() => setCreating(false)}
          onCreated={(id) => {
            setCreating(false);
            void afterChange();
            setSearchParams({ highlight: id }, { replace: true });
          }}
        />
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto_auto]">
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input"
          placeholder="Search descriptions…"
          aria-label="Search descriptions"
        />
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value as RequestType | "all")}
          className="input sm:w-40"
          aria-label="Request type"
        >
          <option value="all">All types</option>
          {(Object.keys(REQUEST_TYPE_LABELS) as RequestType[]).map((type) => (
            <option key={type} value={type}>
              {REQUEST_TYPE_LABELS[type]}
            </option>
          ))}
        </select>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as Sort)}
          className="input sm:w-40"
          aria-label="Sort by date"
        >
          <option value="newest">Newest first</option>
          <option value="oldest">Oldest first</option>
        </select>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div
          className={`hidden gap-4 border-b border-slate-200 bg-slate-50 px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-slate-500 md:grid ${columns}`}
        >
          <button
            type="button"
            onClick={() => setSort((s) => (s === "newest" ? "oldest" : "newest"))}
            className="flex items-center gap-1 text-left uppercase hover:text-slate-800"
            aria-label={`Sort by date, currently ${sort} first`}
          >
            Date <span aria-hidden>{sort === "newest" ? "↓" : "↑"}</span>
          </button>
          {isCoach && <span>Customer</span>}
          <span>Type</span>
          <span>Description</span>
          <span>Status</span>
          <span />
        </div>

        {visible.length === 0 ? (
          <p className="px-4 py-12 text-center text-sm text-slate-500">
            {requests.length === 0 ? "No requests yet." : "No requests match your filters."}
          </p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {visible.map((request) => {
              const highlighted = marked === request.id;
              return (
                <li
                  key={request.id}
                  id={`request-${request.id}`}
                  className={highlighted ? "relative z-[1] ring-2 ring-inset ring-indigo-400" : ""}
                >
                  <button
                    type="button"
                    onClick={() => openRequest(request.id)}
                    aria-haspopup="dialog"
                    className={`group flex w-full flex-wrap items-center gap-x-2 gap-y-1.5 px-4 py-3 text-left transition hover:bg-slate-50 md:grid md:gap-4 ${columns} ${
                      highlighted ? "bg-indigo-50/70" : ""
                    }`}
                  >
                    <span className="order-3 ml-auto text-xs text-slate-500 md:order-none md:ml-0 md:text-sm md:text-slate-700">
                      {formatDate(request.created_at)}
                      <span className="ml-1 md:ml-0 md:block md:text-xs md:text-slate-500">
                        {formatTime(request.created_at)}
                      </span>
                    </span>
                    {isCoach && (
                      <span className="order-4 w-full truncate font-medium text-slate-900 md:order-none md:w-auto">
                        {request.customer_name}
                      </span>
                    )}
                    <span className="order-1 md:order-none">
                      <Badge className={TYPE_STYLES[request.request_type]}>
                        {REQUEST_TYPE_LABELS[request.request_type]}
                      </Badge>
                    </span>
                    <span className="order-5 w-full truncate text-sm text-slate-600 md:order-none md:w-auto">
                      {summary(request) || "—"}
                    </span>
                    <span className="order-2 md:order-none">
                      <Badge className={STATUS_STYLES[request.status]}>
                        {STATUS_LABELS[request.status]}
                      </Badge>
                    </span>
                    <span
                      className="order-3 grid h-8 w-8 place-items-center rounded-lg text-slate-400 transition group-hover:bg-indigo-50 group-hover:text-indigo-600 md:order-none"
                      title="View request"
                    >
                      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M2.5 12S6 5 12 5s9.5 7 9.5 7-3.5 7-9.5 7-9.5-7-9.5-7z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                      <span className="sr-only">View request</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {visible.length > 0 && (
        <p className="text-xs text-slate-500">
          Showing {visible.length} of {requests.length} request{requests.length === 1 ? "" : "s"}
        </p>
      )}

      {selectedRequest && (
        <Modal
          onClose={closeRequest}
          title={
            <>
              <div className="flex flex-wrap items-center gap-2">
                <Badge className={TYPE_STYLES[selectedRequest.request_type]}>
                  {`${REQUEST_TYPE_LABELS[selectedRequest.request_type]} request`}
                </Badge>
                <Badge className={STATUS_STYLES[selectedRequest.status]}>
                  {STATUS_LABELS[selectedRequest.status]}
                </Badge>
              </div>
              <h2 className="mt-2 text-lg font-semibold text-slate-900">
                {isCoach ? selectedRequest.customer_name : "Your request"}
              </h2>
              <p className="text-xs text-slate-500">
                Submitted {formatDateTime(selectedRequest.created_at)}
              </p>
            </>
          }
        >
          <RequestDetail request={selectedRequest} isCoach={isCoach} onDone={afterChange} />
        </Modal>
      )}
    </div>
  );
}
