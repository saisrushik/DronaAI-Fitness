import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth, type User } from "../context/AuthContext";
import { api } from "../lib/api";
import Modal from "./Modal";

const errorText = (err: unknown, fallback: string) => (err instanceof Error ? err.message : fallback);

function DeleteAccountModal({ user, onClose }: { user: User; onClose: () => void }) {
  const { deleteAccount } = useAuth();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setDeleting(true);
    try {
      await deleteAccount(password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(errorText(err, "Could not delete your account"));
      setDeleting(false);
    }
  };

  return (
    <Modal
      onClose={onClose}
      title={<h2 className="text-lg font-semibold text-slate-900">Delete your account</h2>}
    >
      <form onSubmit={submit} className="space-y-4">
        <div className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-900">
          <p className="font-semibold">This can&apos;t be undone.</p>
          {user.role === "coach" ? (
            <p className="mt-1">
              Your account and profile are deleted permanently. Your customers are released and
              notified, and keep the plans you built for them.
            </p>
          ) : (
            <p className="mt-1">
              Your profile, plans, measurements, progress logs, requests and notifications are
              deleted permanently. Your coach loses access immediately.
            </p>
          )}
        </div>
        <p className="text-sm text-slate-600">
          Want a copy first? Close this and use <span className="font-medium">Download my data</span>.
        </p>

        <div>
          <label className="label" htmlFor="delete-password">
            Password
          </label>
          <input
            id="delete-password"
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input"
          />
        </div>

        <label className="flex items-start gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            className="mt-0.5"
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
          />
          I understand my account and data will be permanently deleted.
        </label>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex flex-col-reverse gap-2 border-t border-slate-100 pt-4 sm:flex-row sm:justify-end">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn-danger" disabled={!confirmed || !password || deleting}>
            {deleting ? "Deleting…" : "Delete my account"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

/** Data export, signing out other devices and account deletion. */
export default function AccountPrivacyCard({ user }: { user: User }) {
  const { logoutEverywhere } = useAuth();
  const navigate = useNavigate();
  const [busy, setBusy] = useState<"export" | "logout" | null>(null);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(false);

  const downloadData = async () => {
    setError("");
    setBusy("export");
    try {
      const data = await api.get<unknown>("/auth/me/export");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `dronaai-fit-my-data-${new Date().toISOString().slice(0, 10)}.json`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(errorText(err, "Could not export your data"));
    } finally {
      setBusy(null);
    }
  };

  const signOutEverywhere = async () => {
    if (!window.confirm("Log out on every device, including this one?")) return;
    setError("");
    setBusy("logout");
    try {
      await logoutEverywhere();
      navigate("/login", { replace: true });
    } catch (err) {
      setError(errorText(err, "Could not log out your devices"));
      setBusy(null);
    }
  };

  return (
    <div className="card">
      <h2 className="font-semibold">Your data &amp; sessions</h2>
      <p className="mt-1 text-sm text-slate-600">
        Download everything we store about you, or sign out of devices you no longer use.
      </p>
      <div className="mt-4 flex flex-col gap-2">
        <button type="button" className="btn-secondary" onClick={downloadData} disabled={busy !== null}>
          {busy === "export" ? "Preparing…" : "Download my data"}
        </button>
        <button type="button" className="btn-secondary" onClick={signOutEverywhere} disabled={busy !== null}>
          {busy === "logout" ? "Logging out…" : "Log out on all devices"}
        </button>
      </div>

      <div className="mt-5 border-t border-slate-100 pt-4">
        <button
          type="button"
          className="btn w-full border border-red-200 bg-white text-red-700 hover:bg-red-50"
          onClick={() => setDeleting(true)}
        >
          Delete account
        </button>
      </div>

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      {deleting && <DeleteAccountModal user={user} onClose={() => setDeleting(false)} />}
    </div>
  );
}
