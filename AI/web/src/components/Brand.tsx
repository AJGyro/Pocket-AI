export function Brand({ word = false }: { word?: boolean }) {
  return (
    <span className={word ? "colibri-brand full" : "colibri-brand"} aria-label="Pocket AI">
      <svg viewBox="0 0 40 40" aria-hidden="true" fill="none" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="pocketAiGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#8b5cf6" />
            <stop offset="50%" stopColor="#3b82f6" />
            <stop offset="100%" stopColor="#06b6d4" />
          </linearGradient>
        </defs>
        <rect width="40" height="40" rx="10" fill="url(#pocketAiGrad)" />
        <path
          d="M12 11h16a2 2 0 0 1 2 2v9a8 8 0 0 1-8 8h-4a8 8 0 0 1-8-8v-9a2 2 0 0 1 2-2z"
          fill="rgba(255,255,255,0.2)"
          stroke="#ffffff"
          strokeWidth="2.2"
          strokeLinejoin="round"
        />
        <path d="M16 16h8M16 20h8M20 20v6" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" />
        <circle cx="20" cy="26" r="1.5" fill="#38bdf8" />
      </svg>
      {word && (
        <span
          className="colibri-word"
          style={{
            fontFamily: "Inter, system-ui, sans-serif",
            fontSize: "44px",
            fontWeight: 800,
            letterSpacing: "-0.03em",
            background: "linear-gradient(135deg, #a78bfa 0%, #38bdf8 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          Pocket AI
        </span>
      )}
    </span>
  )
}
