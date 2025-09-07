import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { EmailDashboard } from './components/EmailDashboard'
import { TaskManager } from './components/TaskManager'
import { EmailChat } from './components/EmailChat'
import { Navigation } from './components/Navigation'
import './App.css'

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      <main className="container mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={<EmailDashboard />} />
          <Route path="/tasks" element={<TaskManager />} />
          <Route path="/chat" element={<EmailChat />} />
        </Routes>
      </main>
    </div>
  )
}

export default App