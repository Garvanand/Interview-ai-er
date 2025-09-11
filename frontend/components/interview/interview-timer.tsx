"use client"

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Clock, Pause, Play, RotateCcw } from 'lucide-react'

interface InterviewTimerProps {
  duration: number // in seconds
  onTimeUp: () => void
  isPaused?: boolean
}

export function InterviewTimer({ duration, onTimeUp, isPaused = false }: InterviewTimerProps) {
  const [timeRemaining, setTimeRemaining] = useState(duration)
  const [isRunning, setIsRunning] = useState(!isPaused)
  const [isExpired, setIsExpired] = useState(false)

  useEffect(() => {
    if (!isRunning || isPaused) return

    const timer = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          setIsExpired(true)
          setIsRunning(false)
          onTimeUp()
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [isRunning, isPaused, onTimeUp])

  useEffect(() => {
    setIsRunning(!isPaused)
  }, [isPaused])

  const formatTime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`
  }

  const getProgressPercentage = (): number => {
    return ((duration - timeRemaining) / duration) * 100
  }

  const toggleTimer = () => {
    if (isExpired) return
    setIsRunning(!isRunning)
  }

  const resetTimer = () => {
    setTimeRemaining(duration)
    setIsRunning(true)
    setIsExpired(false)
  }

  const getTimeColor = (): string => {
    if (isExpired) return 'text-red-600'
    if (timeRemaining <= 300) return 'text-orange-600' // 5 minutes or less
    if (timeRemaining <= 600) return 'text-yellow-600' // 10 minutes or less
    return 'text-green-600'
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Clock className="h-4 w-4" />
          Time Remaining
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="text-center">
          <div className={`text-2xl font-bold ${getTimeColor()}`}>
            {formatTime(timeRemaining)}
          </div>
          {isExpired && (
            <div className="text-sm text-red-600 font-medium">
              Time's up!
            </div>
          )}
        </div>

        <Progress 
          value={getProgressPercentage()} 
          className="w-full"
          style={{
            '--progress-color': isExpired ? '#dc2626' : 
                               timeRemaining <= 300 ? '#ea580c' : 
                               timeRemaining <= 600 ? '#ca8a04' : '#16a34a'
          } as React.CSSProperties}
        />

        <div className="flex items-center justify-center gap-2">
          <Button
            onClick={toggleTimer}
            variant="outline"
            size="sm"
            disabled={isExpired}
            className="flex items-center gap-1"
          >
            {isRunning ? (
              <>
                <Pause className="h-3 w-3" />
                Pause
              </>
            ) : (
              <>
                <Play className="h-3 w-3" />
                Resume
              </>
            )}
          </Button>

          <Button
            onClick={resetTimer}
            variant="outline"
            size="sm"
            className="flex items-center gap-1"
          >
            <RotateCcw className="h-3 w-3" />
            Reset
          </Button>
        </div>

        <div className="text-xs text-muted-foreground text-center">
          {isRunning ? 'Timer is running' : 'Timer is paused'}
        </div>
      </CardContent>
    </Card>
  )
}


