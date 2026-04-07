/** CSS linear-gradients for video card thumbnails (replaces Tailwind gradient classes). */
export const VIDEO_CARD_GRADIENTS = [
  'linear-gradient(135deg, #fb923c, #e11d48)',
  'linear-gradient(135deg, #fbbf24, #ea580c)',
  'linear-gradient(135deg, #06b6d4, #4f46e5)',
  'linear-gradient(135deg, #ec4899, #9333ea)',
  'linear-gradient(135deg, #84cc16, #047857)',
] as const

export function videoCardGradientForId(videoId: string): string {
  const n = videoId.split('').reduce((a, c) => a + c.charCodeAt(0), 0)
  return VIDEO_CARD_GRADIENTS[n % VIDEO_CARD_GRADIENTS.length]
}
