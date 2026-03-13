/**
 * StoryPal API Service
 * Feature: StoryPal — AI Interactive Story Companion
 *
 * REST API client for story session and template management.
 */

import { api } from '../lib/api'
import type {
  CreateStorySessionRequest,
  GeneratedContent,
  GeneratedContentListResponse,
  StoryDefaultsResponse,
  StoryImage,
  StoryJobStatus,
  StorySessionListParams,
  StorySessionListResponse,
  StorySessionResponse,
  StoryTemplate,
  StoryTemplateListResponse,
  StoryTurn,
} from '../types/storypal'

// =============================================================================
// Template Endpoints
// =============================================================================

/** List available story templates */
export async function listTemplates(params?: {
  category?: string
  language?: string
}): Promise<StoryTemplateListResponse> {
  const response = await api.get<StoryTemplateListResponse>('/story/templates', { params })
  return response.data
}

/** Get template details by ID */
export async function getTemplate(templateId: string): Promise<StoryTemplate> {
  const response = await api.get<StoryTemplate>(`/story/templates/${templateId}`)
  return response.data
}

// =============================================================================
// Session Endpoints
// =============================================================================

/** Start a new story session */
export async function createSession(
  request: CreateStorySessionRequest
): Promise<StorySessionResponse> {
  const response = await api.post<StorySessionResponse>('/story/sessions', request)
  return response.data
}

/** List story sessions for the current user */
export async function listSessions(
  params?: StorySessionListParams
): Promise<StorySessionListResponse> {
  const response = await api.get<StorySessionListResponse>('/story/sessions', { params })
  return response.data
}

/** Get session details with turns */
export async function getSession(sessionId: string): Promise<StorySessionResponse> {
  const response = await api.get<StorySessionResponse>(`/story/sessions/${sessionId}`)
  return response.data
}

/** Resume a paused session */
export async function resumeSession(sessionId: string): Promise<StorySessionResponse> {
  const response = await api.post<StorySessionResponse>(`/story/sessions/${sessionId}/resume`)
  return response.data
}

/** Delete/end a story session */
export async function deleteSession(sessionId: string): Promise<void> {
  await api.delete(`/story/sessions/${sessionId}`)
}

// =============================================================================
// Generated Content Endpoints
// =============================================================================

/** Generate a themed song for a session */
export async function generateSong(sessionId: string): Promise<GeneratedContent> {
  const response = await api.post<GeneratedContent>(`/story/sessions/${sessionId}/song`)
  return response.data
}

/** Generate Q&A content for a session */
export async function generateQA(sessionId: string): Promise<GeneratedContent> {
  const response = await api.post<GeneratedContent>(`/story/sessions/${sessionId}/qa`)
  return response.data
}

/** Generate interactive choices content for a session */
export async function generateInteractiveChoices(
  sessionId: string
): Promise<GeneratedContent> {
  const response = await api.post<GeneratedContent>(
    `/story/sessions/${sessionId}/interactive-choices`
  )
  return response.data
}

/** List all generated contents for a session */
export async function getGeneratedContents(
  sessionId: string
): Promise<GeneratedContentListResponse> {
  const response = await api.get<GeneratedContentListResponse>(
    `/story/sessions/${sessionId}/content`
  )
  return response.data
}

/** Get a specific generated content by ID */
export async function getGeneratedContent(
  sessionId: string,
  contentId: string
): Promise<GeneratedContent> {
  const response = await api.get<GeneratedContent>(
    `/story/sessions/${sessionId}/content/${contentId}`
  )
  return response.data
}

// =============================================================================
// Static Playback Endpoints (純播放模式)
// =============================================================================

/** Generate complete story content (non-interactive) */
export async function generateStoryContent(sessionId: string): Promise<StorySessionResponse> {
  const response = await api.post<StorySessionResponse>(
    `/story/sessions/${sessionId}/generate`
  )
  return response.data
}

/** Synthesize audio for all story turns */
export async function synthesizeAudio(sessionId: string): Promise<StorySessionResponse> {
  const response = await api.post<StorySessionResponse>(
    `/story/sessions/${sessionId}/synthesize`
  )
  return response.data
}

/** Trigger async story generation (returns immediately, poll status) */
export async function triggerGenerateStory(sessionId: string): Promise<StoryJobStatus> {
  const response = await api.post<StoryJobStatus>(`/story/sessions/${sessionId}/generate`)
  return response.data
}

/** Trigger async audio synthesis (returns immediately, poll status) */
export async function triggerSynthesizeAudio(sessionId: string): Promise<StoryJobStatus> {
  const response = await api.post<StoryJobStatus>(`/story/sessions/${sessionId}/synthesize`)
  return response.data
}

/** Get current session job status (generation/synthesis progress) */
export async function getSessionStatus(sessionId: string): Promise<StoryJobStatus> {
  const response = await api.get<StoryJobStatus>(`/story/sessions/${sessionId}/status`)
  return response.data
}

/** Get audio URL for a specific turn (API-relative path for use with axios) */
export function getTurnAudioUrl(sessionId: string, turnId: string): string {
  return `/story/sessions/${sessionId}/turns/${turnId}/audio`
}

/** Get download URL for full session audio (all turns concatenated) */
export function getSessionAudioDownloadUrl(sessionId: string): string {
  return `/story/sessions/${sessionId}/audio/download`
}

/** Update the text content of a specific story turn */
export async function updateTurnContent(
  sessionId: string,
  turnId: string,
  content: string
): Promise<StoryTurn> {
  const response = await api.patch<StoryTurn>(
    `/story/sessions/${sessionId}/turns/${turnId}`,
    { content }
  )
  return response.data
}

// =============================================================================
// Image Generation Endpoints (019-story-pixel-images)
// =============================================================================

/** Trigger async image generation (returns immediately, poll status) */
export async function triggerGenerateImages(sessionId: string): Promise<StoryJobStatus> {
  const response = await api.post<StoryJobStatus>(
    `/story/sessions/${sessionId}/generate-images`
  )
  return response.data
}

/** Get all scene images for a story session */
export async function getSessionImages(
  sessionId: string
): Promise<{ images: StoryImage[] }> {
  const response = await api.get<{ images: StoryImage[] }>(
    `/story/sessions/${sessionId}/images`
  )
  return response.data
}

/** Get image URL for a specific turn (API-relative path for use with axios) */
export function getTurnImageUrl(sessionId: string, turnId: string): string {
  return `/story/sessions/${sessionId}/turns/${turnId}/image`
}

// =============================================================================
// Defaults Endpoint
// =============================================================================

/** Get default values for the story setup form */
export async function getDefaults(): Promise<StoryDefaultsResponse> {
  const response = await api.get<StoryDefaultsResponse>('/story/defaults')
  return response.data
}

// =============================================================================
// WebSocket URL helpers
// =============================================================================

/** Build WebSocket URL for story interaction */
export function getStoryWSUrl(): string {
  const baseUrl = api.defaults.baseURL || '/api/v1'
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsBase = baseUrl.startsWith('http')
    ? baseUrl.replace(/^https?:/, wsProtocol)
    : `${wsProtocol}//${window.location.host}${baseUrl}`
  return `${wsBase}/story/ws`
}
