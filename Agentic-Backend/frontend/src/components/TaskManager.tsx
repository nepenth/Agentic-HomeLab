import React, { useState, useEffect } from 'react'
import { CheckCircle, Clock, AlertCircle, Calendar, Plus, Filter, Search, MoreVertical } from 'lucide-react'
import toast from 'react-hot-toast'

interface EmailTask {
  id: string
  email_id: string
  status: 'pending' | 'completed' | 'overdue'
  priority: 'low' | 'medium' | 'high' | 'urgent'
  description: string
  created_at: string
  due_date?: string
  email_subject?: string
  email_sender?: string
  category?: string
  importance_score?: number
}

interface TaskFilter {
  status?: string
  priority?: string
  category?: string
  date_from?: string
  date_to?: string
}

export const TaskManager: React.FC = () => {
  const [tasks, setTasks] = useState<EmailTask[]>([])
  const [filteredTasks, setFilteredTasks] = useState<EmailTask[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [filters, setFilters] = useState<TaskFilter>({})
  const [searchQuery, setSearchQuery] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [selectedTask, setSelectedTask] = useState<EmailTask | null>(null)

  useEffect(() => {
    loadTasks()
  }, [])

  useEffect(() => {
    applyFilters()
  }, [tasks, filters, searchQuery])

  const loadTasks = async () => {
    setIsLoading(true)
    try {
      const response = await fetch('/api/v1/email/tasks', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        }
      })

      if (response.ok) {
        const data = await response.json()
        setTasks(data.tasks || [])
      } else {
        toast.error('Failed to load tasks')
      }
    } catch (error) {
      console.error('Failed to load tasks:', error)
      toast.error('Failed to load tasks')
    } finally {
      setIsLoading(false)
    }
  }

  const applyFilters = () => {
    let filtered = [...tasks]

    // Apply search query
    if (searchQuery) {
      filtered = filtered.filter(task =>
        task.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        task.email_subject?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        task.email_sender?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    }

    // Apply status filter
    if (filters.status && filters.status !== 'all') {
      filtered = filtered.filter(task => task.status === filters.status)
    }

    // Apply priority filter
    if (filters.priority && filters.priority !== 'all') {
      filtered = filtered.filter(task => task.priority === filters.priority)
    }

    // Apply category filter
    if (filters.category && filters.category !== 'all') {
      filtered = filtered.filter(task => task.category === filters.category)
    }

    // Apply date filters
    if (filters.date_from) {
      filtered = filtered.filter(task =>
        new Date(task.created_at) >= new Date(filters.date_from!)
      )
    }

    if (filters.date_to) {
      filtered = filtered.filter(task =>
        new Date(task.created_at) <= new Date(filters.date_to!)
      )
    }

    setFilteredTasks(filtered)
  }

  const completeTask = async (taskId: string) => {
    try {
      const response = await fetch(`/api/v1/email/tasks/${taskId}/complete`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        }
      })

      if (response.ok) {
        toast.success('Task completed!')
        loadTasks()
      } else {
        toast.error('Failed to complete task')
      }
    } catch (error) {
      console.error('Failed to complete task:', error)
      toast.error('Failed to complete task')
    }
  }

  const scheduleFollowup = async (taskId: string, followupDate: string, notes: string) => {
    try {
      const response = await fetch(`/api/v1/email/tasks/${taskId}/followup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        },
        body: JSON.stringify({
          followup_date: followupDate,
          followup_notes: notes
        })
      })

      if (response.ok) {
        toast.success('Follow-up scheduled!')
        loadTasks()
      } else {
        toast.error('Failed to schedule follow-up')
      }
    } catch (error) {
      console.error('Failed to schedule follow-up:', error)
      toast.error('Failed to schedule follow-up')
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600 bg-green-100'
      case 'pending': return 'text-blue-600 bg-blue-100'
      case 'overdue': return 'text-red-600 bg-red-100'
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

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="h-5 w-5 text-green-600" />
      case 'pending': return <Clock className="h-5 w-5 text-blue-600" />
      case 'overdue': return <AlertCircle className="h-5 w-5 text-red-600" />
      default: return <Clock className="h-5 w-5 text-gray-600" />
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const isOverdue = (task: EmailTask) => {
    if (!task.due_date) return false
    return new Date(task.due_date) < new Date() && task.status !== 'completed'
  }

  const getUniqueCategories = () => {
    const categories = tasks
      .map(task => task.category)
      .filter((category): category is string => category !== undefined)
    return [...new Set(categories)]
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Task Manager</h2>
          <p className="text-gray-600 mt-1">Manage tasks generated from your email processing workflows</p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="btn-secondary flex items-center space-x-2"
          >
            <Filter className="h-4 w-4" />
            <span>Filters</span>
          </button>
          <button
            onClick={loadTasks}
            disabled={isLoading}
            className="btn-secondary flex items-center space-x-2"
          >
            <div className={`h-4 w-4 ${isLoading ? 'animate-spin rounded-full border-b-2 border-gray-600' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="space-y-4">
        <div className="flex space-x-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search tasks..."
              className="input-field pl-10"
            />
          </div>
        </div>

        {showFilters && (
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Filters</h3>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Status
                </label>
                <select
                  value={filters.status || 'all'}
                  onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value === 'all' ? undefined : e.target.value }))}
                  className="input-field"
                >
                  <option value="all">All Statuses</option>
                  <option value="pending">Pending</option>
                  <option value="completed">Completed</option>
                  <option value="overdue">Overdue</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Priority
                </label>
                <select
                  value={filters.priority || 'all'}
                  onChange={(e) => setFilters(prev => ({ ...prev, priority: e.target.value === 'all' ? undefined : e.target.value }))}
                  className="input-field"
                >
                  <option value="all">All Priorities</option>
                  <option value="urgent">Urgent</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Category
                </label>
                <select
                  value={filters.category || 'all'}
                  onChange={(e) => setFilters(prev => ({ ...prev, category: e.target.value === 'all' ? undefined : e.target.value }))}
                  className="input-field"
                >
                  <option value="all">All Categories</option>
                  {getUniqueCategories().map(category => (
                    <option key={category} value={category}>{category}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Date From
                </label>
                <input
                  type="date"
                  value={filters.date_from || ''}
                  onChange={(e) => setFilters(prev => ({ ...prev, date_from: e.target.value }))}
                  className="input-field"
                />
              </div>
            </div>

            <div className="flex justify-end mt-4">
              <button
                onClick={() => setFilters({})}
                className="btn-secondary mr-2"
              >
                Clear Filters
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Task Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Tasks</p>
              <p className="text-2xl font-bold text-gray-900">{tasks.length}</p>
            </div>
            <CheckCircle className="h-8 w-8 text-blue-600" />
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Pending</p>
              <p className="text-2xl font-bold text-blue-600">
                {tasks.filter(t => t.status === 'pending').length}
              </p>
            </div>
            <Clock className="h-8 w-8 text-blue-600" />
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Completed</p>
              <p className="text-2xl font-bold text-green-600">
                {tasks.filter(t => t.status === 'completed').length}
              </p>
            </div>
            <CheckCircle className="h-8 w-8 text-green-600" />
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Overdue</p>
              <p className="text-2xl font-bold text-red-600">
                {tasks.filter(t => isOverdue(t)).length}
              </p>
            </div>
            <AlertCircle className="h-8 w-8 text-red-600" />
          </div>
        </div>
      </div>

      {/* Task List */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900">
          Tasks ({filteredTasks.length})
        </h3>

        <div className="space-y-3">
          {filteredTasks.map((task) => (
            <div key={task.id} className="card hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-4 flex-1">
                  <div className="mt-1">
                    {getStatusIcon(task.status)}
                  </div>

                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <h4 className="text-lg font-semibold text-gray-900 line-clamp-1">
                        {task.description}
                      </h4>
                      <span className={`status-badge ${getPriorityColor(task.priority)}`}>
                        {task.priority}
                      </span>
                      {isOverdue(task) && (
                        <span className="status-badge bg-red-100 text-red-800">
                          Overdue
                        </span>
                      )}
                    </div>

                    {task.email_subject && (
                      <p className="text-sm text-gray-600 mb-2">
                        <span className="font-medium">From email:</span> {task.email_subject}
                      </p>
                    )}

                    <div className="flex items-center space-x-4 text-sm text-gray-500 mb-3">
                      <div className="flex items-center space-x-1">
                        <Calendar className="h-4 w-4" />
                        <span>Created: {formatDate(task.created_at)}</span>
                      </div>
                      {task.due_date && (
                        <div className="flex items-center space-x-1">
                          <Clock className="h-4 w-4" />
                          <span>Due: {formatDate(task.due_date)}</span>
                        </div>
                      )}
                      {task.importance_score && (
                        <div>
                          <span>Importance: {(task.importance_score * 100).toFixed(0)}%</span>
                        </div>
                      )}
                    </div>

                    {task.category && (
                      <div className="flex items-center space-x-2">
                        <span className="text-sm text-gray-600">Category:</span>
                        <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-full">
                          {task.category}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center space-x-2 ml-4">
                  {task.status === 'pending' && (
                    <>
                      <button
                        onClick={() => completeTask(task.id)}
                        className="btn-primary text-sm px-3 py-1"
                      >
                        Complete
                      </button>
                      <button
                        onClick={() => setSelectedTask(task)}
                        className="btn-secondary text-sm px-3 py-1"
                      >
                        Follow-up
                      </button>
                    </>
                  )}
                  <button className="p-2 text-gray-400 hover:text-gray-600">
                    <MoreVertical className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}

          {filteredTasks.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              <CheckCircle className="h-16 w-16 mx-auto mb-4 text-gray-300" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {tasks.length === 0 ? 'No tasks found' : 'No tasks match your filters'}
              </h3>
              <p className="text-gray-600">
                {tasks.length === 0
                  ? 'Tasks will appear here once you process some emails'
                  : 'Try adjusting your search or filter criteria'
                }
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Follow-up Modal */}
      {selectedTask && (
        <FollowupModal
          task={selectedTask}
          onClose={() => setSelectedTask(null)}
          onSchedule={scheduleFollowup}
        />
      )}
    </div>
  )
}

// Follow-up Modal Component
interface FollowupModalProps {
  task: EmailTask
  onClose: () => void
  onSchedule: (taskId: string, followupDate: string, notes: string) => void
}

const FollowupModal: React.FC<FollowupModalProps> = ({ task, onClose, onSchedule }) => {
  const [followupDate, setFollowupDate] = useState('')
  const [notes, setNotes] = useState('')

  const handleSchedule = () => {
    if (!followupDate) {
      toast.error('Please select a follow-up date')
      return
    }

    onSchedule(task.id, followupDate, notes)
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Schedule Follow-up</h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <span className="text-2xl">&times;</span>
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Follow-up Date
              </label>
              <input
                type="datetime-local"
                value={followupDate}
                onChange={(e) => setFollowupDate(e.target.value)}
                className="input-field"
                min={new Date().toISOString().slice(0, 16)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Notes (Optional)
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="input-field"
                rows={3}
                placeholder="Add any notes for the follow-up..."
              />
            </div>
          </div>

          <div className="flex justify-end space-x-3 mt-6">
            <button
              onClick={onClose}
              className="btn-secondary"
            >
              Cancel
            </button>
            <button
              onClick={handleSchedule}
              className="btn-primary"
            >
              Schedule Follow-up
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}