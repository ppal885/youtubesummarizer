import type { CSSProperties } from 'react'
import { useId } from 'react'

export type ProductIconVariant = 'full' | 'glyph'

type Props = {
  /** Pixel width and height (square). */
  size?: number
  /** `full` = badge with gradient plate; `glyph` = inner mark only (use on colored buttons / `currentColor`). */
  variant?: ProductIconVariant
  /** Accessible label; set when the icon is not decorative. */
  title?: string
  className?: string
  style?: CSSProperties
}

/**
 * Enterprise product mark: structured transcript bars + play control on a disciplined plate,
 * or glyph-only for app chrome on accent backgrounds.
 */
export function ProductIcon({
  size = 32,
  variant = 'full',
  title,
  className,
  style,
}: Props) {
  const uid = useId().replace(/:/g, '')
  const bg = `yc-bg-${uid}`
  const hi = `yc-hi-${uid}`
  const decorative = title == null
  const fill = variant === 'glyph' ? 'currentColor' : '#f1f5f9'

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      className={className}
      style={style}
      role={decorative ? 'presentation' : 'img'}
      aria-hidden={decorative}
      {...(title ? { 'aria-label': title } : {})}
    >
      {title ? <title>{title}</title> : null}
      {variant === 'full' ? (
        <>
          <defs>
            <linearGradient id={bg} x1="6" y1="2" x2="26" y2="32" gradientUnits="userSpaceOnUse">
              <stop stopColor="#0c1e33" />
              <stop offset="0.45" stopColor="#153a5c" />
              <stop offset="1" stopColor="#1a5f8f" />
            </linearGradient>
            <linearGradient id={hi} x1="16" y1="0" x2="16" y2="14" gradientUnits="userSpaceOnUse">
              <stop stopColor="#ffffff" stopOpacity="0.2" />
              <stop offset="1" stopColor="#ffffff" stopOpacity="0" />
            </linearGradient>
          </defs>
          <rect width="32" height="32" rx="8" fill={`url(#${bg})`} />
          <rect width="32" height="32" rx="8" fill={`url(#${hi})`} />
          <rect
            x="0.5"
            y="0.5"
            width="31"
            height="31"
            rx="7.5"
            fill="none"
            stroke="#ffffff"
            strokeOpacity={0.18}
            strokeWidth={1}
          />
        </>
      ) : null}

      <g fill={fill}>
        <rect x="6" y="9.5" width="9.5" height="2.5" rx="1.25" />
        <rect x="6" y="14.25" width="7.5" height="2.5" rx="1.25" opacity={variant === 'glyph' ? 0.9 : 0.92} />
        <rect x="6" y="19" width="8.5" height="2.5" rx="1.25" opacity={variant === 'glyph' ? 0.78 : 0.82} />
      </g>

      <path
        fill={variant === 'glyph' ? 'currentColor' : '#f8fafc'}
        d="M17.2 10.4V21.6L26.4 16 17.2 10.4z"
      />

      {variant === 'full' ? (
        <rect x="6" y="25.25" width="20" height="2" rx="1" fill="#38bdf8" fillOpacity={0.9} />
      ) : (
        <rect x="6" y="25.25" width="20" height="2" rx="1" fill="currentColor" opacity={0.45} />
      )}
    </svg>
  )
}
