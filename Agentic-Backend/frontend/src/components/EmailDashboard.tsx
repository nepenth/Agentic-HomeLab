import React, { useState, useEffect } from 'react'
import { Search, Filter, Plus, RefreshCw, Settings, Mail, AlertCircle, CheckCircle, Clock } from 'lucide-react'
import { WorkflowStarter } from './WorkflowStarter'
import { EmailSearch } from './EmailSearch'
import { ProgressMonitor } from './ProgressMonitor'
import { EmailStats } from './EmailStats'

interface Workflow {
  workflow_id: string
  status: 'running' | 'completed' | 'failed' | 'cancelled'
  emails_processed: number
  tasks_created: number
  started_at: string
  completed_at?: string
  processing_time_ms: number
}

interface EmailTask {
  id: string
  email_id: string
  status: 'pending' | 'completed' | 'overdue'
  priority: 'low' | 'medium' | 'high' | 'urgent'
  description: string
  created_at: string
  due_date?: string
}

export const EmailDashboard: React.FC = () => {
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [tasks, setTasks] = useState<EmailTask[]>([])
  const [activeView, setActiveView] = useState<'overview' | 'search' | 'workflows'>('overview')
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    setIsLoading(true)
    try {
      // Load recent workflows
      const workflowsResponse = await fetch('/api/v1/email/workflows/history?limit=10')
      if (workflowsResponse.ok) {
        const workflowsData = await workflowsResponse.json()
        setWorkflows(workflowsData.workflows || [])
      }

      // Load pending tasks
      const tasksResponse = await fetch('/api/v1/email/tasks?status=pending&limit=20')
      if (tasksResponse.ok) {
        const tasksData = await tasksResponse.json()
        setTasks(tasksData.tasks || [])
      }
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600 bg-green-100'
      case 'running': return 'text-blue-600 bg-blue-100'
      case 'failed': return 'text-red-600 bg-red-100'
      case 'cancelled': return 'text-gray-600 bg-gray-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'text-red-600 bg-red-100'
      case 'high': return 'text-orange-600 bg-orange-100'
      case 'medium': return 'text-yellow-600 bg-yellow-100'
      case 'low': return 'text-green-600 bg-green-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Email Workflow Dashboard</h1>
          <p className="text-gray-600 mt-1">Manage your email processing workflows and tasks</p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={loadDashboardData}
            disabled={isLoading}
            className="btn-secondary flex items-center space-x-2"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <WorkflowStarter onWorkflowStarted={loadDashboardData} />
        </div>
      </div>

      {/* Stats Overview */}
      <EmailStats workflows={workflows} tasks={tasks} />

      {/* Navigation Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          {[
            { id: 'overview', label: 'Overview', icon: Mail },
            { id: 'search', label: 'Search Emails', icon: Search },
            { id: 'workflows', label: 'Workflow History', icon: Settings }
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveView(id as any)}
              className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm ${
                activeView === id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{label}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Content Area */}
      <div className="space-y-6">
        {activeView === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Recent Workflows */}
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Recent Workflows</h3>
                <button
                  onClick={() => setActiveView('workflows')}
                  className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                >
                  View All
                </button>
              </div>

              <div className="space-y-3">
                {workflows.slice(0, 5).map((workflow) => (
                  <div key={workflow.workflow_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center space-x-3">
                      <div className={`w-3 h-3 rounded-full ${
                        workflow.status === 'completed' ? 'bg-green-500' :
                        workflow.status === 'running' ? 'bg-blue-500' :
                        workflow.status === 'failed' ? 'bg-red-500' : 'bg-gray-500'
                      }`} />
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          Workflow {workflow.workflow_id.slice(-8)}
                        </p>
                        <p className="text-xs text-gray-500">
                          {workflow.emails_processed} emails • {workflow.tasks_created} tasks
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`status-badge ${getStatusColor(workflow.status)}`}>
                        {workflow.status}
                      </span>
                      <p className="text-xs text-gray-500 mt-1">
                        {new Date(workflow.started_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                ))}

                {workflows.length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    <Mail className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                    <p>No workflows yet</p>
                    <p className="text-sm">Start your first email processing workflow</p>
                  </div>
                )}
              </div>
            </div>

            {/* Pending Tasks */}
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Pending Tasks</h3>
                <button
                  onClick={() => setActiveView('tasks')}
                  className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                >
                  View All
                </button>
              </div>

              <div className="space-y-3">
                {tasks.slice(0, 5).map((task) => (
                  <div key={task.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900 line-clamp-2">
                        {task.description}
                      </p>
                      <div className="flex items-center space-x-2 mt-2">
                        <span className={`status-badge ${getPriorityColor(task.priority)}`}>
                          {task.priority}
                        </span>
                        <span className="text-xs text-gray-500">
                          {new Date(task.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                    <div className="ml-3">
                      {task.status === 'pending' && (
                        <Clock className="h-5 w-5 text-yellow-500" />
                      )}
                      {task.status === 'completed' && (
                        <CheckCircle className="h-5 w-5 text-green-500" />
                      )}
                      {task.status === 'overdue' && (
                        <AlertCircle className="h-5 w-5 text-red-500" />
                      )}
                    </div>
                  </div>
                ))}

                {tasks.length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    <CheckCircle className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                    <p>No pending tasks</p>
                    <p className="text-sm">All caught up!</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {activeView === 'search' && <EmailSearch />}
        {activeView === 'workflows' && <ProgressMonitor />}
      </div>
    </div>
  )
}