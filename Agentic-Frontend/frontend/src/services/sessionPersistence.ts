/**
 * Session Persistence Service
 *
 * Auto-saves chat sessions to localStorage for offline access and recovery.
 */

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  metadata?: any;
}

interface ChatSession {
  id: string;
  title: string;
  model_name: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  messages: ChatMessage[];
  is_active: boolean;
}

const SESSIONS_STORAGE_KEY = 'assistant_sessions';
const AUTO_SAVE_DEBOUNCE = 2000; // 2 seconds

class SessionPersistenceService {
  private sessions: Map<string, ChatSession> = new Map();
  private saveTimeout: NodeJS.Timeout | null = null;
  private autoSaveEnabled = false;

  constructor() {
    this.loadSessions();
    this.loadAutoSavePreference();
  }

  private loadSessions() {
    try {
      const stored = localStorage.getItem(SESSIONS_STORAGE_KEY);
      if (stored) {
        const sessionsArray: ChatSession[] = JSON.parse(stored);
        sessionsArray.forEach(session => {
          this.sessions.set(session.id, session);
        });
      }
    } catch (error) {
      console.error('Failed to load sessions:', error);
    }
  }

  private saveSessions() {
    try {
      const sessionsArray = Array.from(this.sessions.values());
      localStorage.setItem(SESSIONS_STORAGE_KEY, JSON.stringify(sessionsArray));
    } catch (error) {
      console.error('Failed to save sessions:', error);
    }
  }

  private loadAutoSavePreference() {
    try {
      const settings = localStorage.getItem('assistantSettings');
      if (settings) {
        const parsed = JSON.parse(settings);
        this.autoSaveEnabled = parsed.autoSave || false;
      }
    } catch (error) {
      console.error('Failed to load auto-save preference:', error);
    }
  }

  private debouncedSave() {
    if (this.saveTimeout) {
      clearTimeout(this.saveTimeout);
    }

    this.saveTimeout = setTimeout(() => {
      this.saveSessions();
    }, AUTO_SAVE_DEBOUNCE);
  }

  /**
   * Enable or disable auto-save
   */
  setAutoSave(enabled: boolean) {
    this.autoSaveEnabled = enabled;
  }

  /**
   * Get auto-save status
   */
  isAutoSaveEnabled(): boolean {
    return this.autoSaveEnabled;
  }

  /**
   * Save or update a session
   */
  saveSession(session: ChatSession) {
    if (!this.autoSaveEnabled) {
      return;
    }

    session.updated_at = new Date().toISOString();
    this.sessions.set(session.id, session);
    this.debouncedSave();
  }

  /**
   * Add a message to a session
   */
  addMessage(sessionId: string, message: ChatMessage) {
    if (!this.autoSaveEnabled) {
      return;
    }

    const session = this.sessions.get(sessionId);
    if (session) {
      session.messages.push(message);
      session.message_count = session.messages.length;
      session.updated_at = new Date().toISOString();
      this.debouncedSave();
    }
  }

  /**
   * Update the last message in a session
   */
  updateLastMessage(sessionId: string, updates: Partial<ChatMessage>) {
    if (!this.autoSaveEnabled) {
      return;
    }

    const session = this.sessions.get(sessionId);
    if (session && session.messages.length > 0) {
      const lastMessage = session.messages[session.messages.length - 1];
      Object.assign(lastMessage, updates);
      session.updated_at = new Date().toISOString();
      this.debouncedSave();
    }
  }

  /**
   * Get a session by ID
   */
  getSession(sessionId: string): ChatSession | undefined {
    return this.sessions.get(sessionId);
  }

  /**
   * Get all sessions
   */
  getAllSessions(): ChatSession[] {
    return Array.from(this.sessions.values()).sort(
      (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    );
  }

  /**
   * Delete a session
   */
  deleteSession(sessionId: string) {
    this.sessions.delete(sessionId);
    this.saveSessions();
  }

  /**
   * Clear all sessions
   */
  clearAll() {
    this.sessions.clear();
    this.saveSessions();
  }

  /**
   * Export sessions for backup
   */
  exportSessions(): string {
    return JSON.stringify(Array.from(this.sessions.values()), null, 2);
  }

  /**
   * Import sessions from backup
   */
  importSessions(data: string): boolean {
    try {
      const sessionsArray: ChatSession[] = JSON.parse(data);
      sessionsArray.forEach(session => {
        this.sessions.set(session.id, session);
      });
      this.saveSessions();
      return true;
    } catch (error) {
      console.error('Failed to import sessions:', error);
      return false;
    }
  }

  /**
   * Get storage size in bytes
   */
  getStorageSize(): number {
    const data = localStorage.getItem(SESSIONS_STORAGE_KEY);
    return data ? new Blob([data]).size : 0;
  }

  /**
   * Get storage size in human-readable format
   */
  getStorageSizeFormatted(): string {
    const bytes = this.getStorageSize();
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  }
}

export const sessionPersistenceService = new SessionPersistenceService();
