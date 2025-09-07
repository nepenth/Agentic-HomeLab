import React, { useState, useEffect } from 'react'
import { RefreshCw, Play, Pause, Square, Clock, CheckCircle, AlertCircle, TrendingUp } from 'lucide-react'
import toast from 'react-hot-toast'

interface Workflow {
  workflow_id: string
  status: 'running' | 'completed' | 'failed' | 'cancelled'
  emails_processed: number
  tasks_created: number
  started_at: string
  completed_at?: string
  processing_time_ms: number
}

interface WorkflowProgress {
  workflow_id: string
  item_title: string
  overall_progress_percentage: number
  current_phase: string
  current_phase_progress_percentage: number
  total_phases: number
  completed_phases: number
  estimated_time_remaining_ms: number
  total_processing_time_ms: number
  processing_status: string
  phases: Array<{
    phase_name: string
    status: 'pending' | 'running' | 'completed' | 'failed'
    progress_percentage: number
    processing_duration_ms?: number
    status_message?: string
    started_at?: string
    completed_at?: string
    model_used?: string
  }>
}

export const ProgressMonitor: React.FC = () => {
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowProgress | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [refreshInterval, setRefreshInterval] = useState<NodeJS.Timeout | null>(null)

  useEffect(() => {
    loadWorkflows()

    if (autoRefresh) {
      const interval = setInterval(loadWorkflows, 5000) // Refresh every 5 seconds
      setRefreshInterval(interval)
      return () => clearInterval(interval)
    } else if (refreshInterval) {
      clearInterval(refreshInterval)
      setRefreshInterval(null)
    }
  }, [autoRefresh])

  const loadWorkflows = async () => {
    try {
      const response = await fetch('/api/v1/email/workflows/history?limit=20', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        }
      })

      if (response.ok) {
        const data = await response.json()
        setWorkflows(data.workflows || [])
      }
    } catch (error) {
      console.error('Failed to load workflows:', error)
    }
  }

  const loadWorkflowProgress = async (workflowId: string) => {
    setIsLoading(true)
    try {
      const response = await fetch(`/api/v1/knowledge/items/${workflowId}/progress`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        }
      })

      if (response.ok) {
        const progress = await response.json()
        setSelectedWorkflow(progress)
      } else {
        toast.error('Failed to load workflow progress')
      }
    } catch (error) {
      console.error('Failed to load workflow progress:', error)
      toast.error('Failed to load workflow progress')
    } finally {
      setIsLoading(false)
    }
  }

  const cancelWorkflow = async (workflowId: string) => {
    try {
      const response = await fetch(`/api/v1/email/workflows/${workflowId}/cancel`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        }
      })

      if (response.ok) {
        toast.success('Workflow cancelled successfully')
        loadWorkflows()
        if (selectedWorkflow?.workflow_id === workflowId) {
          setSelectedWorkflow(null)
        }
      } else {
        toast.error('Failed to cancel workflow')
      }
    } catch (error) {
      console.error('Failed to cancel workflow:', error)
      toast.error('Failed to cancel workflow')
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600 bg-green-100'
      case 'running': return 'text-blue-600 bg-blue-100'
      case 'failed': return 'text-red-600 bg-red-100'
      case 'cancelled': return 'text-gray-600 bg-gray-100'
      case 'pending': return 'text-yellow-600 bg-yellow-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  }

  const getPhaseIcon = (phaseName: string) => {
    const icons: { [key: string]: string } = {
      'fetch_bookmarks': '📥',
      'cache_content': '💾',
      'cache_media': '📎',
      'interpret_media': '👁️',
      'categorize_content': '🏷️',
      'holistic_understanding': '🧠',
      'synthesized_learning': '📚',
      'embeddings': '🔍'
    }
    return icons[phaseName] || '⏳'
  }

  const formatTime = (ms: number) => {
    if (!ms) return 'N/A'
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    if (ms < 3600000) return `${(ms / 60000).toFixed(1)}m`
    return `${(ms / 3600000).toFixed(1)}h`
  }

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Workflow Progress Monitor</h2>
          <p className="text-gray-600 mt-1">Monitor real-time progress of email processing workflows</p>
        </div>
        <div className="flex items-center space-x-3">
          <label className="flex items-center space-x-2 text-sm">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded border-gray-300"
            />
            <span>Auto-refresh</span>
          </label>
          <button
            onClick={loadWorkflows}
            disabled={isLoading}
            className="btn-secondary flex items-center space-x-2"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Workflow List */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Workflows</h3>

          <div className="space-y-3 max-h-96 overflow-y-auto">
            {workflows.map((workflow) => (
              <div
                key={workflow.workflow_id}
                className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                  selectedWorkflow?.workflow_id === workflow.workflow_id
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => loadWorkflowProgress(workflow.workflow_id)}
              >
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium text-gray-900">
                    Workflow {workflow.workflow_id.slice(-8)}
                  </h4>
                  <span className={`status-badge ${getStatusColor(workflow.status)}`}>
                    {workflow.status}
                  </span>
                </div>

                <div className="text-sm text-gray-600 space-y-1">
                  <div className="flex justify-between">
                    <span>Emails processed:</span>
                    <span className="font-medium">{workflow.emails_processed}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Tasks created:</span>
                    <span className="font-medium">{workflow.tasks_created}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Started:</span>
                    <span className="font-medium">{formatDateTime(workflow.started_at)}</span>
                  </div>
                  {workflow.completed_at && (
                    <div className="flex justify-between">
                      <span>Completed:</span>
                      <span className="font-medium">{formatDateTime(workflow.completed_at)}</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span>Duration:</span>
                    <span className="font-medium">{formatTime(workflow.processing_time_ms)}</span>
                  </div>
                </div>

                {workflow.status === 'running' && (
                  <div className="mt-3 flex justify-end">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        cancelWorkflow(workflow.workflow_id)
                      }}
                      className="btn-danger text-xs px-3 py-1"
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </div>
            ))}

            {workflows.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <Clock className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p>No workflows found</p>
                <p className="text-sm">Start a new email processing workflow to see progress</p>
              </div>
            )}
          </div>
        </div>

        {/* Detailed Progress View */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Workflow Details</h3>

          {selectedWorkflow ? (
            <div className="space-y-4">
              {/* Overall Progress */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium text-gray-900">{selectedWorkflow.item_title}</h4>
                  <span className={`status-badge ${getStatusColor(selectedWorkflow.processing_status)}`}>
                    {selectedWorkflow.processing_status}
                  </span>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Overall Progress</span>
                    <span>{selectedWorkflow.overall_progress_percentage.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${selectedWorkflow.overall_progress_percentage}%` }}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 mt-4 text-sm">
                  <div>
                    <span className="text-gray-600">Current Phase:</span>
                    <div className="font-medium">{selectedWorkflow.current_phase}</div>
                  </div>
                  <div>
                    <span className="text-gray-600">Phase Progress:</span>
                    <div className="font-medium">{selectedWorkflow.current_phase_progress_percentage.toFixed(1)}%</div>
                  </div>
                  <div>
                    <span className="text-gray-600">Completed Phases:</span>
                    <div className="font-medium">{selectedWorkflow.completed_phases}/{selectedWorkflow.total_phases}</div>
                  </div>
                  <div>
                    <span className="text-gray-600">Time Remaining:</span>
                    <div className="font-medium">{formatTime(selectedWorkflow.estimated_time_remaining_ms)}</div>
                  </div>
                </div>
              </div>

              {/* Phase Breakdown */}
              <div>
                <h5 className="font-medium text-gray-900 mb-3">Phase Breakdown</h5>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {selectedWorkflow.phases.map((phase, index) => (
                    <div key={index} className="flex items-center space-x-3 p-2 bg-gray-50 rounded">
                      <span className="text-lg">{getPhaseIcon(phase.phase_name)}</span>
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-gray-900">
                            {phase.phase_name.replace('_', ' ').toUpperCase()}
                          </span>
                          <span className={`status-badge ${getStatusColor(phase.status)} text-xs`}>
                            {phase.status}
                          </span>
                        </div>
                        <div className="flex items-center space-x-2 mt-1">
                          <div className="flex-1 bg-gray-200 rounded-full h-1">
                            <div
                              className={`h-1 rounded-full transition-all duration-300 ${
                                phase.status === 'completed' ? 'bg-green-500' :
                                phase.status === 'running' ? 'bg-blue-500' :
                                phase.status === 'failed' ? 'bg-red-500' : 'bg-gray-300'
                              }`}
                              style={{ width: `${phase.progress_percentage}%` }}
                            />
                          </div>
                          <span className="text-xs text-gray-600">
                            {phase.progress_percentage.toFixed(0)}%
                          </span>
                        </div>
                        {phase.status_message && (
                          <p className="text-xs text-gray-600 mt-1">{phase.status_message}</p>
                        )}
                        {phase.processing_duration_ms && (
                          <p className="text-xs text-gray-500">
                            Duration: {formatTime(phase.processing_duration_ms)}
                          </p>
                        )}
                        {phase.model_used && phase.model_used !== 'n/a' && (
                          <p className="text-xs text-gray-500">
                            Model: {phase.model_used}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Action Buttons */}
              {selectedWorkflow.processing_status === 'running' && (
                <div className="flex justify-end space-x-2 pt-4 border-t">
                  <button
                    onClick={() => cancelWorkflow(selectedWorkflow.workflow_id)}
                    className="btn-danger text-sm"
                  >
                    Cancel Workflow
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500">
              <TrendingUp className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>Select a workflow to view detailed progress</p>
              <p className="text-sm">Click on any workflow from the list to see real-time progress</p>
            </div>
          )}
        </div>
      </div>

      {/* Auto-refresh indicator */}
      {autoRefresh && (
        <div className="fixed bottom-4 right-4 bg-white border border-gray-200 rounded-lg shadow-lg p-3">
          <div className="flex items-center space-x-2 text-sm text-gray-600">
            <RefreshCw className="h-4 w-4 animate-spin" />
            <span>Auto-refreshing every 5 seconds</span>
          </div>
        </div>
      )}
    </div>
  )
}