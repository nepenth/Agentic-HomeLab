import React, { useState, useEffect, useCallback } from 'react';
import './EmailWorkflowDashboard.css';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

/**
 * Email Workflow Dashboard Component
 *
 * This component demonstrates how to integrate with the email analyzer workflow,
 * displaying processed emails, managing tasks, and monitoring workflow statistics.
 */
function EmailWorkflowDashboard() {
  // State management
  const [emails, setEmails] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [filter, setFilter] = useState('all'); // all, pending, completed
  const [wsConnection, setWsConnection] = useState(null);

  // API helper functions
  const apiRequest = useCallback(async (endpoint, options = {}) => {
    const url = `${API_BASE_URL}${endpoint}`;
    const config = {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('apiKey')}`,
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    };

    const response = await fetch(url, config);
    if (!response.ok) {
      throw new Error(`API request failed: ${response.statusText}`);
    }
    return response.json();
  }, []);

  // WebSocket connection for real-time updates
  const setupWebSocket = useCallback(() => {
    const ws = new WebSocket(`ws://${API_BASE_URL.replace('http://', '')}/ws/workflow-updates`);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setWsConnection(ws);
    };

    ws.onmessage = (event) => {
      const update = JSON.parse(event.data);
      handleRealtimeUpdate(update);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setWsConnection(null);
      // Attempt to reconnect after 5 seconds
      setTimeout(setupWebSocket, 5000);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return ws;
  }, [API_BASE_URL]);

  // Handle real-time updates
  const handleRealtimeUpdate = useCallback((update) => {
    switch (update.type) {
      case 'email_processed':
        setEmails(prev => [update.email, ...prev]);
        break;
      case 'task_created':
        setTasks(prev => [update.task, ...prev]);
        break;
      case 'task_updated':
        setTasks(prev => prev.map(task =>
          task.id === update.task.id ? update.task : task
        ));
        break;
      case 'stats_updated':
        setStats(update.stats);
        break;
      default:
        console.log('Unknown update type:', update.type);
    }
  }, []);

  // Load initial data
  const loadWorkflowData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [emailsRes, tasksRes, statsRes] = await Promise.all([
        apiRequest('/api/v1/workflow/emails'),
        apiRequest('/api/v1/workflow/tasks'),
        apiRequest('/api/v1/workflow/stats')
      ]);

      setEmails(emailsRes);
      setTasks(tasksRes);
      setStats(statsRes);
    } catch (err) {
      setError(err.message);
      console.error('Failed to load workflow data:', err);
    } finally {
      setLoading(false);
    }
  }, [apiRequest]);

  // Task management functions
  const markTaskComplete = useCallback(async (taskId) => {
    try {
      await apiRequest(`/api/v1/workflow/tasks/${taskId}/complete`, {
        method: 'POST'
      });

      // Optimistically update UI
      setTasks(prev => prev.map(task =>
        task.id === taskId ? { ...task, status: 'completed' } : task
      ));
    } catch (err) {
      setError(`Failed to complete task: ${err.message}`);
      console.error('Failed to complete task:', err);
    }
  }, [apiRequest]);

  const markTaskIncomplete = useCallback(async (taskId) => {
    try {
      await apiRequest(`/api/v1/workflow/tasks/${taskId}/incomplete`, {
        method: 'POST'
      });

      setTasks(prev => prev.map(task =>
        task.id === taskId ? { ...task, status: 'pending' } : task
      ));
    } catch (err) {
      setError(`Failed to mark task incomplete: ${err.message}`);
      console.error('Failed to mark task incomplete:', err);
    }
  }, [apiRequest]);

  const updateTaskPriority = useCallback(async (taskId, priority) => {
    try {
      await apiRequest(`/api/v1/workflow/tasks/${taskId}/priority`, {
        method: 'PUT',
        body: JSON.stringify({ priority })
      });

      setTasks(prev => prev.map(task =>
        task.id === taskId ? { ...task, priority } : task
      ));
    } catch (err) {
      setError(`Failed to update task priority: ${err.message}`);
      console.error('Failed to update task priority:', err);
    }
  }, [apiRequest]);

  // Filter tasks based on current filter
  const filteredTasks = tasks.filter(task => {
    switch (filter) {
      case 'pending':
        return task.status === 'pending';
      case 'completed':
        return task.status === 'completed';
      default:
        return true;
    }
  });

  // Initialize component
  useEffect(() => {
    loadWorkflowData();
    const ws = setupWebSocket();

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [loadWorkflowData, setupWebSocket]);

  // Auto-refresh data every 30 seconds
  useEffect(() => {
    const interval = setInterval(loadWorkflowData, 30000);
    return () => clearInterval(interval);
  }, [loadWorkflowData]);

  if (loading && emails.length === 0) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading workflow data...</p>
      </div>
    );
  }

  return (
    <div className="email-workflow-dashboard">
      {/* Header with stats */}
      <div className="dashboard-header">
        <div className="header-content">
          <h1>Email Priority Workflow</h1>
          <div className="connection-status">
            <span className={`status-indicator ${wsConnection ? 'connected' : 'disconnected'}`}></span>
            {wsConnection ? 'Live Updates' : 'Connecting...'}
          </div>
        </div>

        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-value">{stats.emailsProcessed || 0}</div>
            <div className="stat-label">Emails Processed</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.tasksCreated || 0}</div>
            <div className="stat-label">Tasks Created</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.pendingTasks || 0}</div>
            <div className="stat-label">Pending Tasks</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.completedTasks || 0}</div>
            <div className="stat-label">Completed Tasks</div>
          </div>
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div className="error-banner">
          <span className="error-icon">⚠️</span>
          <span className="error-message">{error}</span>
          <button
            className="error-dismiss"
            onClick={() => setError(null)}
          >
            ×
          </button>
        </div>
      )}

      {/* Main content */}
      <div className="dashboard-content">
        {/* Emails section */}
        <div className="emails-section">
          <div className="section-header">
            <h2>Recent Emails</h2>
            <button
              className="refresh-btn"
              onClick={loadWorkflowData}
              disabled={loading}
            >
              {loading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>

          <div className="emails-list">
            {emails.slice(0, 20).map(email => (
              <div
                key={email.id}
                className={`email-item ${selectedEmail?.id === email.id ? 'selected' : ''}`}
                onClick={() => setSelectedEmail(email)}
              >
                <div className="email-header">
                  <div className="email-sender-info">
                    <span className="email-sender">{email.sender}</span>
                    <span className="email-date">
                      {new Date(email.received_date).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="email-priority">
                    <span className={`priority-badge priority-${email.priority || 'normal'}`}>
                      {email.priority || 'normal'}
                    </span>
                  </div>
                </div>

                <h3 className="email-subject">{email.subject}</h3>

                <p className="email-preview">
                  {email.body?.slice(0, 150)}...
                </p>

                <div className="email-meta">
                  <span className="email-score">
                    Score: {(email.priority_score * 100).toFixed(0)}%
                  </span>
                  {email.requires_followup && (
                    <span className="followup-indicator">📋 Needs Follow-up</span>
                  )}
                  {email.sentiment && (
                    <span className={`sentiment-indicator sentiment-${email.sentiment}`}>
                      {email.sentiment}
                    </span>
                  )}
                </div>
              </div>
            ))}

            {emails.length === 0 && !loading && (
              <div className="empty-state">
                <p>No emails processed yet.</p>
                <p>Run the email analyzer to get started!</p>
              </div>
            )}
          </div>
        </div>

        {/* Tasks section */}
        <div className="tasks-section">
          <div className="section-header">
            <h2>Follow-up Tasks</h2>
            <div className="task-filters">
              <button
                className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
                onClick={() => setFilter('all')}
              >
                All ({tasks.length})
              </button>
              <button
                className={`filter-btn ${filter === 'pending' ? 'active' : ''}`}
                onClick={() => setFilter('pending')}
              >
                Pending ({tasks.filter(t => t.status === 'pending').length})
              </button>
              <button
                className={`filter-btn ${filter === 'completed' ? 'active' : ''}`}
                onClick={() => setFilter('completed')}
              >
                Completed ({tasks.filter(t => t.status === 'completed').length})
              </button>
            </div>
          </div>

          <div className="tasks-list">
            {filteredTasks.map(task => (
              <div key={task.id} className={`task-item task-${task.status}`}>
                <div className="task-content">
                  <div className="task-header">
                    <h3>{task.task_description}</h3>
                    <div className="task-badges">
                      <span className={`priority-badge priority-${task.priority}`}>
                        {task.priority}
                      </span>
                      <span className={`status-badge status-${task.status}`}>
                        {task.status}
                      </span>
                    </div>
                  </div>

                  <div className="task-meta">
                    <span className="task-email">
                      From: {task.email_sender} - {task.email_subject}
                    </span>
                    {task.due_date && (
                      <span className="task-due">
                        Due: {new Date(task.due_date).toLocaleDateString()}
                      </span>
                    )}
                    <span className="task-created">
                      Created: {new Date(task.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  {task.tags && task.tags.length > 0 && (
                    <div className="task-tags">
                      {task.tags.map(tag => (
                        <span key={tag} className="tag">{tag}</span>
                      ))}
                    </div>
                  )}
                </div>

                <div className="task-actions">
                  {task.status === 'pending' ? (
                    <button
                      className="action-btn complete-btn"
                      onClick={() => markTaskComplete(task.id)}
                    >
                      ✅ Complete
                    </button>
                  ) : (
                    <button
                      className="action-btn incomplete-btn"
                      onClick={() => markTaskIncomplete(task.id)}
                    >
                      ↩️ Mark Pending
                    </button>
                  )}

                  <select
                    className="priority-select"
                    value={task.priority}
                    onChange={(e) => updateTaskPriority(task.id, e.target.value)}
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>
              </div>
            ))}

            {filteredTasks.length === 0 && (
              <div className="empty-state">
                <p>No tasks found.</p>
                <p>Tasks will appear here after emails are analyzed.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Email detail modal */}
      {selectedEmail && (
        <div className="modal-overlay" onClick={() => setSelectedEmail(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{selectedEmail.subject}</h2>
              <button
                className="modal-close"
                onClick={() => setSelectedEmail(null)}
              >
                ×
              </button>
            </div>

            <div className="modal-body">
              <div className="email-details">
                <div className="detail-row">
                  <strong>From:</strong> {selectedEmail.sender}
                </div>
                <div className="detail-row">
                  <strong>Date:</strong> {new Date(selectedEmail.received_date).toLocaleString()}
                </div>
                <div className="detail-row">
                  <strong>Priority Score:</strong> {(selectedEmail.priority_score * 100).toFixed(1)}%
                </div>
                <div className="detail-row">
                  <strong>Sentiment:</strong> {selectedEmail.sentiment}
                </div>
                {selectedEmail.categories && selectedEmail.categories.length > 0 && (
                  <div className="detail-row">
                    <strong>Categories:</strong> {selectedEmail.categories.join(', ')}
                  </div>
                )}
              </div>

              <div className="email-body">
                <h3>Content</h3>
                <div className="email-content">
                  {selectedEmail.body}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default EmailWorkflowDashboard;