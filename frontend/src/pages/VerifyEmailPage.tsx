import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";

export default function VerifyEmailPage() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const [status, setStatus] = useState<"working" | "done" | "failed">("working");
  const [message, setMessage] = useState("Verifying your email…");

  useEffect(() => {
    if (!token) {
      setStatus("failed");
      setMessage("This link is missing its verification token.");
      return;
    }
    api
      .post<{ message: string }>("/auth/verify-email", { token })
      .then((res) => {
        setStatus("done");
        setMessage(res.message);
      })
      .catch((err) => {
        setStatus("failed");
        setMessage(err instanceof Error ? err.message : "Verification failed");
      });
  }, [token]);

  return (
    <div className="mx-auto max-w-md">
      <div className="card text-center">
        <h1 className="text-2xl font-bold">Email verification</h1>
        <p
          className={`mt-4 text-sm ${
            status === "failed" ? "text-red-600" : status === "done" ? "text-emerald-600" : "text-slate-600"
          }`}
        >
          {message}
        </p>
        {status !== "working" && (
          <Link to="/login" className="btn-primary mt-6 inline-flex">
            Go to login
          </Link>
        )}
      </div>
    </div>
  );
}
