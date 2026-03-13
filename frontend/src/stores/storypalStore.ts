/**
 * StoryPal State Store
 * Feature: StoryPal — AI Interactive Story Companion
 *
 * Zustand store for interactive story session state management.
 */

import axios from 'axios'
import { create } from 'zustand'

import * as storypalApi from '@/services/storypalApi'
import { useSettingsStore } from '@/stores/settingsStore'
import type {
  ChildConfig,
  CreateStorySessionRequest,
  GeneratedContent,
  SceneChangeData,
  StoryCategory,
  StoryCharacter,
  StoryDefaultsResponse,
  StoryJobStatus,
  StorySession,
  StorySessionStatus,
  StorySegmentData,
  SynthesisProgress,
  StoryTemplate,
  StoryTurn,
  StoryWSMessage,
  ChoicePromptData,
} from '@/types/storypal'

// Polling state (module-level to avoid closure issues)
let storyPollingInterval: ReturnType<typeof setInterval> | null = null
const STORY_POLL_INTERVAL_MS = 2000

let listPollingInterval: ReturnType<typeof setInterval> | null = null
const LIST_POLL_INTERVAL_MS = 3000

// =============================================================================
// State Interface
// =============================================================================

type StoryPlayState = 'idle' | 'loading' | 'playing' | 'waiting_choice' | 'listening' | 'paused' | 'ended'

interface StoryPalStoreState {
  // Templates
  templates: StoryTemplate[]
  selectedTemplate: StoryTemplate | null
  isLoadingTemplates: boolean

  // Session
  session: StorySession | null
  sessions: StorySession[]
  isLoadingSessions: boolean

  // Playback state
  playState: StoryPlayState
  turns: StoryTurn[]
  currentSegment: StorySegmentData | null

  // Scene & BGM
  currentScene: SceneChangeData | null
  bgmPlaying: boolean

  // Choice
  currentChoice: ChoicePromptData | null

  // Characters
  characters: StoryCharacter[]
  speakingCharacter: string | null

  // WebSocket
  ws: WebSocket | null
  isConnected: boolean

  // Settings
  language: string
  categoryFilter: StoryCategory | null

  // Child config
  childConfig: ChildConfig | null

  // Generated content
  generatedContents: GeneratedContent[]
  isGeneratingContent: boolean

  // Defaults
  defaults: StoryDefaultsResponse | null
  isLoadingDefaults: boolean

  // Static playback mode
  isGeneratingStory: boolean
  isSynthesizingAudio: boolean
  isGeneratingImages: boolean

  // Async job status
  jobStatus: StoryJobStatus | null
  synthesisProgress: SynthesisProgress
  imageGenerationProgress: SynthesisProgress

  // Error
  error: string | null
  isLoading: boolean

  // === Template Actions ===
  fetchTemplates: (params?: { category?: string; language?: string }) => Promise<void>
  selectTemplate: (template: StoryTemplate | null) => void

  // === Session Actions ===
  fetchSessions: (params?: { status?: StorySessionStatus }) => Promise<void>
  createSession: (request: CreateStorySessionRequest) => Promise<StorySession | null>
  loadSession: (sessionId: string) => Promise<void>
  selectSession: (sessionId: string) => Promise<void>
  deleteSession: (sessionId: string) => Promise<void>

  // === Static Playback Actions ===
  generateStory: (sessionId: string) => Promise<void>
  synthesizeAudio: (sessionId: string) => Promise<void>

  // === Async Job Actions ===
  triggerGenerateStory: (sessionId: string) => Promise<void>
  triggerSynthesizeAudio: (sessionId: string) => Promise<void>
  triggerGenerateImages: (sessionId: string) => Promise<void>
  startPollingStatus: (sessionId: string) => void
  stopPollingStatus: () => void

