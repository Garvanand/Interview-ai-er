"use client"

import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Separator } from '@/components/ui/separator'
import { apiClient } from '@/lib/api-client'
import { MessageCircle, Send, Bot, User, Lightbulb, HelpCircle, Clock, AlertCircle } from 'lucide-react'

interface ChatMessage {
  id: string
  type: 'user' | 'ai' | 'system'
  content: string
  timestamp: Date
  metadata?: {
    questionId?: string
    suggestionType?: 'hint' | 'clarification' | 'followup'
    confidence?: number
  }
}

interface InterviewChatProps {
  sessionId?: string
  questionId?: string
  onHintRequest?: (hint: string) => void
  onClarificationRequest?: (clarification: string) => void
}

const SYSTEM_MESSAGES = {
  welcome: "Welcome to your AI-powered interview! I'm here to help guide you through the process. Feel free to ask questions, request hints, or seek clarification on any topic.",
  hint_request: "I'll provide you with a helpful hint to guide your thinking without giving away the complete solution.",
  clarification_request: "Let me clarify that concept for you to ensure you have a solid understanding.",
  followup_ready: "I have a follow-up question ready to help deepen your understanding of this topic."
}

export function InterviewChat({ sessionId, questionId, onHintRequest, onClarificationRequest }: InterviewChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      type: 'system',
      content: SYSTEM_MESSAGES.welcome,
      timestamp: new Date()
    }
  ])
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [chatMode, setChatMode] = useState<'general' | 'hint' | 'clarification'>('general')
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Focus input when component mounts
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const addMessage = (message: Omit<ChatMessage, 'id' | 'timestamp'>) => {
    const newMessage: ChatMessage = {
      ...message,
      id: Date.now().toString(),
      timestamp: new Date()
    }
    setMessages(prev => [...prev, newMessage])
  }

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isTyping) return

    const userMessage = inputValue.trim()
    setInputValue('')
    setIsTyping(true)

    // Add user message immediately
    addMessage({
      type: 'user',
      content: userMessage
    })

    try {
      let aiResponse = ''
      let responseType: 'ai' | 'system' = 'ai'

      // Determine response type based on user input and chat mode
      if (userMessage.toLowerCase().includes('hint') || chatMode === 'hint') {
        aiResponse = await getHintResponse(userMessage)
        responseType = 'ai'
        setChatMode('hint')
      } else if (userMessage.toLowerCase().includes('clarify') || userMessage.toLowerCase().includes('explain') || chatMode === 'clarification') {
        aiResponse = await getClarificationResponse(userMessage)
        responseType = 'ai'
        setChatMode('clarification')
      } else {
        aiResponse = await getGeneralResponse(userMessage)
        responseType = 'ai'
        setChatMode('general')
      }

      // Add AI response
      addMessage({
        type: responseType,
        content: aiResponse,
        metadata: {
          suggestionType: chatMode === 'hint' ? 'hint' : chatMode === 'clarification' ? 'clarification' : undefined
        }
      })

      // Log chat interaction
      if (sessionId) {
        await apiClient.logEvent(sessionId, 'chat_interaction', {
          user_message: userMessage,
          ai_response: aiResponse,
          chat_mode: chatMode,
          question_id: questionId
        })
      }

    } catch (error: any) {
      addMessage({
        type: 'system',
        content: 'Sorry, I encountered an error while processing your request. Please try again.'
      })
    } finally {
      setIsTyping(false)
    }
  }

  const getHintResponse = async (userMessage: string): Promise<string> => {
    // Simulate AI hint generation
    await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000))
    
    const hints = [
      "Think about the problem step by step. What's the first thing you need to do?",
      "Consider edge cases - what happens with empty input or invalid data?",
      "Look for patterns in the data that might help you optimize your solution.",
      "Remember that sometimes the simplest approach is the best approach.",
      "Try to break down the problem into smaller, manageable sub-problems.",
      "What data structure would be most efficient for this type of operation?",
      "Consider the time and space complexity of your approach.",
      "Think about how you would solve this manually, then translate that to code."
    ]
    
    return hints[Math.floor(Math.random() * hints.length)]
  }

  const getClarificationResponse = async (userMessage: string): Promise<string> => {
    // Simulate AI clarification generation
    await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000))
    
    const clarifications = [
      "Let me break this down: The concept involves understanding how data flows through your program and how different operations affect the overall performance.",
      "Think of it like this: You're building a pipeline where data goes through multiple transformations, and each step has a cost in terms of time and memory.",
      "Here's a simple analogy: If you're sorting cards, you can do it one by one (O(n²)) or use a more efficient method like merge sort (O(n log n)).",
      "The key insight is that some operations scale differently with input size. A linear search grows linearly, while a binary search grows logarithmically.",
      "Consider this: Every time you loop through data, you're adding time complexity. Nested loops multiply this complexity exponentially.",
      "Memory usage works similarly - each variable you create takes up space, and some data structures use more memory than others for the same amount of data."
    ]
    
    return clarifications[Math.floor(Math.random() * clarifications.length)]
  }

  const getGeneralResponse = async (userMessage: string): Promise<string> => {
    // Simulate AI general response generation
    await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000))
    
    const responses = [
      "That's a great question! Let me help you think through this systematically.",
      "I understand your concern. Let's approach this from a different angle.",
      "You're on the right track! Let me provide some additional context.",
      "That's an interesting perspective. Let me share some insights that might help.",
      "I can see you're thinking deeply about this. Let me offer some guidance.",
      "You're asking the right questions! Let me help clarify this concept.",
      "That's a common point of confusion. Let me explain this step by step.",
      "Great observation! Let me build on that with some additional information."
    ]
    
    return responses[Math.floor(Math.random() * responses.length)]
  }

  const handleQuickAction = async (action: 'hint' | 'clarification' | 'followup') => {
    if (isTyping) return

    setIsTyping(true)
    setChatMode(action)

    try {
      let response = ''
      
      switch (action) {
        case 'hint':
          response = await getHintResponse('Request for hint')
          if (onHintRequest) onHintRequest(response)
          break
        case 'clarification':
          response = await getClarificationResponse('Request for clarification')
          if (onClarificationRequest) onClarificationRequest(response)
          break
        case 'followup':
          response = "I'll generate a follow-up question to help deepen your understanding. Let me think about the best approach..."
          break
      }

      addMessage({
        type: 'ai',
        content: response,
        metadata: {
          suggestionType: action
        }
      })

      // Log quick action
      if (sessionId) {
        await apiClient.logEvent(sessionId, 'quick_action_used', {
          action_type: action,
          question_id: questionId
        })
      }

    } catch (error: any) {
      addMessage({
        type: 'system',
        content: 'Sorry, I encountered an error. Please try again.'
      })
    } finally {
      setIsTyping(false)
    }
  }

  const formatTimestamp = (date: Date): string => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  const getMessageIcon = (type: ChatMessage['type']) => {
    switch (type) {
      case 'user':
        return <User className="h-4 w-4" />
      case 'ai':
        return <Bot className="h-4 w-4" />
      case 'system':
        return <HelpCircle className="h-4 w-4" />
      default:
        return <MessageCircle className="h-4 w-4" />
    }
  }

  const getMessageColor = (type: ChatMessage['type']) => {
    switch (type) {
      case 'user':
        return 'bg-blue-500 text-white'
      case 'ai':
        return 'bg-green-500 text-white'
      case 'system':
        return 'bg-gray-500 text-white'
      default:
        return 'bg-gray-400 text-white'
    }
  }

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2">
          <MessageCircle className="h-5 w-5" />
          AI Interview Assistant
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Get help, hints, and clarifications during your interview
        </p>
      </CardHeader>

      {/* Quick Actions */}
      <div className="px-6 pb-3">
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleQuickAction('hint')}
            disabled={isTyping}
            className="flex items-center gap-2"
          >
            <Lightbulb className="h-4 w-4" />
            Get Hint
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleQuickAction('clarification')}
            disabled={isTyping}
            className="flex items-center gap-2"
          >
            <HelpCircle className="h-4 w-4" />
            Clarify
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleQuickAction('followup')}
            disabled={isTyping}
            className="flex items-center gap-2"
          >
            <Clock className="h-4 w-4" />
            Follow-up
          </Button>
        </div>
      </div>

      <Separator />

      {/* Messages */}
      <ScrollArea className="flex-1 px-6 py-4">
        <div className="space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex gap-3 ${
                message.type === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {message.type !== 'user' && (
                <Avatar className="h-8 w-8">
                  <AvatarFallback className={getMessageColor(message.type)}>
                    {getMessageIcon(message.type)}
                  </AvatarFallback>
                </Avatar>
              )}
              
              <div
                className={`max-w-[80%] rounded-lg px-4 py-2 ${
                  message.type === 'user'
                    ? 'bg-blue-500 text-white'
                    : message.type === 'ai'
                    ? 'bg-gray-100 text-gray-900'
                    : 'bg-gray-200 text-gray-700'
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium">
                    {message.type === 'user' ? 'You' : message.type === 'ai' ? 'AI Assistant' : 'System'}
                  </span>
                  <span className="text-xs opacity-70">
                    {formatTimestamp(message.timestamp)}
                  </span>
                  {message.metadata?.suggestionType && (
                    <Badge variant="outline" className="text-xs">
                      {message.metadata.suggestionType}
                    </Badge>
                  )}
                </div>
                <p className="text-sm">{message.content}</p>
              </div>

              {message.type === 'user' && (
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-blue-500 text-white">
                    <User className="h-4 w-4" />
                  </AvatarFallback>
                </Avatar>
              )}
            </div>
          ))}
          
          {isTyping && (
            <div className="flex gap-3 justify-start">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="bg-green-500 text-white">
                  <Bot className="h-4 w-4" />
                </AvatarFallback>
              </Avatar>
              <div className="bg-gray-100 rounded-lg px-4 py-2">
                <div className="flex items-center gap-2">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                  <span className="text-sm text-gray-500">AI is typing...</span>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      <Separator />

      {/* Input */}
      <div className="p-4">
        <div className="flex gap-2">
          <Input
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Ask for help, hints, or clarification..."
            disabled={isTyping}
            className="flex-1"
          />
          <Button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || isTyping}
            size="icon"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
        
        {/* Chat Mode Indicator */}
        {chatMode !== 'general' && (
          <div className="flex items-center gap-2 mt-2">
            <AlertCircle className="h-4 w-4 text-blue-500" />
            <span className="text-xs text-blue-600">
              Mode: {chatMode === 'hint' ? 'Hint Mode' : 'Clarification Mode'}
            </span>
          </div>
        )}
      </div>
    </Card>
  )
}
