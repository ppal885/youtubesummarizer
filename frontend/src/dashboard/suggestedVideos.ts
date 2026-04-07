export type SuggestedVideo = {
  id: string
  title: string
  description: string
  url: string
  /** CSS background for card thumbnail area */
  thumbnailBackground: string
}

export const SUGGESTED_VIDEOS: SuggestedVideo[] = [
  {
    id: 'ted-stress',
    title: 'How stress affects your brain',
    description: 'TED-Ed explainer — strong structure for bullets and chapters.',
    url: 'https://www.youtube.com/watch?v=WuyPuA9KyCw',
    thumbnailBackground: 'linear-gradient(135deg, #8b5cf6, #c026d3)',
  },
  {
    id: 'veritasium-binary',
    title: 'How imaginary numbers were invented',
    description: 'Long-form narrative — good test for chunking and recall.',
    url: 'https://www.youtube.com/watch?v=cUzklzVXJwo',
    thumbnailBackground: 'linear-gradient(135deg, #0ea5e9, #1d4ed8)',
  },
  {
    id: '3b1b-neural',
    title: 'But what is a neural network?',
    description: '3Blue1Brown — technical summary mode shines here.',
    url: 'https://www.youtube.com/watch?v=aircAruvnKk',
    thumbnailBackground: 'linear-gradient(135deg, #10b981, #0f766e)',
  },
]
