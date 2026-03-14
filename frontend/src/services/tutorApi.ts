/**
 * Tutor (適齡萬事通) API Service
 *
 * REST API client for Tutor v2v configuration and WebSocket URL helpers.
 * Separated from StoryPal — uses /api/v1/tutor prefix.
 */

import { api } from '../lib/api'

// =============================================================================
// Types
// =============================================================================

export interface TutorGame {
  id: string
  name: string
  description: string
  min_age: number
  max_age: number
}

export interface TutorV2vConfig {
  ws_url: string
  model: string
  voice: string
  available_voices: string[]
  system_prompt: string
  available_games: TutorGame[]
}

// =============================================================================
// WebSocket URL helpers
// =============================================================================

/** Build WebSocket URL for Gemini Live proxy (tutor v2v) */
export function getTutorLiveWsUrl(): string {
  const baseUrl = api.defaults.baseURL || '/api/v1'
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsBase = baseUrl.startsWith('http')
    ? baseUrl.replace(/^https?:/, wsProtocol)
    : `${wsProtocol}//${window.location.host}${baseUrl}`
  return `${wsBase}/tutor/live-ws`
}

// =============================================================================
// REST API
// =============================================================================

/** Fetch available games for a given child age */
export async function getTutorGames(childAge: number): Promise<TutorGame[]> {
  const response = await api.get<TutorGame[]>('/tutor/games', {
    params: { child_age: childAge },
  })
  return response.data
}

/** Fetch Gemini Live v2v config for US5 適齡萬事通 */
export async function getTutorV2vConfig(
  childAge: number,
  voice?: string,
  gameType?: string,
  language?: string
): Promise<TutorV2vConfig> {
  const params: Record<string, string | number> = { child_age: childAge }
  if (voice) params.voice = voice
  if (gameType) params.game_type = gameType
  if (language) params.language = language
  const response = await api.get<TutorV2vConfig>('/tutor/v2v-config', { params })
  return response.data
}
