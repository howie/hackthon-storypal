/**
 * StoryBookViewer Component Tests
 * Feature: 019-story-pixel-images (T035)
 *
 * Tests:
 *  - Renders empty state when no turns have images
 *  - Renders page content with image and text
 *  - Shows end page after last scene
 *  - Navigation buttons work (prev/next)
 *  - Page indicator displays correctly
 *  - Keyboard navigation (ArrowLeft, ArrowRight, Escape)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { StoryBookViewer } from '../StoryBookViewer'
import type { StoryTurn } from '@/types/storypal'

// Mock the api module
vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn().mockResolvedValue({
      data: new Blob(['fake-image'], { type: 'image/png' }),
    }),
  },
}))

vi.mock('@/services/storypalApi', () => ({
  getTurnImageUrl: vi.fn(
    (sessionId: string, turnId: string) =>
      `/api/v1/story/sessions/${sessionId}/turns/${turnId}/image`
  ),
}))

// Mock URL.createObjectURL/revokeObjectURL
const mockCreateObjectURL = vi.fn(() => 'blob:http://localhost/fake-blob-url')
const mockRevokeObjectURL = vi.fn()
Object.defineProperty(globalThis.URL, 'createObjectURL', { value: mockCreateObjectURL })
Object.defineProperty(globalThis.URL, 'revokeObjectURL', { value: mockRevokeObjectURL })

function makeTurn(overrides: Partial<StoryTurn> & { id: string }): StoryTurn {
  return {
    session_id: 's1',
    turn_number: 1,
    turn_type: 'narration',
    content: '故事內容',
    character_name: null,
    audio_path: null,
    image_path: null,
    scene_description: null,
    choice_options: null,
    child_choice: null,
    bgm_scene: null,
    created_at: new Date().toISOString(),
    ...overrides,
  }
}

describe('StoryBookViewer', () => {
  const mockOnExit = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('empty state', () => {
    it('renders empty state when no turns have images', () => {
      const turns = [
        makeTurn({ id: 't1', turn_number: 1 }),
        makeTurn({ id: 't2', turn_number: 2 }),
      ]

      render(
        <StoryBookViewer
          sessionId="s1"
          turns={turns}
          title="測試故事"
          onExit={mockOnExit}
        />
      )

      expect(screen.getByText('尚未生成場景圖片')).toBeInTheDocument()
    })

    it('shows return button in empty state', () => {
      const turns = [makeTurn({ id: 't1', turn_number: 1 })]

      render(
        <StoryBookViewer
          sessionId="s1"
          turns={turns}
          title="測試故事"
          onExit={mockOnExit}
        />
      )

      const returnBtn = screen.getByText('返回')
      expect(returnBtn).toBeInTheDocument()

      fireEvent.click(returnBtn)
      expect(mockOnExit).toHaveBeenCalled()
    })
  })

  describe('page rendering', () => {
    const turnsWithImages = [
      makeTurn({
        id: 't1',
        turn_number: 1,
        content: '小狐狸走進森林',
        image_path: 'stories/abc/image_001.png',
        scene_description: '森林入口',
      }),
      makeTurn({
        id: 't2',
        turn_number: 2,
        content: '他遇到了一隻小鹿',
        image_path: 'stories/abc/image_002.png',
        scene_description: '遇見小鹿',
      }),
      makeTurn({
        id: 't3',
        turn_number: 3,
        content: '一般對話（無圖）',
      }),
    ]

    it('renders title in header', () => {
      render(
        <StoryBookViewer
          sessionId="s1"
          turns={turnsWithImages}
          title="魔法森林"
          onExit={mockOnExit}
        />
      )

      expect(screen.getByText('魔法森林')).toBeInTheDocument()
    })

    it('shows page counter', () => {
      render(
        <StoryBookViewer
          sessionId="s1"
          turns={turnsWithImages}
          title="測試故事"
          onExit={mockOnExit}
        />
      )

      // 2 image pages + 1 end page = 3 total, starts at page 1
      expect(screen.getByText('1 / 3')).toBeInTheDocument()
    })

    it('renders story content text', () => {
      render(
        <StoryBookViewer
          sessionId="s1"
          turns={turnsWithImages}
          title="測試故事"
          onExit={mockOnExit}
        />
      )

      expect(screen.getByText('小狐狸走進森林')).toBeInTheDocument()
    })

    it('renders scene description', () => {
      render(
        <StoryBookViewer
          sessionId="s1"
          turns={turnsWithImages}
          title="測試故事"
          onExit={mockOnExit}
        />
      )

      expect(screen.getByText('森林入口')).toBeInTheDocument()
    })
  })

  describe('navigation', () => {
    const turnsWithImages = [
      makeTurn({
        id: 't1',
        turn_number: 1,
        content: '第一頁',
        image_path: 'stories/abc/image_001.png',
        scene_description: '場景一',
      }),
      makeTurn({
        id: 't2',
        turn_number: 2,
        content: '第二頁',
        image_path: 'stories/abc/image_002.png',
        scene_description: '場景二',
      }),
    ]

    it('navigates forward with next button', () => {
      render(
        <StoryBookViewer
          sessionId="s1"
          turns={turnsWithImages}
          title="測試故事"
          onExit={mockOnExit}
        />
      )

      // Initially on page 1
      expect(screen.getByText('第一頁')).toBeInTheDocument()

      // Click next
      fireEvent.click(screen.getByText('下一頁'))

      // Now on page 2
      expect(screen.getByText('第二頁')).toBeInTheDocument()
    })

    it('navigates backward with prev button', () => {
      render(
        <StoryBookViewer
          sessionId="s1"
          turns={turnsWithImages}
          title="測試故事"
          onExit={mockOnExit}
        />
      )

      // Go to page 2
      fireEvent.click(screen.getByText('下一頁'))
      expect(screen.getByText('第二頁')).toBeInTheDocument()

      // Go back to page 1
      fireEvent.click(screen.getByText('上一頁'))
      expect(screen.getByText('第一頁')).toBeInTheDocument()
    })

    it('disables prev button on first page', () => {
      render(
        <StoryBookViewer
          sessionId="s1"
          turns={turnsWithImages}
          title="測試故事"
          onExit={mockOnExit}
        />
      )

      const prevBtn = screen.getByText('上一頁').closest('button')
      expect(prevBtn).toBeDisabled()
    })

    it('shows end page after last image page', () => {
      render(
        <StoryBookViewer
          sessionId="s1"
          turns={turnsWithImages}
          title="測試故事"
          onExit={mockOnExit}
        />
      )

      // Navigate to page 2
      fireEvent.click(screen.getByText('下一頁'))
      // Navigate to end page
      fireEvent.click(screen.getByText('下一頁'))

      expect(screen.getByText('故事結束')).toBeInTheDocument()
    })

    it('end page shows return button that calls onExit', () => {
      render(
        <StoryBookViewer
          sessionId="s1"
          turns={turnsWithImages}
          title="測試故事"
          onExit={mockOnExit}
        />
      )

      // Navigate to end page
      fireEvent.click(screen.getByText('下一頁'))
      fireEvent.click(screen.getByText('下一頁'))

      fireEvent.click(screen.getByText('返回故事列表'))
      expect(mockOnExit).toHaveBeenCalled()
    })
  })

  describe('keyboard navigation', () => {
    const turnsWithImages = [
      makeTurn({
        id: 't1',
        turn_number: 1,
        content: '第一頁',
        image_path: 'stories/abc/image_001.png',
      }),
      makeTurn({
        id: 't2',
        turn_number: 2,
        content: '第二頁',
        image_path: 'stories/abc/image_002.png',
      }),
    ]

    it('ArrowRight navigates to next page', () => {
      render(
        <StoryBookViewer
          sessionId="s1"
          turns={turnsWithImages}
          title="測試故事"
          onExit={mockOnExit}
        />
      )

      expect(screen.getByText('第一頁')).toBeInTheDocument()

      fireEvent.keyDown(window, { key: 'ArrowRight' })

      expect(screen.getByText('第二頁')).toBeInTheDocument()
    })

    it('ArrowLeft navigates to previous page', () => {
      render(
        <StoryBookViewer
          sessionId="s1"
          turns={turnsWithImages}
          title="測試故事"
          onExit={mockOnExit}
        />
      )

      // Go forward first
      fireEvent.keyDown(window, { key: 'ArrowRight' })
      expect(screen.getByText('第二頁')).toBeInTheDocument()

      // Go back
      fireEvent.keyDown(window, { key: 'ArrowLeft' })
      expect(screen.getByText('第一頁')).toBeInTheDocument()
    })

    it('Escape calls onExit', () => {
      render(
        <StoryBookViewer
          sessionId="s1"
          turns={turnsWithImages}
          title="測試故事"
          onExit={mockOnExit}
        />
      )

      fireEvent.keyDown(window, { key: 'Escape' })
      expect(mockOnExit).toHaveBeenCalled()
    })
  })

  describe('header', () => {
    it('header return button calls onExit', () => {
      const turns = [
        makeTurn({
          id: 't1',
          turn_number: 1,
          image_path: 'stories/abc/image_001.png',
        }),
      ]

      render(
        <StoryBookViewer
          sessionId="s1"
          turns={turns}
          title="測試故事"
          onExit={mockOnExit}
        />
      )

      // Click the header "返回" button (first one)
      const returnButtons = screen.getAllByText('返回')
      fireEvent.click(returnButtons[0])
      expect(mockOnExit).toHaveBeenCalled()
    })
  })
})
