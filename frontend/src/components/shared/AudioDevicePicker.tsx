/**
 * AudioDevicePicker
 * Shared component — Audio device selection popover
 *
 * Gear icon button that opens a popover with mic/speaker device selection.
 * Speaker selection is hidden on browsers that don't support setSinkId (Safari).
 *
 * The popover is rendered via createPortal to document.body so it is never
 * clipped by ancestor overflow rules (e.g. AppLayout's overflow-hidden).
 */

import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Settings } from 'lucide-react'

import { useAudioDevices } from '@/hooks/useAudioDevices'
import { useSettingsStore } from '@/stores/settingsStore'

interface AudioDevicePickerProps {
  /** Popover 展開方向。'above' = 向上 (底部控制列)，'below' = 向下 (頂部 header) */
  popoverPosition?: 'above' | 'below'
}

export function AudioDevicePicker({ popoverPosition = 'above' }: AudioDevicePickerProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)

  const { inputDevices, outputDevices, supportsOutputSelection } = useAudioDevices()
  const audioInputDeviceId = useSettingsStore((s) => s.audioInputDeviceId)
  const audioOutputDeviceId = useSettingsStore((s) => s.audioOutputDeviceId)
  const setAudioInputDeviceId = useSettingsStore((s) => s.setAudioInputDeviceId)
  const setAudioOutputDeviceId = useSettingsStore((s) => s.setAudioOutputDeviceId)

  // Compute popover position when opening
  useEffect(() => {
    if (!isOpen || !triggerRef.current) return
    const rect = triggerRef.current.getBoundingClientRect()
    if (popoverPosition === 'below') {
      setPos({ top: rect.bottom + 8, left: rect.right - 288 })
    } else {
      setPos({ top: rect.top - 8, left: rect.right - 288 })
    }
  }, [isOpen, popoverPosition])

  // Close on outside click — check both trigger and panel
  useEffect(() => {
    if (!isOpen) return
    const handleMouseDown = (e: MouseEvent) => {
      const target = e.target as Node
      if (
        triggerRef.current &&
        !triggerRef.current.contains(target) &&
        panelRef.current &&
        !panelRef.current.contains(target)
      ) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleMouseDown)
    return () => document.removeEventListener('mousedown', handleMouseDown)
  }, [isOpen])

  return (
    <>
      <button
        ref={triggerRef}
        onClick={() => setIsOpen((v) => !v)}
        className="rounded-full p-2 text-muted-foreground hover:bg-muted hover:text-foreground"
        title="音訊裝置設定"
      >
        <Settings className="h-4 w-4" />
      </button>

      {isOpen &&
        pos &&
        createPortal(
          <div
            ref={panelRef}
            className="fixed z-50 w-72 rounded-lg border bg-popover p-3 shadow-lg"
            style={
              popoverPosition === 'below'
                ? { top: pos.top, left: pos.left }
                : { bottom: window.innerHeight - pos.top, left: pos.left }
            }
          >
            {/* Microphone */}
            <label className="mb-1 block text-xs font-medium text-muted-foreground">
              麥克風
            </label>
            <select
              value={audioInputDeviceId}
              onChange={(e) => setAudioInputDeviceId(e.target.value)}
              className="mb-3 w-full rounded-md border bg-background px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              <option value="">系統預設</option>
              {inputDevices.map((d) => (
                <option key={d.deviceId} value={d.deviceId}>
                  {d.label}
                </option>
              ))}
            </select>

            {/* Speaker — only shown when setSinkId is supported */}
            {supportsOutputSelection && (
              <>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">
                  喇叭
                </label>
                <select
                  value={audioOutputDeviceId}
                  onChange={(e) => setAudioOutputDeviceId(e.target.value)}
                  className="w-full rounded-md border bg-background px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                >
                  <option value="">系統預設</option>
                  {outputDevices.map((d) => (
                    <option key={d.deviceId} value={d.deviceId}>
                      {d.label}
                    </option>
                  ))}
                </select>
              </>
            )}
          </div>,
          document.body
        )}
    </>
  )
}