  // === WebSocket Actions ===
  connectWS: () => void
  disconnectWS: () => void
  sendStoryConfig: (config: {
    template_id?: string
    language: string
    characters_config?: StoryCharacter[]
  }) => void
  sendChoice: (choice: string) => void
  sendAudioChunk: (data: string) => void
  sendTextInput: (text: string) => void
  sendInterrupt: () => void

  // === Playback Actions ===
  setPlayState: (state: StoryPlayState) => void
  addTurn: (turn: StoryTurn) => void
  setCurrentSegment: (segment: StorySegmentData | null) => void
  setCurrentChoice: (choice: ChoicePromptData | null) => void
  setCurrentScene: (scene: SceneChangeData | null) => void
  setSpeakingCharacter: (name: string | null) => void
  setBgmPlaying: (playing: boolean) => void

  // === Child Config Actions ===
  setChildConfig: (config: ChildConfig | null) => void

  // === Generated Content Actions ===
  loadGeneratedContents: (sessionId: string) => Promise<void>
  generateSong: (sessionId: string) => Promise<GeneratedContent | null>
  generateQA: (sessionId: string) => Promise<GeneratedContent | null>
  generateInteractiveChoices: (sessionId: string) => Promise<GeneratedContent | null>

  // === Defaults Actions ===
  fetchDefaults: () => Promise<void>

  // === Settings Actions ===
  setLanguage: (language: string) => void
  setCategoryFilter: (category: StoryCategory | null) => void

  // === List Polling Actions ===
  triggerSessionSynthesis: (sessionId: string) => Promise<void>
  retrySessionGeneration: (sessionId: string) => Promise<void>
  retrySessionSynthesis: (sessionId: string) => Promise<void>
  startListPolling: () => void
  stopListPolling: () => void

  // === General Actions ===
  clearError: () => void
  reset: () => void
}

// =============================================================================
// Store Implementation
// =============================================================================

