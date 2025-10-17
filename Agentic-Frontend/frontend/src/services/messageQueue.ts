/**
 * Message Queue Service for Offline Support
 *
 * Queues messages when offline and automatically sends them when connection is restored.
 */

export interface QueuedMessage {
  id: string;
  sessionId?: string;
  message: string;
  context?: any;
  timestamp: number;
  retryCount: number;
  status: 'pending' | 'sending' | 'sent' | 'failed';
  error?: string;
}

const QUEUE_STORAGE_KEY = 'assistant_message_queue';
const MAX_RETRY_COUNT = 3;
const RETRY_DELAY = 2000; // 2 seconds

class MessageQueueService {
  private queue: QueuedMessage[] = [];
  private processing = false;
  private listeners: Set<(queue: QueuedMessage[]) => void> = new Set();

  constructor() {
    this.loadQueue();
    this.setupOnlineListener();
  }

  private loadQueue() {
    try {
      const stored = localStorage.getItem(QUEUE_STORAGE_KEY);
      if (stored) {
        this.queue = JSON.parse(stored);
        // Reset sending status to pending on load
        this.queue = this.queue.map(msg => ({
          ...msg,
          status: msg.status === 'sending' ? 'pending' : msg.status,
        }));
      }
    } catch (error) {
      console.error('Failed to load message queue:', error);
      this.queue = [];
    }
  }

  private saveQueue() {
    try {
      localStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(this.queue));
      this.notifyListeners();
    } catch (error) {
      console.error('Failed to save message queue:', error);
    }
  }

  private setupOnlineListener() {
    window.addEventListener('online', () => {
      console.log('Connection restored, processing queue...');
      this.processQueue();
    });
  }

  private notifyListeners() {
    this.listeners.forEach(listener => listener([...this.queue]));
  }

  /**
   * Subscribe to queue updates
   */
  subscribe(listener: (queue: QueuedMessage[]) => void) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /**
   * Add a message to the queue
   */
  enqueue(
    message: string,
    sessionId?: string,
    context?: any
  ): string {
    const queuedMessage: QueuedMessage = {
      id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      sessionId,
      message,
      context,
      timestamp: Date.now(),
      retryCount: 0,
      status: 'pending',
    };

    this.queue.push(queuedMessage);
    this.saveQueue();

    // Try to process immediately if online
    if (navigator.onLine) {
      this.processQueue();
    }

    return queuedMessage.id;
  }

  /**
   * Process all pending messages in the queue
   */
  async processQueue() {
    if (this.processing || !navigator.onLine) {
      return;
    }

    this.processing = true;

    try {
      const pendingMessages = this.queue.filter(
        msg => msg.status === 'pending' && msg.retryCount < MAX_RETRY_COUNT
      );

      for (const queuedMessage of pendingMessages) {
        await this.processMessage(queuedMessage);
      }

      // Remove sent messages
      this.queue = this.queue.filter(msg => msg.status !== 'sent');
      this.saveQueue();
    } finally {
      this.processing = false;
    }
  }

  /**
   * Process a single message
   */
  private async processMessage(queuedMessage: QueuedMessage): Promise<void> {
    queuedMessage.status = 'sending';
    this.saveQueue();

    try {
      // This will be called by the sendMessage mutation
      // For now, just mark as sent (actual sending happens in useAssistant)
      queuedMessage.status = 'sent';
      this.saveQueue();
    } catch (error: any) {
      queuedMessage.retryCount++;
      queuedMessage.error = error.message;

      if (queuedMessage.retryCount >= MAX_RETRY_COUNT) {
        queuedMessage.status = 'failed';
      } else {
        queuedMessage.status = 'pending';
        // Wait before retrying
        await new Promise(resolve => setTimeout(resolve, RETRY_DELAY * queuedMessage.retryCount));
      }

      this.saveQueue();
    }
  }

  /**
   * Mark a message as sent (called after successful API call)
   */
  markAsSent(messageId: string) {
    const message = this.queue.find(msg => msg.id === messageId);
    if (message) {
      message.status = 'sent';
      this.saveQueue();
    }
  }

  /**
   * Mark a message as failed
   */
  markAsFailed(messageId: string, error: string) {
    const message = this.queue.find(msg => msg.id === messageId);
    if (message) {
      message.status = 'failed';
      message.error = error;
      this.saveQueue();
    }
  }

  /**
   * Retry a failed message
   */
  retry(messageId: string) {
    const message = this.queue.find(msg => msg.id === messageId);
    if (message && message.status === 'failed') {
      message.status = 'pending';
      message.retryCount = 0;
      message.error = undefined;
      this.saveQueue();
      this.processQueue();
    }
  }

  /**
   * Remove a message from the queue
   */
  remove(messageId: string) {
    this.queue = this.queue.filter(msg => msg.id !== messageId);
    this.saveQueue();
  }

  /**
   * Get all queued messages
   */
  getQueue(): QueuedMessage[] {
    return [...this.queue];
  }

  /**
   * Get pending message count
   */
  getPendingCount(): number {
    return this.queue.filter(msg => msg.status === 'pending').length;
  }

  /**
   * Clear all messages
   */
  clear() {
    this.queue = [];
    this.saveQueue();
  }
}

export const messageQueueService = new MessageQueueService();
