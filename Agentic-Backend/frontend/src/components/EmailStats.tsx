import React from 'react'
import { Mail, CheckCircle, Clock, AlertTriangle, TrendingUp } from 'lucide-react'

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

interface EmailStatsProps {
  workflows: Workflow[]
  tasks: EmailTask[]
}

export const EmailStats: React.FC<EmailStatsProps> = ({ workflows, tasks }) => {
  // Calculate workflow statistics
  const totalWorkflows = workflows.length
  const completedWorkflows = workflows.filter(w => w.status === 'completed').length
  const runningWorkflows = workflows.filter(w => w.status === 'running').length
  const failedWorkflows = workflows.filter(w => w.status === 'failed').length

  const totalEmailsProcessed = workflows.reduce((sum, w) => sum + w.emails_processed, 0)
  const totalTasksCreated = workflows.reduce((sum, w) => sum + w.tasks_created, 0)

  // Calculate task statistics
  const pendingTasks = tasks.filter(t => t.status === 'pending').length
  const completedTasks = tasks.filter(t => t.status === 'completed').length
  const overdueTasks = tasks.filter(t => t.status === 'overdue').length

  const urgentTasks = tasks.filter(t => t.priority === 'urgent').length
  const highPriorityTasks = tasks.filter(t => t.priority === 'high').length

  // Calculate success rate
  const successRate = totalWorkflows > 0 ? (completedWorkflows / totalWorkflows) * 100 : 0

  // Calculate average processing time
  const avgProcessingTime = completedWorkflows > 0
    ? workflows
        .filter(w => w.status === 'completed')
        .reduce((sum, w) => sum + w.processing_time_ms, 0) / completedWorkflows
    : 0

  const formatTime = (ms: number) => {
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    if (ms < 3600000) return `${(ms / 60000).toFixed(1)}m`
    return `${(ms / 3600000).toFixed(1)}h`
  }

  const stats = [
    {
      title: 'Total Emails Processed',
      value: totalEmailsProcessed.toLocaleString(),
      icon: Mail,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
      change: null
    },
    {
      title: 'Tasks Created',
      value: totalTasksCreated.toLocaleString(),
      icon: CheckCircle,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
      change: null
    },
    {
      title: 'Pending Tasks',
      value: pendingTasks.toString(),
      icon: Clock,
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-100',
      change: overdueTasks > 0 ? `${overdueTasks} overdue` : null
    },
    {
      title: 'Workflow Success Rate',
      value: `${successRate.toFixed(1)}%`,
      icon: TrendingUp,
      color: 'text-purple-600',
      bgColor: 'bg-purple-100',
      change: null
    },
    {
      title: 'Active Workflows',
      value: runningWorkflows.toString(),
      icon: AlertTriangle,
      color: runningWorkflows > 0 ? 'text-orange-600' : 'text-gray-600',
      bgColor: runningWorkflows > 0 ? 'bg-orange-100' : 'bg-gray-100',
      change: null
    },
    {
      title: 'Avg Processing Time',
      value: formatTime(avgProcessingTime),
      icon: Clock,
      color: 'text-indigo-600',
      bgColor: 'bg-indigo-100',
      change: null
    }
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
      {stats.map((stat, index) => {
        const Icon = stat.icon
        return (
          <div key={index} className="card">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">{stat.title}</p>
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                {stat.change && (
                  <p className="text-xs text-red-600 mt-1">{stat.change}</p>
                )}
              </div>
              <div className={`p-3 rounded-full ${stat.bgColor}`}>
                <Icon className={`h-6 w-6 ${stat.color}`} />
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}