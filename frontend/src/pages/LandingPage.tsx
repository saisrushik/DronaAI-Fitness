import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const features = [
  {
    title: "Personalized workouts",
    description: "Splits, exercises and progression built around your goal, schedule and injuries.",
  },
  {
    title: "Diet that fits you",
    description: "Meal plans that respect your calories, macros, allergies and food preferences.",
  },
  {
    title: "AI chat assistant",
    description: "Ask about form, swap an exercise, or get a nudge when motivation dips.",
  },
  {
    title: "Progress that adapts",
    description: "Log your week and your plan adjusts automatically to keep you moving forward.",
  },
];

const steps = [
  { step: "1", title: "Tell us about you", text: "Age, body stats, activity level and goal." },
  { step: "2", title: "Get your plan", text: "AI builds your workout and diet plan in seconds." },
  { step: "3", title: "Track and adapt", text: "Log progress weekly and the plan evolves." },
];

export default function LandingPage() {
  const { user } = useAuth();
  const homeLink = user?.role === "coach" ? "/customers" : "/workout-plan";

  return (
    <div className="space-y-12 sm:space-y-16">
      <section className="rounded-3xl bg-gradient-to-br from-indigo-600 to-violet-600 px-5 py-12 text-center text-white sm:px-12 sm:py-16">
        <p className="text-xs font-semibold uppercase tracking-widest text-indigo-200 sm:text-sm">
          AI-powered fitness
        </p>
        <h1 className="mx-auto mt-4 max-w-3xl text-3xl font-bold leading-tight sm:text-4xl lg:text-5xl">
          Your personal trainer and nutritionist, powered by AI
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-base text-indigo-100 sm:text-lg">
          Personalized workout and diet plans built from your body, your goals and your daily
          routine — explained, safe and always adapting.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          {user ? (
            <Link
              to={homeLink}
              className="btn bg-white px-6 py-3 text-indigo-700 hover:bg-indigo-50"
            >
              {user.role === "coach" ? "View my customers" : "View my plan"}
            </Link>
          ) : (
            <>
              <Link
                to="/register"
                className="btn bg-white px-6 py-3 text-indigo-700 hover:bg-indigo-50"
              >
                Get started free
              </Link>
              <Link
                to="/login"
                className="btn border border-white/40 px-6 py-3 text-white hover:bg-white/10"
              >
                Log in
              </Link>
            </>
          )}
        </div>
      </section>

      <section>
        <h2 className="text-center text-2xl font-bold sm:text-3xl">Everything you need to stay on track</h2>
        <div className="mt-6 grid gap-4 sm:mt-8 sm:grid-cols-2 sm:gap-5 lg:grid-cols-4">
          {features.map((feature) => (
            <article key={feature.title} className="card transition hover:-translate-y-1 hover:shadow-md">
              <h3 className="font-semibold text-slate-900">{feature.title}</h3>
              <p className="mt-2 text-sm text-slate-600">{feature.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-center text-2xl font-bold sm:text-3xl">How it works</h2>
        <div className="mt-6 grid gap-4 sm:mt-8 sm:gap-5 md:grid-cols-3">
          {steps.map((item) => (
            <article key={item.step} className="card text-center">
              <span className="mx-auto grid h-11 w-11 place-items-center rounded-full bg-indigo-600 text-lg font-bold text-white">
                {item.step}
              </span>
              <h3 className="mt-4 font-semibold text-slate-900">{item.title}</h3>
              <p className="mt-2 text-sm text-slate-600">{item.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="card flex flex-col items-center gap-4 text-center">
        <h2 className="text-2xl font-bold">Ready to start?</h2>
        <p className="max-w-xl text-slate-600">
          Create your profile and get your first personalized plan today.
        </p>
        <Link to={user ? homeLink : "/register"} className="btn-primary px-6 py-3">
          {user ? "Go to my dashboard" : "Create free account"}
        </Link>
      </section>
    </div>
  );
}
