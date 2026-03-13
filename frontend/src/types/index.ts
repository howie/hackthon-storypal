// Provider types (simplified for StoryPal - Gemini only)
export type TTSProvider = 'gemini' | 'gemini-flash' | 'gemini-pro'
export type LLMProvider = 'gemini'

export type TestType = 'tts' | 'interaction'

// TTS types
export interface TTSRequest {
  text: string
  provider: TTSProvider
  voice_id: string
  language?: string
  speed?: number
  pitch?: number
  volume?: number
  output_format?: 'mp3' | 'wav' | 'opus'
}

export interface TTSResponse {
  audio_url: string
  duration_ms: number
  latency_ms: number
  cost_estimate: number
  provider: string
  voice_id: string
  format: string
}

// Interaction types
export interface InteractionConfig {
  tts_provider: TTSProvider
  llm_provider: LLMProvider
  voice_id: string
  system_prompt?: string
  language?: string
}

export interface InteractionResponse {
  user_transcript: string
  ai_text: string
  ai_audio_url: string
  tts_latency_ms: number
  llm_latency_ms: number
  total_latency_ms: number
}
