/**
 * Demo video script — scene definitions, timings, and narration text.
 *
 * Each scene describes what the viewer sees and what Gemini Live narrates.
 * The DemoPage orchestrator uses this data to auto-advance through the demo.
 */

export interface DemoScene {
  id: number
  title: string
  /** Which visual to render for this scene */
  visual: 'title' | 'landing' | 'story-templates' | 'story-setup' | 'story-playing' | 'tutor-intro' | 'tutor-live' | 'closing'
  /** Narration text sent to Gemini Live for TTS */
  narration: string
  /** Fallback duration in ms if narration finishes early or fails */
  fallbackDurationMs: number
  /** Extra delay after narration completes before advancing (ms) */
  postNarrationDelayMs: number
}

export const DEMO_SCENES: DemoScene[] = [
  {
    id: 1,
    title: 'Title & Introduction',
    visual: 'title',
    narration:
      'Welcome to StoryPal — an AI-powered storytelling companion designed to make learning magical for children ages one to eight.',
    fallbackDurationMs: 15000,
    postNarrationDelayMs: 2000,
  },
  {
    id: 2,
    title: 'Landing Page Overview',
    visual: 'landing',
    narration:
      'StoryPal combines three powerful features: AI Voice Stories that create personalized adventures, interactive voice games, and an age-appropriate AI tutor that answers children\'s curious questions. Let me show you how each one works.',
    fallbackDurationMs: 18000,
    postNarrationDelayMs: 1500,
  },
  {
    id: 3,
    title: 'Voice Story — Templates',
    visual: 'story-templates',
    narration:
      'Let\'s create a story! Parents can choose from beautifully designed templates — like a pirate adventure or a wizard quest — and customize it for their child\'s age, interests, and learning goals.',
    fallbackDurationMs: 18000,
    postNarrationDelayMs: 1500,
  },
  {
    id: 4,
    title: 'Voice Story — Setup & Generation',
    visual: 'story-setup',
    narration:
      'StoryPal uses Google Gemini to generate a complete story with multi-character dialogue, scene descriptions, and even comprehension questions — all personalized for your child. The generation progress is shown in real time.',
    fallbackDurationMs: 20000,
    postNarrationDelayMs: 1500,
  },
  {
    id: 5,
    title: 'Voice Story — Playback',
    visual: 'story-playing',
    narration:
      'Each story comes alive with AI-generated voice acting for every character, beautiful illustrations for each scene, and an immersive storybook mode. Children can listen, look at the pictures, and follow along with the narrative.',
    fallbackDurationMs: 22000,
    postNarrationDelayMs: 2000,
  },
  {
    id: 6,
    title: 'Tutor — Introduction',
    visual: 'tutor-intro',
    narration:
      'Now let\'s meet the AI Tutor. Powered by Gemini\'s Live API, it has real-time voice conversations with children, answering their questions in age-appropriate language.',
    fallbackDurationMs: 15000,
    postNarrationDelayMs: 1500,
  },
  {
    id: 7,
    title: 'Tutor — Live Demo',
    visual: 'tutor-live',
    narration:
      'Children simply speak their questions, and the tutor responds instantly with voice. Parents can send guidance to steer the conversation, and every session is transcribed and available for review.',
    fallbackDurationMs: 18000,
    postNarrationDelayMs: 2000,
  },
  {
    id: 8,
    title: 'Closing & Tech Stack',
    visual: 'closing',
    narration:
      'StoryPal is built entirely on Google\'s Gemini ecosystem — using Gemini for story generation, text-to-speech, image creation, and real-time voice interaction. Thank you for watching!',
    fallbackDurationMs: 15000,
    postNarrationDelayMs: 3000,
  },
]

/** Narrator system prompt for Gemini Live */
export const NARRATOR_SYSTEM_PROMPT =
  'You are a professional product demo narrator. Read the provided text naturally and engagingly in English. Do not add any extra commentary, greetings, or filler words — read exactly what is given to you, word for word. Speak at a clear, measured pace suitable for a product demo video.'

/** Default voice for narration */
export const NARRATOR_VOICE = 'Kore'

/** Default model for narration */
export const NARRATOR_MODEL = 'gemini-2.5-flash-native-audio-preview-12-2025'
