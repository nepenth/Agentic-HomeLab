import React, { useState, useEffect, useRef } from 'react'
import { Send, MessageCircle, Bot, User, Loader2, Settings, History } from 'lucide-react'
import toast from 'react-hot-toast'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  metadata?: {
    intent?: string
    entities?: any[]
    actions?: any[]
    suggestions?: string[]
  }
}

interface ChatSession {
  id: string
  title: string
  created_at: string
  last_message_at: string
  message_count: number
}

export const EmailChat: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [showSessionList, setShowSessionList] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadChatSessions()
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const loadChatSessions = async () => {
    try {
      const response = await fetch('/api/v1/email/chat/sessions', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        }
      })

      if (response.ok) {
        const data = await response.json()
        setSessions(data.sessions || [])
      }
    } catch (error) {
      console.error('Failed to load chat sessions:', error)
    }
  }

  const createNewSession = async () => {
    try {
      const response = await fetch('/api/v1/chat/sessions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        },
        body: JSON.stringify({
          title: `Email Chat ${new Date().toLocaleDateString()}`,
          model_name: 'llama2:13b'
        })
      })

      if (response.ok) {
        const session = await response.json()
        setCurrentSessionId(session.id)
        setMessages([])
        loadChatSessions()
        toast.success('New chat session created')
      }
    } catch (error) {
      console.error('Failed to create session:', error)
      toast.error('Failed to create new session')
    }
  }

  const loadSession = async (sessionId: string) => {
    setCurrentSessionId(sessionId)
    setShowSessionList(false)

    try {
      const response = await fetch(`/api/v1/chat/sessions/${sessionId}/messages`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        }
      })

      if (response.ok) {
        const data = await response.json()
        setMessages(data.messages || [])
      }
    } catch (error) {
      console.error('Failed to load session messages:', error)
      toast.error('Failed to load session')
    }
  }

  const sendMessage = async (message: string, intent?: string) => {
    if (!message.trim()) return

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsLoading(true)

    try {
      let endpoint = '/api/v1/email/chat'
      let payload: any = { message }

      // Determine intent and use appropriate endpoint
      if (intent) {
        switch (intent) {
          case 'search':
            endpoint = '/api/v1/email/chat/search'
            break
          case 'organize':
            endpoint = '/api/v1/email/chat/organize'
            break
          case 'summarize':
            endpoint = '/api/v1/email/chat/summarize'
            break
          case 'action':
            endpoint = '/api/v1/email/chat/action'
            break
        }
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        },
        body: JSON.stringify(payload)
      })

      if (response.ok) {
        const data = await response.json()

        const assistantMessage: ChatMessage = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: data.response,
          timestamp: new Date().toISOString(),
          metadata: {
            intent: data.intent,
            entities: data.entities,
            actions: data.actions,
            suggestions: data.suggestions
          }
        }

        setMessages(prev => [...prev, assistantMessage])
      } else {
        const error = await response.json()
        toast.error(`Failed to send message: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Failed to send message:', error)
      toast.error('Failed to send message')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    sendMessage(inputMessage)
  }

  const detectIntent = (message: string): string | null => {
    const lowerMessage = message.toLowerCase()

    if (lowerMessage.includes('search') || lowerMessage.includes('find') || lowerMessage.includes('look for')) {
      return 'search'
    }
    if (lowerMessage.includes('organize') || lowerMessage.includes('sort') || lowerMessage.includes('categorize')) {
      return 'organize'
    }
    if (lowerMessage.includes('summarize') || lowerMessage.includes('summary') || lowerMessage.includes('recap')) {
      return 'summarize'
    }
    if (lowerMessage.includes('do') || lowerMessage.includes('action') || lowerMessage.includes('complete')) {
      return 'action'
    }

    return null
  }

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getIntentColor = (intent?: string) => {
    switch (intent) {
      case 'search': return 'bg-blue-100 text-blue-800'
      case 'organize': return 'bg-green-100 text-green-800'
      case 'summarize': return 'bg-purple-100 text-purple-800'
      case 'action': return 'bg-orange-100 text-orange-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="flex h-[calc(100vh-12rem)] bg-white rounded-lg shadow-sm border border-gray-200">
      {/* Session Sidebar */}
      {showSessionList && (
        <div className="w-80 border-r border-gray-200 flex flex-col">
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Chat Sessions</h3>
              <button
                onClick={() => setShowSessionList(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <span className="text-xl">&times;</span>
              </button>
            </div>
            <button
              onClick={createNewSession}
              className="w-full btn-primary flex items-center justify-center space-x-2"
            >
              <MessageCircle className="h-4 w-4" />
              <span>New Chat</span>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto">
            {sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => loadSession(session.id)}
                className={`w-full text-left p-4 border-b border-gray-100 hover:bg-gray-50 transition-colors ${
                  currentSessionId === session.id ? 'bg-blue-50 border-l-4 border-l-blue-500' : ''
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {session.title}
                    </p>
                    <p className="text-xs text-gray-500">
                      {session.message_count} messages • {new Date(session.last_message_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              </button>
            ))}

            {sessions.length === 0 && (
              <div className="p-8 text-center text-gray-500">
                <MessageCircle className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p>No chat sessions yet</p>
                <p className="text-sm">Start a new conversation to get help with your emails</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Chat Header */}
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setShowSessionList(!showSessionList)}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
            >
              <History className="h-5 w-5" />
            </button>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                {currentSessionId ? 'Email Assistant' : 'Start a Conversation'}
              </h2>
              <p className="text-sm text-gray-600">
                Ask me anything about your emails - search, organize, summarize, or take actions
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <div className="flex items-center space-x-2 text-sm text-gray-500">
              <Bot className="h-4 w-4" />
              <span>AI Assistant</span>
            </div>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && !currentSessionId && (
            <div className="text-center py-12">
              <Bot className="h-16 w-16 mx-auto mb-4 text-gray-300" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">Welcome to Email Assistant</h3>
              <p className="text-gray-600 mb-6 max-w-md mx-auto">
                I can help you search through your emails, organize them, create summaries, and even take actions.
                Try asking me something like:
              </p>
              <div className="space-y-2 text-left max-w-md mx-auto">
                <button
                  onClick={() => sendMessage("Show me my urgent emails from this week")}
                  className="w-full text-left p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  "Show me my urgent emails from this week"
                </button>
                <button
                  onClick={() => sendMessage("Summarize my emails about the project deadline")}
                  className="w-full text-left p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  "Summarize my emails about the project deadline"
                </button>
                <button
                  onClick={() => sendMessage("Organize my inbox by priority")}
                  className="w-full text-left p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  "Organize my inbox by priority"
                </button>
              </div>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-3xl rounded-lg p-4 ${
                  message.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}
              >
                <div className="flex items-start space-x-3">
                  <div className={`p-2 rounded-full ${
                    message.role === 'user' ? 'bg-blue-700' : 'bg-gray-200'
                  }`}>
                    {message.role === 'user' ? (
                      <User className="h-4 w-4" />
                    ) : (
                      <Bot className="h-4 w-4" />
                    )}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>

                    {message.metadata && (
                      <div className="mt-3 space-y-2">
                        {message.metadata.intent && (
                          <div className="flex items-center space-x-2">
                            <span className="text-xs font-medium text-gray-600">Intent:</span>
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getIntentColor(message.metadata.intent)}`}>
                              {message.metadata.intent}
                            </span>
                          </div>
                        )}

                        {message.metadata.suggestions && message.metadata.suggestions.length > 0 && (
                          <div>
                            <span className="text-xs font-medium text-gray-600">Suggestions:</span>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {message.metadata.suggestions.slice(0, 3).map((suggestion, index) => (
                                <button
                                  key={index}
                                  onClick={() => sendMessage(suggestion)}
                                  className="px-2 py-1 bg-gray-200 text-gray-700 text-xs rounded-full hover:bg-gray-300 transition-colors"
                                >
                                  {suggestion}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    <div className="mt-2 text-xs opacity-70">
                      {formatTimestamp(message.timestamp)}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-lg p-4 max-w-3xl">
                <div className="flex items-center space-x-3">
                  <div className="p-2 rounded-full bg-gray-200">
                    <Bot className="h-4 w-4" />
                  </div>
                  <div className="flex items-center space-x-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span className="text-sm text-gray-600">Thinking...</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Message Input */}
        <div className="p-4 border-t border-gray-200">
          <form onSubmit={handleSubmit} className="flex space-x-3">
            <div className="flex-1">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Ask me about your emails... (e.g., 'Find urgent emails' or 'Summarize project updates')"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={isLoading}
              />
            </div>
            <button
              type="submit"
              disabled={isLoading || !inputMessage.trim()}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              <Send className="h-4 w-4" />
              <span>Send</span>
            </button>
          </form>

          <div className="mt-2 text-xs text-gray-500 text-center">
            Try: "Show me emails from John about the project" • "Summarize my unread emails" • "Organize by priority"
          </div>
        </div>
      </div>
    </div>
  )
}