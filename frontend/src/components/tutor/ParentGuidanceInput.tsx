/**
 * ParentGuidanceInput — Inline input for parents to send real-time guidance
 * to the AI during a live session.
 *
 * Messages are prefixed with [家長引導] and sent via Gemini's clientContent,
 * so the AI adjusts its behaviour without showing the guidance in the child's
 * conversation transcript.
 */

import { useState } from 'react'
import { MessageSquare, Send } from 'lucide-react'

interface ParentGuidanceInputProps {
  onSendGuidance: (text: string) => void
}

export function ParentGuidanceInput({ onSendGuidance }: ParentGuidanceInputProps) {
  const [text, setText] = useState('')

  const handleSend = () => {
    const trimmed = text.trim()
    if (!trimmed) return
    onSendGuidance(trimmed)
    setText('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="w-full rounded-lg border border-dashed border-muted-foreground/30 px-3 py-2">
      <div className="mb-1.5 flex items-center gap-1.5">
        <MessageSquare className="h-3.5 w-3.5 text-muted-foreground/60" />
        <span className="text-xs text-muted-foreground/60">家長引導</span>
      </div>
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="輸入引導文字，AI 會調整對話方向..."
          className="flex-1 bg-transparent text-sm text-muted-foreground outline-none placeholder:text-muted-foreground/40"
        />
        <button
          type="button"
          onClick={handleSend}
          disabled={!text.trim()}
          className="rounded-md p-1.5 text-muted-foreground/60 transition-colors hover:bg-muted hover:text-foreground disabled:opacity-30"
        >
          <Send className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  )
}
