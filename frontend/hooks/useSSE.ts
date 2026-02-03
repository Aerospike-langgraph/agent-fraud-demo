'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { TraceEvent } from '@/lib/types'

interface UseSSEOptions {
  onEvent?: (event: TraceEvent) => void
  onComplete?: (data: any) => void
  onError?: (error: Error) => void
}

interface UseSSEReturn {
  events: TraceEvent[]
  isConnected: boolean
  isComplete: boolean
  error: Error | null
  connect: () => void
  disconnect: () => void
}

export function useSSE(url: string | null, options: UseSSEOptions = {}): UseSSEReturn {
  const [events, setEvents] = useState<TraceEvent[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [isComplete, setIsComplete] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const { onEvent, onComplete, onError } = options

  const connect = useCallback(() => {
    if (!url || eventSourceRef.current) return

    try {
      const eventSource = new EventSource(url)
      eventSourceRef.current = eventSource

      eventSource.onopen = () => {
        setIsConnected(true)
        setError(null)
      }

      eventSource.onerror = (e) => {
        const err = new Error('SSE connection error')
        setError(err)
        setIsConnected(false)
        onError?.(err)
      }

      // Handle different event types
      const eventTypes = [
        'node_start',
        'node_end',
        'tool_call',
        'tool_result',
        'graph_update',
        'score_update',
        'decision',
        'artifact',
        'workflow_complete'
      ]

      eventTypes.forEach((eventType) => {
        eventSource.addEventListener(eventType, (e: MessageEvent) => {
          try {
            const data = JSON.parse(e.data)
            
            if (eventType === 'workflow_complete') {
              setIsComplete(true)
              onComplete?.(data)
              eventSource.close()
              eventSourceRef.current = null
              setIsConnected(false)
            } else {
              const event: TraceEvent = {
                type: eventType as any,
                ...data
              }
              setEvents((prev) => [...prev, event])
              onEvent?.(event)
            }
          } catch (err) {
            console.error('Error parsing SSE event:', err)
          }
        })
      })

      // Fallback for generic message events
      eventSource.onmessage = (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data)
          const event: TraceEvent = data
          setEvents((prev) => [...prev, event])
          onEvent?.(event)
        } catch (err) {
          console.error('Error parsing SSE message:', err)
        }
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to connect to SSE')
      setError(error)
      onError?.(error)
    }
  }, [url, onEvent, onComplete, onError])

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
      setIsConnected(false)
    }
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [disconnect])

  return {
    events,
    isConnected,
    isComplete,
    error,
    connect,
    disconnect
  }
}
