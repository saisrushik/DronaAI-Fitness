import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { APP_NAME } from "../config/brand";
import { useAuth, type Role } from "../context/AuthContext";
import { PASSWORD_HINT } from "./ResetPasswordPage";

const roleOptions: { value: Role; title: string; description: string }[] = [
  {
    value: "customer",
    title: "Customer",
    description: "I want personalized workout and diet plans.",
  },
  { value: "coach", title: "Coach", description: "I train customers and build their plans." },
];

const emptyForm = {
  first_name: "",
  last_name: "",
  email: "",
  password: "",
  confirm: "",
  date_of_birth: "",
  gender: "male",
  height_cm: "",
  weight_kg: "",
  waist_cm: "",
  neck_cm: "",
  hip_cm: "",
};

export default function RegisterPage() {
  const { register } = useAuth();
  const [form, setForm] = useState(emptyForm);
  const [role, setRole] = useState<Role>("customer");
  const [acceptedDisclaimer, setAcceptedDisclaimer] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const isCustomer = role === "customer";
  const update = (field: keyof typeof form, value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (form.password !== form.confirm) {
      setError("Passwords do not match.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      const message = await register({
        first_name: form.first_name,
        last_name: form.last_name,
        email: form.email,
        password: form.password,
        role,
        accepted_disclaimer: acceptedDisclaimer,
        ...(isCustomer && {
          date_of_birth: form.date_of_birth,
          gender: form.gender,
          height_cm: Number(form.height_cm),
          weight_kg: Number(form.weight_kg),
          waist_cm: Number(form.waist_cm),
          neck_cm: Number(form.neck_cm),
          ...(form.hip_cm ? { hip_cm: Number(form.hip_cm) } : {}),
        }),
      });
      setDone(message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setSubmitting(false);
    }
  };

  const numberField = (
    field: keyof typeof form,
    label: string,
    placeholder: string,
    { min, max, required = true }: { min: number; max: number; required?: boolean },
  ) => (
    <div>
      <label className="label" htmlFor={field}>
        {label}
      </label>
      <input
        id={field}
        type="number"
        step="0.1"
        min={min}
        max={max}
        required={required}
        value={form[field]}
        onChange={(e) => update(field, e.target.value)}
        className="input"
        placeholder={placeholder}
      />
    </div>
  );

  if (done) {
    return (
      <div className="mx-auto max-w-md">
        <div className="card text-center">
          <h1 className="text-2xl font-bold">Almost there</h1>
          <p className="mt-4 text-sm text-slate-600">{done}</p>
          <Link to="/login" className="btn-primary mt-6 inline-flex">
            Go to login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="card">
        <h1 className="text-2xl font-bold">Create your account</h1>
        <p className="mt-1 text-sm text-slate-600">
          {isCustomer
            ? "We use your measurements to calculate your health metrics."
            : "Tell us who you are — you'll add your coaching details next."}
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-5">
          <div>
            <span className="label">I am a…</span>
            <div className="grid gap-2 sm:grid-cols-2">
              {roleOptions.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setRole(option.value)}
                  className={`rounded-xl border p-3 text-left transition ${
                    role === option.value
                      ? "border-indigo-500 bg-indigo-50"
                      : "border-slate-300 hover:bg-slate-50"
                  }`}
                >
                  <span className="block font-medium text-slate-900">{option.title}</span>
                  <span className="mt-1 block text-xs text-slate-600">{option.description}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor="first_name">
                First name
              </label>
              <input
                id="first_name"
                required
                value={form.first_name}
                onChange={(e) => update("first_name", e.target.value)}
                className="input"
                placeholder="Alex"
              />
            </div>
            <div>
              <label className="label" htmlFor="last_name">
                Last name
              </label>
              <input
                id="last_name"
                required
                value={form.last_name}
                onChange={(e) => update("last_name", e.target.value)}
                className="input"
                placeholder="Doe"
              />
            </div>
          </div>

          <div>
            <label className="label" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={form.email}
              onChange={(e) => update("email", e.target.value)}
              className="input"
              placeholder="you@example.com"
            />
          </div>

          {isCustomer && (
            <>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="label" htmlFor="date_of_birth">
                    Date of birth
                  </label>
                  <input
                    id="date_of_birth"
                    type="date"
                    required
                    value={form.date_of_birth}
                    onChange={(e) => update("date_of_birth", e.target.value)}
                    className="input"
                  />
                  <p className="mt-1 text-xs text-slate-500">Your age is calculated from this.</p>
                </div>

                <div>
                  <label className="label" htmlFor="gender">
                    Gender
                  </label>
                  <select
                    id="gender"
                    value={form.gender}
                    onChange={(e) => update("gender", e.target.value)}
                    className="input"
                  >
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                  </select>
                  <p className="mt-1 text-xs text-slate-500">Used for BMR and body fat formulas.</p>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                {numberField("height_cm", "Height (cm)", "178", { min: 100, max: 250 })}
                {numberField("weight_kg", "Weight (kg)", "82.5", { min: 30, max: 250 })}
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                {numberField("waist_cm", "Waist (cm)", "92", { min: 40, max: 200 })}
                {numberField("neck_cm", "Neck (cm)", "39", { min: 20, max: 60 })}
                {numberField("hip_cm", "Hip (cm)", "96", {
                  min: 40,
                  max: 200,
                  required: false,
                })}
              </div>
              <p className="-mt-2 text-xs text-slate-500">
                Waist, neck and hip are used for your body fat estimate. Hip is only needed for
                women.
              </p>
            </>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor="password">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                minLength={8}
                value={form.password}
                onChange={(e) => update("password", e.target.value)}
                className="input"
                placeholder="At least 8 characters"
              />
            </div>
            <div>
              <label className="label" htmlFor="confirm">
                Confirm password
              </label>
              <input
                id="confirm"
                type="password"
                required
                value={form.confirm}
                onChange={(e) => update("confirm", e.target.value)}
                className="input"
              />
            </div>
          </div>
          <p className="-mt-2 text-xs text-slate-500">{PASSWORD_HINT}</p>

          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
            <h2 className="text-sm font-semibold text-amber-900">Medical disclaimer</h2>
            <p className="mt-2 text-xs leading-relaxed text-amber-800">
              {APP_NAME} provides general fitness and nutrition guidance only. It is not
              medical advice, diagnosis or treatment, and it is not a substitute for consulting a
              qualified healthcare professional. Talk to your doctor before starting any new
              exercise or diet programme, particularly if you have an existing medical condition,
              are pregnant, or are recovering from an injury. Stop immediately and seek medical
              help if you feel unwell.
            </p>
            <label className="mt-3 flex items-start gap-2 text-sm text-amber-900">
              <input
                type="checkbox"
                required
                checked={acceptedDisclaimer}
                onChange={(e) => setAcceptedDisclaimer(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-amber-400"
              />
              <span>I have read and accept this disclaimer.</span>
            </label>
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button type="submit" className="btn-primary w-full py-2.5" disabled={submitting}>
            {submitting ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-600">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-indigo-600 hover:underline">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}
