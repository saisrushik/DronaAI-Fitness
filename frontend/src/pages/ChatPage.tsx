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
        <h1 className="text-2xl font-bold sm:text-3xl">Chat Assistant</h1>
        <p className="mt-1 text-slate-600">
          Ask about form, swaps, nutrition or motivation — your plan and profile are the context.
        </p>
      </header>

      <div className="card flex h-[65dvh] min-h-[22rem] flex-col sm:h-[32rem]">
        <div className="flex-1 space-y-4 overflow-y-auto pr-1">
          <div className="flex justify-start">
            <p className="max-w-[85%] rounded-2xl rounded-tl-sm bg-slate-100 px-4 py-2 text-sm sm:max-w-md">
              Hi! I&apos;m your {APP_NAME} assistant. Once the AI layer is connected I&apos;ll
              answer questions about your workouts and meals.
            </p>
          </div>
        </div>

        <div className="-mx-1 mt-4 flex gap-2 overflow-x-auto px-1 pb-1 sm:flex-wrap sm:overflow-visible">
          {suggestions.map((text) => (
            <button key={text} className="btn-secondary shrink-0 text-xs" disabled>
              {text}
            </button>
          ))}
        </div>

        <form className="mt-4 flex gap-2">
          <input className="input" placeholder="Ask anything about your plan…" disabled />
          <button type="submit" className="btn-primary shrink-0" disabled>
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
