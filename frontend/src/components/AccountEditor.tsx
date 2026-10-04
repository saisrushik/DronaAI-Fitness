import { useState, type FormEvent } from "react";
import { useAuth, type Role, type User } from "../context/AuthContext";
import { api } from "../lib/api";
import Modal from "./Modal";

interface Props {
  user: User;
  onClose: () => void;
}

/** Popup for editing name, email, role, gender and date of birth. */
export default function AccountEditor({ user, onClose }: Props) {
  const { setUser } = useAuth();
  const profile = user.role === "coach" ? user.coach : user.customer;
  const [form, setForm] = useState({
    first_name: user.first_name,
    last_name: user.last_name,
    email: user.email,
    role: user.role as Role,
    gender: profile?.gender ?? "",
    date_of_birth: profile?.date_of_birth ?? "",
    current_password: "",
  });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const update = (field: keyof typeof form, value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const emailChanged = form.email.trim().toLowerCase() !== user.email.toLowerCase();
  const roleChanged = form.role !== user.role;
  const needsPassword = emailChanged || roleChanged;

  const save = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setSaving(true);
    try {
      const updated = await api.put<User>("/auth/me/account", {
        first_name: form.first_name,
        last_name: form.last_name,
        email: form.email.trim(),
        role: form.role,
        gender: form.gender || null,
        date_of_birth: form.date_of_birth || null,
        current_password: needsPassword ? form.current_password : null,
      });
      setUser(updated);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update your details");
      setSaving(false);
    }
  };

  return (
    <Modal
      onClose={onClose}
      title={<h2 className="text-lg font-semibold text-slate-900">Edit account details</h2>}
    >
      <form onSubmit={save} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="acc-first">
              First name
            </label>
            <input
              id="acc-first"
              required
              maxLength={60}
              value={form.first_name}
              onChange={(e) => update("first_name", e.target.value)}
              className="input"
            />
          </div>
          <div>
            <label className="label" htmlFor="acc-last">
              Last name
            </label>
            <input
              id="acc-last"
              maxLength={60}
              value={form.last_name}
              onChange={(e) => update("last_name", e.target.value)}
              className="input"
            />
          </div>
        </div>

        <div>
          <label className="label" htmlFor="acc-email">
            Email
          </label>
          <input
            id="acc-email"
            type="email"
            required
            value={form.email}
            onChange={(e) => update("email", e.target.value)}
            className="input"
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label className="label" htmlFor="acc-role">
              Role
            </label>
            <select
              id="acc-role"
              value={form.role}
              onChange={(e) => update("role", e.target.value)}
              className="input"
            >
              <option value="customer">Customer</option>
              <option value="coach">Coach</option>
            </select>
          </div>
          <div>
            <label className="label" htmlFor="acc-gender">
              Gender
            </label>
            <select
              id="acc-gender"
              value={form.gender}
              required={form.role === "customer"}
              onChange={(e) => update("gender", e.target.value)}
              className="input"
            >
              <option value="">Prefer not to say</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div>
            <label className="label" htmlFor="acc-dob">
              Date of birth
            </label>
            <input
              id="acc-dob"
              type="date"
              required={form.role === "customer"}
              max={new Date().toISOString().slice(0, 10)}
              value={form.date_of_birth}
              onChange={(e) => update("date_of_birth", e.target.value)}
              className="input"
            />
          </div>
        </div>
        {form.role === "customer" && (
          <p className="-mt-2 text-xs text-slate-500">
            Gender and date of birth are used for your BMR and body fat calculations.
          </p>
        )}

        {roleChanged && (
          <p className="rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-900">
            Switching to a <span className="font-semibold">{form.role}</span> account changes what
            you can see and do. You&apos;ll be asked to complete your {form.role} profile next.
          </p>
        )}

        {needsPassword && (
          <div>
            <label className="label" htmlFor="acc-password">
              Current password
            </label>
            <input
              id="acc-password"
              type="password"
              required
              autoComplete="current-password"
              value={form.current_password}
              onChange={(e) => update("current_password", e.target.value)}
              className="input"
            />
            <p className="mt-1 text-xs text-slate-500">
              Needed to change your email or role.
            </p>
          </div>
        )}

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex flex-col-reverse gap-2 border-t border-slate-100 pt-4 sm:flex-row sm:justify-end">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? "Saving…" : "Save details"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
