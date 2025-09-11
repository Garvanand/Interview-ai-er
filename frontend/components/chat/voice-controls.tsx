"use client"

import { useEffect, useRef, useState } from "react"
import { Button } from "@/components/ui/button"

type Props = {
  onTranscript: (text: string) => void
  onTtsChange?: (enabled: boolean) => void
}

export function VoiceControls({ onTranscript, onTtsChange }: Props) {
  const recognitionRef = useRef<any | null>(null)
  const [recording, setRecording] = useState(false)
  const [supportsSTT, setSupportsSTT] = useState(false)
  const [tts, setTts] = useState(false)

  useEffect(() => {
    // Attempt to attach browser speech recognition
    const SR: any = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (SR) {
      const rec = new SR()
      rec.lang = "en-US"
      rec.interimResults = true
      rec.continuous = false
      rec.onresult = (e: any) => {
        let final = ""
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const res = e.results[i]
          if (res.isFinal) final += res[0].transcript
        }
        if (final) onTranscript(final)
      }
      rec.onend = () => setRecording(false)
      recognitionRef.current = rec
      setSupportsSTT(true)
    }
  }, [onTranscript])

  useEffect(() => {
    onTtsChange?.(tts)
  }, [tts, onTtsChange])

  function toggleRecording() {
    const rec = recognitionRef.current
    if (!rec) return
    try {
      if (!recording) {
        rec.start()
        setRecording(true)
      } else {
        rec.stop()
        setRecording(false)
      }
    } catch {
      // ignore
    }
  }

  return (
    <div className="flex items-center gap-2">
      <Button
        type="button"
        onClick={toggleRecording}
        disabled={!supportsSTT}
        aria-pressed={recording}
        aria-label={recording ? "Stop recording" : "Start recording"}
      >
        {supportsSTT ? (recording ? "Stop Mic" : "Start Mic") : "Mic N/A"}
      </Button>
      <Button
        type="button"
        variant={tts ? "default" : "secondary"}
        onClick={() => setTts((v) => !v)}
        aria-pressed={tts}
        aria-label={tts ? "Disable TTS" : "Enable TTS"}
      >
        {tts ? "TTS On" : "TTS Off"}
      </Button>
    </div>
  )
}