export const useStoryPalStore = create<StoryPalStoreState>((set, get) => ({
  // Initial state
  templates: [],
  selectedTemplate: null,
  isLoadingTemplates: false,
  session: null,
  sessions: [],
  isLoadingSessions: false,
  playState: 'idle',
  turns: [],
  currentSegment: null,
  currentScene: null,
  bgmPlaying: false,
  currentChoice: null,
  characters: [],
  speakingCharacter: null,
  ws: null,
  isConnected: false,
  childConfig: null,
  generatedContents: [],
  isGeneratingContent: false,
  defaults: null,
  isLoadingDefaults: false,
  language: 'zh-TW',
  categoryFilter: null,
  error: null,
  isLoading: false,
  isGeneratingStory: false,
  isSynthesizingAudio: false,
  isGeneratingImages: false,
  jobStatus: null,
  synthesisProgress: { completed: 0, total: 0 },
  imageGenerationProgress: { completed: 0, total: 0 },

  // === Template Actions ===
  fetchTemplates: async (params) => {
    set({ isLoadingTemplates: true, error: null })
    try {
      const response = await storypalApi.listTemplates(params)
      set({ templates: response.templates, isLoadingTemplates: false })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '載入故事範本失敗', isLoadingTemplates: false })
    }
  },

  selectTemplate: (template) => {
    set({
      selectedTemplate: template,
      characters: template?.characters ?? [],
    })
  },

  // === Session Actions ===
  fetchSessions: async (params) => {
    set({ isLoadingSessions: true, error: null })
    try {
      const response = await storypalApi.listSessions(params)
      set({ sessions: response.sessions, isLoadingSessions: false })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '載入故事列表失敗', isLoadingSessions: false })
    }
  },

  createSession: async (request) => {
    set({ isLoading: true, error: null })
    try {
      const response = await storypalApi.createSession(request)
      set({
        session: response,
        turns: response.turns ?? [],
        characters: response.characters_config ?? [],
        playState: 'loading',
        isLoading: false,
      })
      return response
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '建立故事失敗', isLoading: false })
      return null
    }
  },

  loadSession: async (sessionId) => {
    set({ isLoading: true, error: null })
    try {
      const response = await storypalApi.getSession(sessionId)
      set({
        session: response,
        turns: response.turns ?? [],
        characters: response.characters_config ?? [],
        playState: response.status === 'completed' ? 'ended' : 'paused',
        isLoading: false,
      })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '載入故事失敗', isLoading: false })
    }
  },

  selectSession: async (sessionId) => {
    set({ isLoadingSessions: true, error: null })
    try {
      const detail = await storypalApi.getSession(sessionId)
      set({
        session: detail,
        turns: detail.turns ?? [],
        characters: detail.characters_config ?? [],
        isLoadingSessions: false,
      })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '載入故事失敗', isLoadingSessions: false })
    }
  },

  deleteSession: async (sessionId) => {
    try {
      await storypalApi.deleteSession(sessionId)
      const { sessions } = get()
      set({ sessions: sessions.filter((s) => s.id !== sessionId) })
      if (get().session?.id === sessionId) {
        set({ session: null, turns: [], playState: 'idle' })
      }
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '刪除故事失敗' })
    }
  },

  // === Static Playback Actions ===
  generateStory: async (sessionId) => {
    set({ isGeneratingStory: true, error: null })
    try {
      const response = await storypalApi.generateStoryContent(sessionId)
      set({
        session: response,
        turns: response.turns ?? [],
        isGeneratingStory: false,
      })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '生成故事失敗', isGeneratingStory: false })
    }
  },

  synthesizeAudio: async (sessionId) => {
    set({ isSynthesizingAudio: true, error: null })
    try {
      const response = await storypalApi.synthesizeAudio(sessionId)
      set({
        session: response,
        turns: response.turns ?? [],
        isSynthesizingAudio: false,
      })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '合成音訊失敗', isSynthesizingAudio: false })
    }
  },

  // === Async Job Actions ===
  triggerGenerateStory: async (sessionId) => {
    set({ isGeneratingStory: true, error: null, jobStatus: null })
    try {
      const status = await storypalApi.triggerGenerateStory(sessionId)
      set({ jobStatus: status })
      get().startPollingStatus(sessionId)
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '觸發故事生成失敗', isGeneratingStory: false })
    }
  },

  triggerSynthesizeAudio: async (sessionId) => {
    set({ isSynthesizingAudio: true, error: null, synthesisProgress: { completed: 0, total: 0 } })
    try {
      const status = await storypalApi.triggerSynthesizeAudio(sessionId)
      set({ jobStatus: status, synthesisProgress: status.synthesis_progress })
      get().startPollingStatus(sessionId)
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '觸發音訊合成失敗', isSynthesizingAudio: false })
    }
  },

  triggerGenerateImages: async (sessionId) => {
    set({ isGeneratingImages: true, imageGenerationProgress: { completed: 0, total: 0 } })
    try {
      const status = await storypalApi.triggerGenerateImages(sessionId)
      set({
        jobStatus: status,
        imageGenerationProgress: status.image_generation_progress ?? { completed: 0, total: 0 },
      })
      get().startPollingStatus(sessionId)
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '觸發圖片生成失敗', isGeneratingImages: false })
    }
  },

  startPollingStatus: (sessionId) => {
    if (storyPollingInterval) clearInterval(storyPollingInterval)
    storyPollingInterval = setInterval(async () => {
      try {
        const status = await storypalApi.getSessionStatus(sessionId)
        const prev = useStoryPalStore.getState().jobStatus
        set({
          jobStatus: status,
          synthesisProgress: status.synthesis_progress,
          imageGenerationProgress: status.image_generation_progress ?? { completed: 0, total: 0 },
        })

        // Generation completed → reload session (to get turns), stop polling
        if (status.generation_status === 'completed' && prev?.generation_status !== 'completed') {
          set({ isGeneratingStory: false })
          await get().loadSession(sessionId)
          // Don't stop polling yet — image generation may still be pending
        }
        if (status.generation_status === 'failed') {
          set({ isGeneratingStory: false, error: status.generation_error ?? '生成故事失敗' })
          get().stopPollingStatus()
          return
        }

        // Synthesis completed → reload session (to get audio_path)
        if (status.synthesis_status === 'completed' && prev?.synthesis_status !== 'completed') {
          set({ isSynthesizingAudio: false })
          await get().loadSession(sessionId)
          // Verify actual audio output exists
          if (status.audio_ready_count === 0 && status.turns_count > 0) {
            set({ error: status.synthesis_error || '音訊合成完成但沒有音檔產生，請重試' })
          }
        }
        if (status.synthesis_status === 'failed') {
          set({ isSynthesizingAudio: false, error: status.synthesis_error ?? '合成音訊失敗' })
        }

        // Image generation completed
        if (status.image_generation_status === 'completed' && prev?.image_generation_status !== 'completed') {
          set({ isGeneratingImages: false })
          await get().loadSession(sessionId)
        }
        if (status.image_generation_status === 'failed') {
          set({ isGeneratingImages: false })
          // Image failure is non-blocking — only log, don't set error
        }

        // Stop polling when all active jobs are done
        const isDone = (s: string | null | undefined) => !s || s === 'completed' || s === 'failed'
        if (isDone(status.generation_status) && isDone(status.synthesis_status) && isDone(status.image_generation_status)) {
          get().stopPollingStatus()
        }
      } catch (err) {
        // 404 = session deleted/not found → stop polling permanently
        if (axios.isAxiosError(err) && err.response?.status === 404) {
          get().stopPollingStatus()
          return
        }
        // Other errors (network, 5xx) — silently ignore, next poll will retry
      }
    }, STORY_POLL_INTERVAL_MS)
  },

  stopPollingStatus: () => {
    if (storyPollingInterval) {
      clearInterval(storyPollingInterval)
      storyPollingInterval = null
    }
  },

  // === WebSocket Actions ===
  connectWS: () => {
    const { ws } = get()
    if (ws && ws.readyState !== WebSocket.CLOSED) {
      return
    }
    if (ws) ws.close()

    const token = localStorage.getItem('auth_token')
    const url = storypalApi.getStoryWSUrl() + (token ? `?token=${token}` : '')
    const socket = new WebSocket(url)

    socket.onopen = () => {
      if (get().ws !== socket) return
      set({ isConnected: true, error: null })
    }

    socket.onclose = () => {
      if (get().ws !== socket) return
      set({ isConnected: false, ws: null })
    }

    socket.onerror = () => {
      if (get().ws !== socket) return
      if (socket.readyState !== WebSocket.CLOSED) {
        socket.close()
      }
      set({ error: '故事連線失敗', isConnected: false, ws: null })
    }

    socket.onmessage = (event) => {
      if (get().ws !== socket) return
      try {
        const msg: StoryWSMessage = JSON.parse(event.data)
        handleWSMessage(msg, set, get)
      } catch {
        // Ignore parse errors
      }
    }

    set({ ws: socket })
  },

  disconnectWS: () => {
    const { ws } = get()
    if (ws) {
      ws.onopen = null
      ws.onclose = null
      ws.onerror = null
      ws.onmessage = null
      if (ws.readyState !== WebSocket.CLOSING && ws.readyState !== WebSocket.CLOSED) {
        ws.close()
      }
      set({ ws: null, isConnected: false })
    }
  },

  sendStoryConfig: (config) => {
    const { ws } = get()
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'story_configure', data: config }))
      set({ playState: 'loading' })
    }
  },

  sendChoice: (choice) => {
    const { ws } = get()
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'story_choice', data: { choice } }))
      set({ currentChoice: null, playState: 'loading' })
    }
  },

  sendAudioChunk: (data) => {
    const { ws } = get()
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'audio_chunk', data: { audio: data } }))
    }
  },

  sendTextInput: (text) => {
    const { ws } = get()
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'text_input', data: { text } }))
      set({ playState: 'loading' })
    }
  },

  sendInterrupt: () => {
    const { ws } = get()
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'interrupt', data: {} }))
    }
  },

  // === Playback Actions ===
  setPlayState: (state) => set({ playState: state }),
  addTurn: (turn) => set((s) => ({ turns: [...s.turns, turn] })),
  setCurrentSegment: (segment) => set({ currentSegment: segment }),
  setCurrentChoice: (choice) => set({ currentChoice: choice, playState: choice ? 'waiting_choice' : get().playState }),
  setCurrentScene: (scene) => set({ currentScene: scene }),
  setSpeakingCharacter: (name) => set({ speakingCharacter: name }),
  setBgmPlaying: (playing) => set({ bgmPlaying: playing }),

  // === Child Config Actions ===
  setChildConfig: (config) => set({ childConfig: config }),

  // === Generated Content Actions ===
  loadGeneratedContents: async (sessionId) => {
    try {
      const response = await storypalApi.getGeneratedContents(sessionId)
      // Response only contains summaries; store them as partial GeneratedContent
      set({
        generatedContents: response.contents.map((c) => ({
          ...c,
          session_id: response.session_id,
          content_data: {} as GeneratedContent['content_data'],
        })),
      })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '載入生成內容失敗' })
    }
  },

  generateSong: async (sessionId) => {
    set({ isGeneratingContent: true, error: null })
    try {
      const content = await storypalApi.generateSong(sessionId)
      set((s) => ({
        generatedContents: [...s.generatedContents, content],
        isGeneratingContent: false,
      }))
      return content
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '生成兒歌失敗', isGeneratingContent: false })
      return null
    }
  },

  generateQA: async (sessionId) => {
    set({ isGeneratingContent: true, error: null })
    try {
      const content = await storypalApi.generateQA(sessionId)
      set((s) => ({
        generatedContents: [...s.generatedContents, content],
        isGeneratingContent: false,
      }))
      return content
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '生成 Q&A 失敗', isGeneratingContent: false })
      return null
    }
  },

  generateInteractiveChoices: async (sessionId) => {
    set({ isGeneratingContent: true, error: null })
    try {
      const content = await storypalApi.generateInteractiveChoices(sessionId)
      set((s) => ({
        generatedContents: [...s.generatedContents, content],
        isGeneratingContent: false,
      }))
      return content
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '生成互動選擇失敗', isGeneratingContent: false })
      return null
    }
  },

  // === Defaults Actions ===
  fetchDefaults: async () => {
    set({ isLoadingDefaults: true })
    try {
      const defaults = await storypalApi.getDefaults()
      set({ defaults, isLoadingDefaults: false })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '載入預設資料失敗', isLoadingDefaults: false })
    }
  },

  // === Settings Actions ===
  setLanguage: (language) => set({ language }),
  setCategoryFilter: (category) => set({ categoryFilter: category }),

  // === List Polling Actions ===
  triggerSessionSynthesis: async (sessionId) => {
    try {
      await storypalApi.triggerSynthesizeAudio(sessionId)
      await get().fetchSessions()
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '合成音訊失敗' })
    }
  },

  retrySessionGeneration: async (sessionId) => {
    try {
      await storypalApi.triggerGenerateStory(sessionId)
      await get().fetchSessions()
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '重試生成失敗' })
    }
  },

  retrySessionSynthesis: async (sessionId) => {
    try {
      await storypalApi.triggerSynthesizeAudio(sessionId)
      await get().fetchSessions()
    } catch (err) {
      set({ error: err instanceof Error ? err.message : '重試合成失敗' })
    }
  },

  startListPolling: () => {
    if (listPollingInterval) return
    listPollingInterval = setInterval(async () => {
      await get().fetchSessions()
      const hasInProgress = get().sessions.some((s) => {
        const state = s.story_state
        return state.generation_status === 'generating' || state.synthesis_status === 'synthesizing'
      })
      if (!hasInProgress) get().stopListPolling()
    }, LIST_POLL_INTERVAL_MS)
  },

  stopListPolling: () => {
    if (listPollingInterval) {
      clearInterval(listPollingInterval)
      listPollingInterval = null
    }
  },

  // === General Actions ===
  clearError: () => set({ error: null }),
  reset: () => {
    const { ws } = get()
    if (ws) ws.close()
    get().stopListPolling()
    get().stopPollingStatus()
    set({
      session: null,
      turns: [],
      playState: 'idle',
      currentSegment: null,
      currentScene: null,
      currentChoice: null,
      speakingCharacter: null,
      bgmPlaying: false,
      ws: null,
      isConnected: false,
      childConfig: null,
      generatedContents: [],
      isGeneratingContent: false,
      jobStatus: null,
      synthesisProgress: { completed: 0, total: 0 },
      imageGenerationProgress: { completed: 0, total: 0 },
      isGeneratingImages: false,
      error: null,
    })
  },
}))

