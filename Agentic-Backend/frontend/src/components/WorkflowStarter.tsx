import React, { useState } from 'react'
import { Plus, Settings, Mail, AlertCircle, CheckCircle } from 'lucide-react'
import toast from 'react-hot-toast'

interface WorkflowStarterProps {
  onWorkflowStarted: () => void
}

interface MailboxConfig {
  server: string
  port: number
  username: string
  password: string
  mailbox?: string
  use_ssl?: boolean
}

interface ProcessingOptions {
  max_emails?: number
  unread_only?: boolean
  since_date?: string
  importance_threshold?: number
  spam_threshold?: number
  create_tasks?: boolean
  schedule_followups?: boolean
}

export const WorkflowStarter: React.FC<WorkflowStarterProps> = ({ onWorkflowStarted }) => {
  const [isOpen, setIsOpen] = useState(false)
  const [isStarting, setIsStarting] = useState(false)
  const [mailboxConfig, setMailboxConfig] = useState<MailboxConfig>({
    server: 'imap.gmail.com',
    port: 993,
    username: '',
    password: '',
    mailbox: 'INBOX',
    use_ssl: true
  })
  const [processingOptions, setProcessingOptions] = useState<ProcessingOptions>({
    max_emails: 50,
    unread_only: false,
    since_date: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // 7 days ago
    importance_threshold: 0.7,
    spam_threshold: 0.8,
    create_tasks: true,
    schedule_followups: true
  })

  const handleStartWorkflow = async () => {
    if (!mailboxConfig.username || !mailboxConfig.password) {
      toast.error('Please provide email credentials')
      return
    }

    setIsStarting(true)
    try {
      const response = await fetch('/api/v1/email/workflows/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        },
        body: JSON.stringify({
          mailbox_config: mailboxConfig,
          processing_options: processingOptions,
          user_id: 'default-user' // In a real app, get from auth context
        })
      })

      if (response.ok) {
        const result = await response.json()
        toast.success(`Workflow started! Processing ${result.workflow_id}`)
        setIsOpen(false)
        onWorkflowStarted()
      } else {
        const error = await response.json()
        toast.error(`Failed to start workflow: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Failed to start workflow:', error)
      toast.error('Failed to start workflow. Please try again.')
    } finally {
      setIsStarting(false)
    }
  }

  const presetConfigs = {
    gmail: {
      server: 'imap.gmail.com',
      port: 993,
      mailbox: 'INBOX',
      use_ssl: true
    },
    outlook: {
      server: 'outlook.office365.com',
      port: 993,
      mailbox: 'INBOX',
      use_ssl: true
    },
    yahoo: {
      server: 'imap.mail.yahoo.com',
      port: 993,
      mailbox: 'INBOX',
      use_ssl: true
    }
  }

  const applyPreset = (preset: keyof typeof presetConfigs) => {
    setMailboxConfig(prev => ({
      ...prev,
      ...presetConfigs[preset]
    }))
  }

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="btn-primary flex items-center space-x-2"
      >
        <Plus className="h-4 w-4" />
        <span>Start Email Workflow</span>
      </button>

      {isOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center space-x-3">
                  <Mail className="h-6 w-6 text-blue-600" />
                  <h2 className="text-xl font-semibold text-gray-900">Start Email Processing Workflow</h2>
                </div>
                <button
                  onClick={() => setIsOpen(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <span className="text-2xl">&times;</span>
                </button>
              </div>

              <div className="space-y-6">
                {/* Quick Setup */}
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <h3 className="text-sm font-medium text-blue-900 mb-3">Quick Setup</h3>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(presetConfigs).map(([key, config]) => (
                      <button
                        key={key}
                        onClick={() => applyPreset(key as keyof typeof presetConfigs)}
                        className="px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200 transition-colors capitalize"
                      >
                        {key}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Mailbox Configuration */}
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center space-x-2">
                    <Settings className="h-5 w-5" />
                    <span>Mailbox Configuration</span>
                  </h3>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        IMAP Server
                      </label>
                      <input
                        type="text"
                        value={mailboxConfig.server}
                        onChange={(e) => setMailboxConfig(prev => ({ ...prev, server: e.target.value }))}
                        className="input-field"
                        placeholder="imap.gmail.com"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Port
                      </label>
                      <input
                        type="number"
                        value={mailboxConfig.port}
                        onChange={(e) => setMailboxConfig(prev => ({ ...prev, port: parseInt(e.target.value) }))}
                        className="input-field"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Email Address
                      </label>
                      <input
                        type="email"
                        value={mailboxConfig.username}
                        onChange={(e) => setMailboxConfig(prev => ({ ...prev, username: e.target.value }))}
                        className="input-field"
                        placeholder="your-email@gmail.com"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Password / App Password
                      </label>
                      <input
                        type="password"
                        value={mailboxConfig.password}
                        onChange={(e) => setMailboxConfig(prev => ({ ...prev, password: e.target.value }))}
                        className="input-field"
                        placeholder="App-specific password"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Mailbox
                      </label>
                      <input
                        type="text"
                        value={mailboxConfig.mailbox}
                        onChange={(e) => setMailboxConfig(prev => ({ ...prev, mailbox: e.target.value }))}
                        className="input-field"
                        placeholder="INBOX"
                      />
                    </div>

                    <div className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id="use_ssl"
                        checked={mailboxConfig.use_ssl}
                        onChange={(e) => setMailboxConfig(prev => ({ ...prev, use_ssl: e.target.checked }))}
                        className="rounded border-gray-300"
                      />
                      <label htmlFor="use_ssl" className="text-sm text-gray-700">
                        Use SSL/TLS
                      </label>
                    </div>
                  </div>
                </div>

                {/* Processing Options */}
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Processing Options</h3>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Max Emails to Process
                      </label>
                      <input
                        type="number"
                        value={processingOptions.max_emails}
                        onChange={(e) => setProcessingOptions(prev => ({ ...prev, max_emails: parseInt(e.target.value) }))}
                        className="input-field"
                        min="1"
                        max="500"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Since Date
                      </label>
                      <input
                        type="date"
                        value={processingOptions.since_date}
                        onChange={(e) => setProcessingOptions(prev => ({ ...prev, since_date: e.target.value }))}
                        className="input-field"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Importance Threshold (0-1)
                      </label>
                      <input
                        type="number"
                        value={processingOptions.importance_threshold}
                        onChange={(e) => setProcessingOptions(prev => ({ ...prev, importance_threshold: parseFloat(e.target.value) }))}
                        className="input-field"
                        min="0"
                        max="1"
                        step="0.1"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Spam Threshold (0-1)
                      </label>
                      <input
                        type="number"
                        value={processingOptions.spam_threshold}
                        onChange={(e) => setProcessingOptions(prev => ({ ...prev, spam_threshold: parseFloat(e.target.value) }))}
                        className="input-field"
                        min="0"
                        max="1"
                        step="0.1"
                      />
                    </div>

                    <div className="flex items-center space-x-4">
                      <div className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          id="unread_only"
                          checked={processingOptions.unread_only}
                          onChange={(e) => setProcessingOptions(prev => ({ ...prev, unread_only: e.target.checked }))}
                          className="rounded border-gray-300"
                        />
                        <label htmlFor="unread_only" className="text-sm text-gray-700">
                          Unread emails only
                        </label>
                      </div>

                      <div className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          id="create_tasks"
                          checked={processingOptions.create_tasks}
                          onChange={(e) => setProcessingOptions(prev => ({ ...prev, create_tasks: e.target.checked }))}
                          className="rounded border-gray-300"
                        />
                        <label htmlFor="create_tasks" className="text-sm text-gray-700">
                          Create tasks
                        </label>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id="schedule_followups"
                        checked={processingOptions.schedule_followups}
                        onChange={(e) => setProcessingOptions(prev => ({ ...prev, schedule_followups: e.target.checked }))}
                        className="rounded border-gray-300"
                      />
                      <label htmlFor="schedule_followups" className="text-sm text-gray-700">
                        Schedule follow-ups
                      </label>
                    </div>
                  </div>
                </div>

                {/* Security Notice */}
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <div className="flex items-start space-x-3">
                    <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
                    <div>
                      <h4 className="text-sm font-medium text-yellow-900">Security Notice</h4>
                      <p className="text-sm text-yellow-700 mt-1">
                        Your email credentials are encrypted and stored securely. For Gmail, use an
                        <a href="https://support.google.com/accounts/answer/185833" target="_blank" rel="noopener noreferrer" className="underline ml-1">
                          app-specific password
                        </a>.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center justify-end space-x-3 pt-4 border-t border-gray-200">
                  <button
                    onClick={() => setIsOpen(false)}
                    className="btn-secondary"
                    disabled={isStarting}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleStartWorkflow}
                    disabled={isStarting}
                    className="btn-primary flex items-center space-x-2"
                  >
                    {isStarting ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                        <span>Starting Workflow...</span>
                      </>
                    ) : (
                      <>
                        <CheckCircle className="h-4 w-4" />
                        <span>Start Workflow</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}