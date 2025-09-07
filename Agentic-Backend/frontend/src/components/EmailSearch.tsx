import React, { useState, useEffect } from 'react'
import { Search, Filter, Calendar, User, Tag, AlertCircle, Download } from 'lucide-react'
import toast from 'react-hot-toast'

interface EmailResult {
  content_item_id: string
  email_id: string
  subject: string
  sender: string
  content_preview: string
  relevance_score: number
  importance_score: number
  categories: string[]
  sent_date: string
  has_attachments: boolean
  thread_id?: string
  matched_terms: string[]
}

interface SearchFilters {
  date_from?: string
  date_to?: string
  sender?: string
  categories?: string[]
  min_importance?: number
  has_attachments?: boolean
  thread_id?: string
}

export const EmailSearch: React.FC = () => {
  const [query, setQuery] = useState('')
  const [searchType, setSearchType] = useState<'semantic' | 'keyword'>('semantic')
  const [results, setResults] = useState<EmailResult[]>([])
  const [filters, setFilters] = useState<SearchFilters>({})
  const [isSearching, setIsSearching] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [totalCount, setTotalCount] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [suggestions, setSuggestions] = useState<string[]>([])

  const performSearch = async (page = 1) => {
    if (!query.trim()) return

    setIsSearching(true)
    try {
      const searchParams = new URLSearchParams({
        query: query.trim(),
        search_type: searchType,
        limit: '20',
        offset: ((page - 1) * 20).toString(),
        include_threads: 'true',
        ...Object.fromEntries(
          Object.entries(filters).filter(([_, value]) => value !== undefined && value !== '')
        )
      })

      const response = await fetch(`/api/v1/email/search?${searchParams}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        }
      })

      if (response.ok) {
        const data = await response.json()
        setResults(data.results || [])
        setTotalCount(data.total_count || 0)
        setSuggestions(data.suggestions || [])
        setCurrentPage(page)
      } else {
        const error = await response.json()
        toast.error(`Search failed: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Search error:', error)
      toast.error('Search failed. Please try again.')
    } finally {
      setIsSearching(false)
    }
  }

  const getSuggestions = async () => {
    if (!query.trim()) {
      setSuggestions([])
      return
    }

    try {
      const response = await fetch(`/api/v1/email/search/suggestions?query=${encodeURIComponent(query)}&limit=5`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        }
      })

      if (response.ok) {
        const data = await response.json()
        setSuggestions(data.suggestions || [])
      }
    } catch (error) {
      console.error('Failed to get suggestions:', error)
    }
  }

  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      getSuggestions()
    }, 300)

    return () => clearTimeout(debounceTimer)
  }, [query])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    performSearch(1)
  }

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion)
    setSuggestions([])
    // Auto-search with suggestion
    setTimeout(() => performSearch(1), 100)
  }

  const getImportanceColor = (score: number) => {
    if (score >= 0.8) return 'text-red-600 bg-red-100'
    if (score >= 0.6) return 'text-orange-600 bg-orange-100'
    if (score >= 0.4) return 'text-yellow-600 bg-yellow-100'
    return 'text-green-600 bg-green-100'
  }

  const getRelevanceColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600'
    if (score >= 0.6) return 'text-blue-600'
    if (score >= 0.4) return 'text-yellow-600'
    return 'text-gray-600'
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

  const exportResults = () => {
    const csvContent = [
      ['Subject', 'Sender', 'Date', 'Importance', 'Categories', 'Preview'].join(','),
      ...results.map(result => [
        `"${result.subject.replace(/"/g, '""')}"`,
        `"${result.sender}"`,
        `"${formatDate(result.sent_date)}"`,
        result.importance_score.toFixed(2),
        `"${result.categories.join(', ')}"`,
        `"${result.content_preview.replace(/"/g, '""').slice(0, 100)}..."`
      ].join(','))
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `email-search-results-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    window.URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      {/* Search Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Email Search</h2>
          <p className="text-gray-600 mt-1">Search through your processed emails with AI-powered semantic search</p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="btn-secondary flex items-center space-x-2"
          >
            <Filter className="h-4 w-4" />
            <span>Filters</span>
          </button>
          {results.length > 0 && (
            <button
              onClick={exportResults}
              className="btn-secondary flex items-center space-x-2"
            >
              <Download className="h-4 w-4" />
              <span>Export</span>
            </button>
          )}
        </div>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="space-y-4">
        <div className="flex space-x-4">
          <div className="flex-1 relative">
            <div className="relative">
              <Search className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search emails... (e.g., 'urgent project deadlines' or 'meeting with boss')"
                className="input-field pl-10 pr-4 py-3 text-lg"
              />
            </div>

            {/* Search Suggestions */}
            {suggestions.length > 0 && (
              <div className="absolute z-10 w-full bg-white border border-gray-200 rounded-md shadow-lg mt-1">
                {suggestions.map((suggestion, index) => (
                  <button
                    key={index}
                    onClick={() => handleSuggestionClick(suggestion)}
                    className="w-full text-left px-4 py-2 hover:bg-gray-50 border-b border-gray-100 last:border-b-0"
                  >
                    <div className="flex items-center space-x-2">
                      <Search className="h-4 w-4 text-gray-400" />
                      <span className="text-gray-700">{suggestion}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <select
            value={searchType}
            onChange={(e) => setSearchType(e.target.value as 'semantic' | 'keyword')}
            className="input-field w-40"
          >
            <option value="semantic">Semantic</option>
            <option value="keyword">Keyword</option>
          </select>

          <button
            type="submit"
            disabled={isSearching || !query.trim()}
            className="btn-primary px-8 flex items-center space-x-2"
          >
            {isSearching ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Searching...</span>
              </>
            ) : (
              <>
                <Search className="h-4 w-4" />
                <span>Search</span>
              </>
            )}
          </button>
        </div>
      </form>

      {/* Advanced Filters */}
      {showFilters && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Advanced Filters</h3>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                From Date
              </label>
              <input
                type="date"
                value={filters.date_from || ''}
                onChange={(e) => setFilters(prev => ({ ...prev, date_from: e.target.value }))}
                className="input-field"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                To Date
              </label>
              <input
                type="date"
                value={filters.date_to || ''}
                onChange={(e) => setFilters(prev => ({ ...prev, date_to: e.target.value }))}
                className="input-field"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Sender
              </label>
              <input
                type="email"
                value={filters.sender || ''}
                onChange={(e) => setFilters(prev => ({ ...prev, sender: e.target.value }))}
                placeholder="sender@example.com"
                className="input-field"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Min Importance (0-1)
              </label>
              <input
                type="number"
                value={filters.min_importance || ''}
                onChange={(e) => setFilters(prev => ({ ...prev, min_importance: parseFloat(e.target.value) || undefined }))}
                min="0"
                max="1"
                step="0.1"
                className="input-field"
              />
            </div>
          </div>

          <div className="flex items-center space-x-4 mt-4">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={filters.has_attachments || false}
                onChange={(e) => setFilters(prev => ({ ...prev, has_attachments: e.target.checked }))}
                className="rounded border-gray-300"
              />
              <span className="text-sm text-gray-700">Has Attachments</span>
            </label>
          </div>
        </div>
      )}

      {/* Search Results */}
      {results.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">
              Search Results ({totalCount.toLocaleString()})
            </h3>
            <div className="text-sm text-gray-600">
              Page {currentPage} • {results.length} shown
            </div>
          </div>

          <div className="space-y-3">
            {results.map((result) => (
              <div key={result.content_item_id} className="card hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <h4 className="text-lg font-semibold text-gray-900 line-clamp-1">
                        {result.subject}
                      </h4>
                      <span className={`status-badge ${getImportanceColor(result.importance_score)}`}>
                        {result.importance_score >= 0.8 ? 'High' :
                         result.importance_score >= 0.6 ? 'Medium' :
                         result.importance_score >= 0.4 ? 'Low' : 'Very Low'}
                      </span>
                      {result.has_attachments && (
                        <span className="status-badge bg-blue-100 text-blue-800">
                          📎 Attachment
                        </span>
                      )}
                    </div>

                    <div className="flex items-center space-x-4 text-sm text-gray-600 mb-2">
                      <div className="flex items-center space-x-1">
                        <User className="h-4 w-4" />
                        <span>{result.sender}</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <Calendar className="h-4 w-4" />
                        <span>{formatDate(result.sent_date)}</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <span className={`font-medium ${getRelevanceColor(result.relevance_score)}`}>
                          Relevance: {(result.relevance_score * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>

                    <p className="text-gray-700 mb-3 line-clamp-2">
                      {result.content_preview}
                    </p>

                    {result.categories.length > 0 && (
                      <div className="flex items-center space-x-2 mb-3">
                        <Tag className="h-4 w-4 text-gray-400" />
                        <div className="flex flex-wrap gap-1">
                          {result.categories.slice(0, 3).map((category, index) => (
                            <span
                              key={index}
                              className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-full"
                            >
                              {category}
                            </span>
                          ))}
                          {result.categories.length > 3 && (
                            <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-full">
                              +{result.categories.length - 3} more
                            </span>
                          )}
                        </div>
                      </div>
                    )}

                    {result.matched_terms.length > 0 && (
                      <div className="text-sm text-gray-600">
                        <span className="font-medium">Matched terms:</span>{' '}
                        {result.matched_terms.slice(0, 5).join(', ')}
                        {result.matched_terms.length > 5 && ` +${result.matched_terms.length - 5} more`}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalCount > 20 && (
            <div className="flex items-center justify-center space-x-2 mt-6">
              <button
                onClick={() => performSearch(currentPage - 1)}
                disabled={currentPage === 1 || isSearching}
                className="btn-secondary"
              >
                Previous
              </button>

              <span className="text-gray-600">
                Page {currentPage} of {Math.ceil(totalCount / 20)}
              </span>

              <button
                onClick={() => performSearch(currentPage + 1)}
                disabled={currentPage === Math.ceil(totalCount / 20) || isSearching}
                className="btn-primary"
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {query && !isSearching && results.length === 0 && (
        <div className="text-center py-12">
          <Search className="h-16 w-16 mx-auto mb-4 text-gray-300" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No results found</h3>
          <p className="text-gray-600 mb-4">
            Try adjusting your search query or filters
          </p>
          <div className="flex justify-center space-x-4 text-sm text-gray-500">
            <div>💡 Try semantic search for better results</div>
            <div>📅 Use date filters to narrow results</div>
            <div>🏷️ Filter by categories or importance</div>
          </div>
        </div>
      )}
    </div>
  )
}