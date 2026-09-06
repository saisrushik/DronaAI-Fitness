import { APP_NAME } from "../config/brand";

const suggestions = [
  "Swap barbell squats for a knee-friendly alternative",
  "Is my protein target high enough?",
  "Check my deadlift form cues",
  "I missed two workouts — what now?",
];

export default function ChatPage() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold">Chat Assistant</h1>
        <p className="mt-1 text-slate-600">
          Ask about form, swaps, nutrition or motivation — your plan and profile are the context.
        </p>
      </header>

      <div className="card flex h-[28rem] flex-col">
        <div className="flex-1 space-y-4 overflow-y-auto pr-1">
          <div className="flex justify-start">
            <p className="max-w-md rounded-2xl rounded-tl-sm bg-slate-100 px-4 py-2 text-sm">
              Hi! I&apos;m your {APP_NAME} assistant. Once the AI layer is connected I&apos;ll
              answer questions about your workouts and meals.
            </p>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {suggestions.map((text) => (
            <button key={text} className="btn-secondary text-xs" disabled>
              {text}
            </button>
          ))}
        </div>

        <form className="mt-4 flex gap-2">
          <input className="input" placeholder="Ask anything about your plan…" disabled />
          <button type="submit" className="btn-primary" disabled>
            Send
          </button>
        </form>
      </div>

      <p className="text-center text-sm text-slate-500">
        Chat components will be wired up when the AI agent layer is implemented.
      </p>
    </div>
  );
}
