/** Lightweight inline SVGs (no external assets). */

export function VideoLibraryIllustration({ className = '' }: { className?: string }) {
  return (
    <svg
      className={className}
      style={{ width: '100%', height: 'auto', maxWidth: '100%' }}
      viewBox="0 0 200 140"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <defs>
        <linearGradient id="es-vid-a" x1="32" y1="24" x2="168" y2="116" gradientUnits="userSpaceOnUse">
          <stop stopColor="#22d3ee" stopOpacity="0.35" />
          <stop offset="1" stopColor="#6366f1" stopOpacity="0.25" />
        </linearGradient>
        <linearGradient id="es-vid-b" x1="70" y1="48" x2="130" y2="92" gradientUnits="userSpaceOnUse">
          <stop stopColor="#0ea5e9" />
          <stop offset="1" stopColor="#4f46e5" />
        </linearGradient>
      </defs>
      <rect x="20" y="16" width="160" height="108" rx="14" fill="url(#es-vid-a)" stroke="#e2e8f0" strokeWidth="1.5" />
      <rect x="44" y="36" width="112" height="68" rx="8" fill="white" fillOpacity="0.9" />
      <circle cx="100" cy="70" r="18" fill="url(#es-vid-b)" opacity="0.9" />
      <path d="M96 62l14 8-14 8V62z" fill="white" />
      <rect x="36" y="118" width="48" height="6" rx="3" fill="#cbd5e1" />
      <rect x="92" y="118" width="72" height="6" rx="3" fill="#e2e8f0" />
    </svg>
  )
}

export function ChatThreadsIllustration({ className = '' }: { className?: string }) {
  return (
    <svg
      className={className}
      style={{ width: '100%', height: 'auto', maxWidth: '100%' }}
      viewBox="0 0 200 140"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <defs>
        <linearGradient id="es-chat-a" x1="40" y1="28" x2="160" y2="112" gradientUnits="userSpaceOnUse">
          <stop stopColor="#a5b4fc" stopOpacity="0.4" />
          <stop offset="1" stopColor="#67e8f9" stopOpacity="0.35" />
        </linearGradient>
      </defs>
      <rect x="24" y="20" width="152" height="100" rx="16" fill="url(#es-chat-a)" stroke="#e2e8f0" strokeWidth="1.5" />
      <rect x="44" y="36" width="96" height="22" rx="10" fill="#f1f5f9" stroke="#e2e8f0" />
      <rect x="60" y="66" width="112" height="26" rx="12" fill="#0f172a" fillOpacity="0.88" />
      <rect x="44" y="100" width="72" height="20" rx="10" fill="#e2e8f0" />
      <circle cx="54" cy="47" r="4" fill="#94a3b8" />
      <circle cx="66" cy="47" r="4" fill="#cbd5e1" />
    </svg>
  )
}