// =============================================================================
// WebSocket Message Handler
// =============================================================================

type SetFn = (partial: Partial<StoryPalStoreState> | ((state: StoryPalStoreState) => Partial<StoryPalStoreState>)) => void
type GetFn = () => StoryPalStoreState

function handleWSMessage(msg: StoryWSMessage, set: SetFn, _get: GetFn) {
  switch (msg.type) {
    case 'story_segment': {
      const segment = msg.data as unknown as StorySegmentData
      set((s) => ({
        currentSegment: segment,
        playState: 'playing',
        speakingCharacter: segment.character_name,
        turns: [
          ...s.turns,
          {
            id: `ws-${Date.now()}-${s.turns.length}`,
            session_id: s.session?.id ?? '',
            turn_number: s.turns.length + 1,
            turn_type: segment.turn_type ?? 'narration',
            character_name: segment.character_name ?? null,
            content: segment.content,
            audio_path: null,
            choice_options: null,
            child_choice: null,
            bgm_scene: null,
            created_at: new Date().toISOString(),
          } as StoryTurn,
        ],
      }))
      // Play TTS audio if available
      if (segment.audio) {
        const { audioOutputDeviceId } = useSettingsStore.getState()
        const audio = new Audio(`data:audio/${segment.audio_format ?? 'mp3'};base64,${segment.audio}`)
        const playAudio = () => {
          audio.play().catch((err: DOMException) => {
            console.warn('[StoryPal] Audio playback failed:', err.name, err.message)
          })
        }
        if ('setSinkId' in audio) {
          void (audio as HTMLAudioElement & { setSinkId(id: string): Promise<void> })
            .setSinkId(audioOutputDeviceId)
            .then(playAudio)
            .catch((err: Error) => {
              console.warn('[StoryPal] setSinkId failed, using default:', err.message)
              playAudio()
            })
        } else {
          playAudio()
        }
      } else {
        console.warn('[StoryPal] No audio in segment, text-only mode')
      }
      break
    }

    case 'choice_prompt': {
      const choice = msg.data as unknown as ChoicePromptData
      set({ currentChoice: choice, playState: 'waiting_choice' })
      break
    }

    case 'scene_change': {
      const scene = msg.data as unknown as SceneChangeData
      set({ currentScene: scene })
      break
    }

    case 'audio': {
      // Audio chunk handled by audio playback hook
      break
    }

    case 'story_end': {
      set({ playState: 'ended' })
      break
    }

    case 'error': {
      const errorMsg = (msg.data as { message?: string }).message ?? '故事發生錯誤'
      set({ error: errorMsg })
      break
    }
  }
}
