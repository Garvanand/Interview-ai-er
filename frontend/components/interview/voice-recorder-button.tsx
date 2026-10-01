"use client"

/**
 * VoiceRecorderButton — push-to-talk recorder with transcript editing.
 *
 * Renders a microphone button that captures audio, sends it for Whisper
 * transcription, and lets the user edit the transcript before inserting
 * it into the answer field.
 *
 * Props:
 *   onTranscriptReady — called with the final (possibly edited) transcript
 *                        and full transcription metadata
 *   disabled          — disables the button
 */

import { useVoiceRecorder, type TranscriptionMetadata } from "@/hooks/use-voice-recorder"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Mic,
  MicOff,
  Square,
  RotateCcw,
  CheckCircle,
  Loader2,
  AlertTriangle,
  Clock,
  X,
} from "lucide-react"

interface VoiceRecorderButtonProps {
  /** Called when the user confirms the transcript */
  onTranscriptReady: (transcript: string, metadata: TranscriptionMetadata) => void
  /** Disable the entire component */
  disabled?: boolean
}

export function VoiceRecorderButton({
  onTranscriptReady,
  disabled = false,
}: VoiceRecorderButtonProps) {
  const [state, actions] = useVoiceRecorder()

  const handleConfirm = () => {
    if (state.transcript.trim() && state.transcriptionMetadata) {
      onTranscriptReady(state.transcript, {
        ...state.transcriptionMetadata,
        transcript: state.transcript, // may have been edited
      })
      actions.reset()
    }
  }

  const handleCancel = () => {
    actions.reset()
  }

  // ── Not supported ─────────────────────────────────────────
  if (!state.isSupported) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <MicOff className="h-4 w-4" />
        <span>Voice input not supported in this browser</span>
      </div>
    )
  }

  // ── Idle state — just the mic button ──────────────────────
  if (state.recordingState === "idle") {
    return (
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={actions.startRecording}
        disabled={disabled}
        className="flex items-center gap-2 hover:bg-red-50 hover:border-red-300 hover:text-red-600 transition-colors"
        title="Start voice recording"
        id="voice-recorder-start"
      >
        <Mic className="h-4 w-4" />
        Voice
      </Button>
    )
  }

  // ── Recording state ───────────────────────────────────────
  if (state.recordingState === "recording") {
    return (
      <div className="flex items-center gap-2">
        <Button
          type="button"
          variant="destructive"
          size="sm"
          onClick={actions.stopRecording}
          className="flex items-center gap-2 animate-pulse"
          id="voice-recorder-stop"
        >
          <Square className="h-3 w-3 fill-current" />
          Stop
        </Button>
        <Badge variant="outline" className="flex items-center gap-1.5 text-red-600 border-red-300 bg-red-50">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
          </span>
          {state.recordingDuration}s
        </Badge>
      </div>
    )
  }

  // ── Requesting permission ─────────────────────────────────
  if (state.recordingState === "requesting_permission") {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>Requesting microphone access…</span>
      </div>
    )
  }

  // ── Transcribing ──────────────────────────────────────────
  if (state.recordingState === "transcribing" || state.recordingState === "processing") {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>Transcribing with Whisper…</span>
      </div>
    )
  }

  // ── Error state ───────────────────────────────────────────
  if (state.recordingState === "error") {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-sm text-red-600">
          <AlertTriangle className="h-4 w-4" />
          <span className="truncate max-w-[300px]">{state.errorMessage}</span>
        </div>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={actions.retry}
            className="flex items-center gap-2"
            id="voice-recorder-retry"
          >
            <RotateCcw className="h-3 w-3" />
            Retry
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleCancel}
          >
            Cancel
          </Button>
        </div>
      </div>
    )
  }

  // ── Done — transcript preview + edit + confirm ────────────
  if (state.recordingState === "done") {
    return (
      <div className="space-y-3 rounded-lg border border-green-200 bg-green-50/50 p-3">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-medium text-green-700">
            <CheckCircle className="h-4 w-4" />
            Transcript Ready
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleCancel}
            className="h-6 w-6 p-0"
          >
            <X className="h-3 w-3" />
          </Button>
        </div>

        {/* Editable transcript */}
        <textarea
          value={state.transcript}
          onChange={(e) => actions.setTranscript(e.target.value)}
          className="w-full min-h-[60px] p-2 text-sm border border-gray-200 rounded-md resize-y focus:ring-2 focus:ring-green-500 focus:border-transparent bg-white"
          placeholder="Edit transcript before submitting…"
          id="voice-transcript-editor"
        />

        {/* Metadata badges */}
        <div className="flex flex-wrap gap-1.5">
          {state.transcriptionMetadata?.model_id && (
            <Badge variant="outline" className="text-xs">
              {state.transcriptionMetadata.model_id.split("/").pop()}
            </Badge>
          )}
          {state.transcriptionMetadata?.language && (
            <Badge variant="outline" className="text-xs">
              {state.transcriptionMetadata.language}
            </Badge>
          )}
          {state.transcriptionMetadata?.duration_seconds != null && (
            <Badge variant="outline" className="text-xs flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {state.transcriptionMetadata.duration_seconds.toFixed(1)}s audio
            </Badge>
          )}
          {state.transcriptionMetadata?.confidence != null ? (
            <Badge variant="outline" className="text-xs">
              {(state.transcriptionMetadata.confidence * 100).toFixed(0)}% conf
            </Badge>
          ) : (
            <Badge variant="outline" className="text-xs text-muted-foreground">
              conf: N/A
            </Badge>
          )}
          {state.latency.totalMs != null && (
            <Badge variant="outline" className="text-xs">
              {state.latency.totalMs}ms total
            </Badge>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <Button
            type="button"
            size="sm"
            onClick={handleConfirm}
            disabled={!state.transcript.trim()}
            className="flex items-center gap-2"
            id="voice-transcript-confirm"
          >
            <CheckCircle className="h-3 w-3" />
            Use This Answer
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={actions.startRecording}
            className="flex items-center gap-2"
          >
            <Mic className="h-3 w-3" />
            Re-record
          </Button>
        </div>
      </div>
    )
  }

  return null
}
