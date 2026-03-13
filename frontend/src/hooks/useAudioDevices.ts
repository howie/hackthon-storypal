/**
 * Audio Devices hook — enumerates available audio input/output devices.
 * Feature: StoryPal — Audio device picker
 *
 * Handles permission-gated labels, devicechange events (Bluetooth pair/unpair),
 * and detects setSinkId support for output device selection.
 */

import { useCallback, useEffect, useRef, useState } from 'react'

export interface AudioDeviceInfo {
  deviceId: string
  label: string
  kind: MediaDeviceKind
}

export interface UseAudioDevicesReturn {
  inputDevices: AudioDeviceInfo[]
  outputDevices: AudioDeviceInfo[]
  isLoading: boolean
  supportsOutputSelection: boolean
  refresh: () => Promise<void>
}

const supportsOutputSelection =
  typeof HTMLAudioElement !== 'undefined' &&
  'setSinkId' in HTMLAudioElement.prototype

export function useAudioDevices(): UseAudioDevicesReturn {
  const [inputDevices, setInputDevices] = useState<AudioDeviceInfo[]>([])
  const [outputDevices, setOutputDevices] = useState<AudioDeviceInfo[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const mountedRef = useRef(true)

  const enumerate = useCallback(async () => {
    try {
      let devices = await navigator.mediaDevices.enumerateDevices()

      // If labels are empty (no permission yet), request mic access to unlock them
      const hasLabels = devices.some((d) => d.label)
      if (!hasLabels) {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
          stream.getTracks().forEach((t) => t.stop())
          devices = await navigator.mediaDevices.enumerateDevices()
        } catch {
          // Permission denied — use devices without labels
        }
      }

      if (!mountedRef.current) return

      let inputCount = 0
      let outputCount = 0

      setInputDevices(
        devices
          .filter((d) => d.kind === 'audioinput')
          .map((d) => ({
            deviceId: d.deviceId,
            label: d.label || `麥克風 ${++inputCount}`,
            kind: d.kind,
          }))
      )

      setOutputDevices(
        devices
          .filter((d) => d.kind === 'audiooutput')
          .map((d) => ({
            deviceId: d.deviceId,
            label: d.label || `喇叭 ${++outputCount}`,
            kind: d.kind,
          }))
      )
    } finally {
      if (mountedRef.current) setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    void enumerate()

    const handler = () => void enumerate()
    navigator.mediaDevices.addEventListener('devicechange', handler)

    return () => {
      mountedRef.current = false
      navigator.mediaDevices.removeEventListener('devicechange', handler)
    }
  }, [enumerate])

  return {
    inputDevices,
    outputDevices,
    isLoading,
    supportsOutputSelection,
    refresh: enumerate,
  }
}
