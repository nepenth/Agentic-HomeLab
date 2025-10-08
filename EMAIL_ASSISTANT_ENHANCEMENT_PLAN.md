# Email Assistant Enhancement Plan
## Modern Agentic Architecture Implementation

This document outlines the comprehensive enhancement plan for the Email Assistant workflow, following modern agentic best practices.

---

## 🎯 Part 1: Frontend Enhancements

### 1.1 Embedding Model Configuration UI

#### **Email Account Settings Page**
Location: `Agentic-Frontend/frontend/src/pages/EmailAccounts.tsx` (to be created)

**Features:**
- List all email accounts with sync status
- Per-account embedding model selector
- Real-time model availability checking
- Model performance metrics display

**API Integration:**
```typescript
// GET /api/v1/email-sync/accounts - List accounts
// GET /api/v1/models/embedding - Get available embedding models
// PATCH /api/v1/email-sync/accounts/{id} - Update account settings
```

**UI Components Needed:**
1. **EmbeddingModelSelector.tsx**
   - Dropdown with available models
   - Model metadata (dimensions, performance)
   - "Use System Default" option
   - Model testing button (generate sample embedding)

2. **EmailAccountCard.tsx**
   - Account details (email, type, sync status)
   - Last sync timestamp
   - Embedding model badge
   - Quick actions (sync now, edit settings)

---

### 1.2 Enhanced Email Assistant Chat UI

#### **Current State Analysis**
✅ **What Works:**
- Streaming support with abort capability
- Model selection with live switching
- Quick actions sidebar
- Message history management
- Basic rich content rendering

❌ **What Needs Enhancement:**

#### **1.2.1 Rich Email References Component**
File: `frontend/src/components/EmailAssistant/EmailReferences.tsx`

**Current Issues:**
- Basic email list display
- No linking to actual emails
- Limited metadata shown
- No preview/expand functionality

**Enhanced Features:**
```typescript
interface EmailReferenceProps {
  email: {
    id: string;
    subject: string;
    sender: string;
    date: string;
    snippet: string;
    importance_score: number;
    similarity_score: number;
    category: string;
    has_attachments: boolean;
    labels: string[];
  };
  onEmailClick: (emailId: string) => void;
  onCreateTask: (emailId: string) => void;
  onReply: (emailId: string) => void;
}
```

**Visual Improvements:**
- **Email cards** with hover effects
- **Importance indicators** (color-coded badges)
- **Similarity score visualization** (progress bar)
- **Quick action buttons** (View, Reply, Create Task)
- **Expandable preview** showing full email body
- **Thread context** for email chains
- **Attachment indicators** with file type icons

#### **1.2.2 Email Deep Linking**

**Implementation:**
```typescript
// URL structure: /emails/{email_id}
// Opens email in modal overlay or dedicated page

const EmailDetailModal = ({ emailId, open, onClose }) => {
  // Fetch full email content
  // Display with formatting preserved
  // Show all metadata, attachments, thread
  // Actions: Reply, Forward, Archive, Create Task
};
```

**Backend API Support:**
```python
# Add to app/api/routes/email_sync.py
@router.get("/emails/{email_id}")
async def get_email_detail(
    email_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get full email details with content, attachments, and thread."""
    # Return complete email with:
    # - Full body (text + HTML)
    # - All attachments with download links
    # - Thread emails
    # - Related tasks
    # - Email actions history
```

#### **1.2.3 Rich Text Formatting in Chat**

**Markdown Support:**
- Use `react-markdown` with syntax highlighting
- Support for:
  - **Bold**, *italic*, `code`
  - Lists (bulleted, numbered)
  - Tables
  - Code blocks
  - Blockquotes
  - Links

**Email-Specific Formatting:**
```markdown
📧 **Email from:** John Doe <john@example.com>
📅 **Sent:** 2025-10-05 14:30
📎 **Attachments:** 2 files

**Subject:** Project Update

---

[View Full Email](#/emails/abc-123) | [Create Task](#) | [Reply](#)
```

**Component Enhancement:**
```tsx
// In ChatMessage.tsx
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';

const MessageContent = ({ content }) => (
  <ReactMarkdown
    components={{
      code({ node, inline, className, children, ...props }) {
        // Syntax highlighting for code blocks
      },
      a({ node, children, href, ...props }) {
        // Custom link handling for email references
        if (href.startsWith('#/emails/')) {
          return <EmailLink emailId={extractId(href)} />;
        }
        return <a href={href} {...props}>{children}</a>;
      }
    }}
  >
    {content}
  </ReactMarkdown>
);
```

#### **1.2.4 Interactive Task Cards**

**Enhanced Task Display:**
```tsx
<TaskCard
  task={task}
  onComplete={() => completeTask(task.id)}
  onEdit={() => editTask(task.id)}
  onSnooze={() => snoozeTask(task.id)}
  showEmailContext={true}
  inline={true}
/>
```

**Features:**
- Checkbox for quick completion
- Priority badge (color-coded)
- Due date with countdown
- Related email preview
- Inline editing
- Task status progression

---

### 1.3 Email Account Configuration Page

**New Page:** `frontend/src/pages/EmailAccountSettings.tsx`

**Layout:**
```
┌─────────────────────────────────────────────┐
│ Email Accounts Configuration               │
├─────────────────────────────────────────────┤
│                                             │
│ ┌─────────────────────────────────────┐   │
│ │ chris@whyland.net                    │   │
│ │ Type: IMAP                           │   │
│ │ Status: ● Synced 2 hours ago        │   │
│ │                                      │   │
│ │ Embedding Model:                     │   │
│ │ [snowflake-arctic-embed2:latest ▼]  │   │
│ │ ○ Use system default                │   │
│ │ ● Custom model                       │   │
│ │                                      │   │
│ │ Sync Interval: [15] minutes          │   │
│ │ ☑ Auto-sync enabled                 │   │
│ │                                      │   │
│ │ [Sync Now] [Edit] [Test Model]      │   │
│ └─────────────────────────────────────┘   │
│                                             │
│ ┌─────────────────────────────────────┐   │
│ │ + Add Email Account                  │   │
│ └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

**API Implementation:**
```python
# app/api/routes/email_sync.py

@router.get("/models/embedding")
async def get_available_embedding_models():
    """Get list of available embedding models from Ollama."""
    from app.services.model_capability_service import model_capability_service

    await model_capability_service.initialize()
    models = await model_capability_service.get_embedding_models()

    return {
        "models": [
            {
                "name": model.name,
                "dimensions": model.context_length,
                "performance": model.capabilities,
                "size_mb": model.parameter_size
            }
            for model in models
        ],
        "system_default": settings.default_embedding_model
    }

@router.patch("/accounts/{account_id}/embedding-model")
async def update_account_embedding_model(
    account_id: UUID,
    model_config: EmbeddingModelConfig,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update embedding model for specific email account."""
    account = await db.get(EmailAccount, account_id)

    if not account or account.user_id != current_user.id:
        raise HTTPException(404, "Account not found")

    account.embedding_model = model_config.model_name if not model_config.use_default else None
    await db.commit()

    # Optionally trigger re-embedding of existing emails
    if model_config.regenerate_embeddings:
        from app.tasks.email_sync_tasks import regenerate_email_embeddings
        regenerate_email_embeddings.delay(str(account_id))

    return {"message": "Embedding model updated", "account_id": str(account_id)}
```

---

## 🏗️ Part 2: Backend Architecture - Modern Async-First Celery

### 2.1 The Problem with Current Approach

**Current Issue:**
```python
# ❌ BAD: Mixing async SQLAlchemy with sync Celery workers
def _sync_single_account_sync(account_id: str, sync_type: str, force_sync: bool):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_run_sync())  # Event loop in forked process
    finally:
        loop.close()  # ❌ SQLAlchemy connections still open!
```

**Why This Fails:**
1. Celery uses `prefork` pool by default (forks processes)
2. Forked processes inherit the parent's async event loop
3. SQLAlchemy's async connections try to close using the inherited (closed) loop
4. Result: `RuntimeError: Event loop is closed`

### 2.2 Modern Agentic Best Practices Solution

**Principle:** *Use the right tool for the right job*

- **API Layer**: Async (FastAPI) - handles HTTP requests efficiently
- **Background Tasks**: Sync (Celery) - processes jobs reliably
- **Database**: Hybrid - use sync sessions in Celery, async in API

#### **2.2.1 Dual Database Session Factory**

```python
# app/db/database.py

class DatabaseSessionManager:
    """Unified database session management for async and sync contexts."""

    def __init__(self, url: str):
        # Async engine for FastAPI
        self.async_engine = create_async_engine(
            url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20
        )

        # Sync engine for Celery
        sync_url = url.replace('+asyncpg', '+psycopg2')
        self.sync_engine = create_engine(
            sync_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600
        )

        self.async_session_factory = sessionmaker(
            self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        self.sync_session_factory = sessionmaker(
            self.sync_engine,
            expire_on_commit=False
        )

    @asynccontextmanager
    async def get_async_session(self):
        """For FastAPI endpoints."""
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    @contextmanager
    def get_sync_session(self):
        """For Celery tasks."""
        session = self.sync_session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

# Global instance
db_manager = DatabaseSessionManager(settings.database_url)

# FastAPI dependency
async def get_db_session():
    async with db_manager.get_async_session() as session:
        yield session

# Celery helper
def get_celery_db_session():
    return db_manager.get_sync_session()
```

#### **2.2.2 Sync-Based Email Sync Service**

```python
# app/services/sync_email_service.py (NEW)

class SyncEmailSyncService:
    """Synchronous email sync service for Celery tasks."""

    def __init__(self):
        self.logger = get_logger("sync_email_service")

    def sync_account(
        self,
        db: Session,  # ✅ Sync session
        account_id: str,
        sync_type: SyncType,
        force_sync: bool = False
    ) -> EmailSyncResult:
        """
        Synchronously sync emails for an account.

        This runs in Celery worker processes without async complications.
        """
        account = db.query(EmailAccount).filter_by(id=account_id).first()

        if not account:
            raise ValueError(f"Account {account_id} not found")

        # Get connector (IMAP is already synchronous)
        connector = self._get_connector(account)

        # Sync emails
        result = connector.fetch_emails(
            since_date=self._get_sync_start_date(account, sync_type),
            folder="INBOX"
        )

        # Process and store emails synchronously
        for email_data in result.emails:
            self._process_email(db, account, email_data)

        # Update account sync status
        account.last_sync_at = datetime.now(timezone.utc)
        account.sync_status = "success"
        db.commit()

        return EmailSyncResult(
            success=True,
            emails_processed=len(result.emails),
            # ... other fields
        )

    def _process_email(self, db: Session, account: EmailAccount, email_data: dict):
        """Process single email synchronously."""
        # Check if email exists
        existing = db.query(Email).filter_by(
            account_id=account.id,
            message_id=email_data['message_id']
        ).first()

        if existing:
            # Update existing
            for key, value in email_data.items():
                setattr(existing, key, value)
            email = existing
        else:
            # Create new
            email = Email(
                account_id=account.id,
                user_id=account.user_id,
                **email_data
            )
            db.add(email)

        db.flush()  # Get email.id

        # Generate embeddings (call sync embedding service)
        self._generate_embeddings_sync(db, email, account.embedding_model)

    def _generate_embeddings_sync(
        self,
        db: Session,
        email: Email,
        account_model: Optional[str] = None
    ):
        """Generate embeddings synchronously using requests library."""
        from app.config import settings
        import requests

        model = account_model or settings.default_embedding_model

        # Prepare content
        content_types = self._prepare_embedding_content(email)

        for emb_type, content in content_types.items():
            # Call Ollama synchronously
            response = requests.post(
                f"{settings.ollama_base_url}/api/embeddings",
                json={"model": model, "prompt": content},
                timeout=30
            )

            if response.status_code == 200:
                embedding_data = response.json()

                embedding = EmailEmbedding(
                    email_id=email.id,
                    embedding_type=emb_type,
                    embedding_vector=embedding_data['embedding'],
                    model_name=model,
                    model_version="1.0",
                    content_hash=hashlib.sha256(content.encode()).hexdigest()
                )

                db.add(embedding)

        email.embeddings_generated = True
        db.flush()

# Global instance
sync_email_service = SyncEmailSyncService()
```

#### **2.2.3 Updated Celery Tasks**

```python
# app/tasks/email_sync_tasks.py

from app.db.database import get_celery_db_session
from app.services.sync_email_service import sync_email_service

@celery_app.task(base=EmailSyncTask, bind=True, max_retries=3)
def sync_single_account(self, account_id: str, sync_type: str = "incremental"):
    """
    ✅ CLEAN: Pure synchronous task with sync database session.
    No async/await, no event loop issues.
    """
    logger.info(f"Starting sync for account {account_id}")

    try:
        with get_celery_db_session() as db:
            sync_enum = SyncType.FULL if sync_type.lower() == "full" else SyncType.INCREMENTAL

            result = sync_email_service.sync_account(
                db=db,
                account_id=account_id,
                sync_type=sync_enum
            )

            logger.info(f"Completed sync: {result.emails_processed} emails processed")

            return {
                "success": result.success,
                "emails_processed": result.emails_processed,
                "emails_added": result.emails_added,
                # ... serialize result
            }

    except Exception as exc:
        logger.error(f"Sync failed: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=120, exc=exc)
        raise

@celery_app.task
def periodic_sync_scheduler():
    """✅ CLEAN: Sync scheduler without async complications."""
    logger.info("Running periodic sync scheduler")

    with get_celery_db_session() as db:
        # Query accounts that need syncing
        accounts = db.query(EmailAccount).filter(
            EmailAccount.auto_sync_enabled == True
        ).all()

        scheduled_count = 0
        now = datetime.now(timezone.utc)

        for account in accounts:
            needs_sync = False

            if not account.last_sync_at:
                needs_sync = True
            else:
                time_since = now - account.last_sync_at
                if time_since.total_seconds() >= (account.sync_interval_minutes * 60):
                    needs_sync = True

            if needs_sync:
                # Enqueue sync task
                sync_single_account.delay(str(account.id), "incremental")

                # Update next sync time
                account.next_sync_at = now + timedelta(minutes=account.sync_interval_minutes)
                scheduled_count += 1

        db.commit()

        logger.info(f"Scheduled {scheduled_count} sync tasks")
        return {"scheduled_count": scheduled_count}
```

### 2.3 Architecture Benefits

**Modern Agentic Principles Applied:**

1. **Separation of Concerns**
   - Async for I/O-bound API requests
   - Sync for CPU-bound background processing
   - Clear boundaries, no mixing

2. **Reliability**
   - No event loop conflicts
   - Proper connection pooling
   - Graceful error handling
   - Retry mechanisms work correctly

3. **Scalability**
   - Celery workers scale independently
   - Database connections managed efficiently
   - No resource leaks

4. **Maintainability**
   - Clear code flow (no async in sync contexts)
   - Easier debugging
   - Standard Python patterns

5. **Observability**
   - Structured logging works properly
   - Metrics collection accurate
   - Tracing doesn't break

---

## 📋 Implementation Checklist

### Phase 1: Frontend Enhancements (Week 1)
- [ ] Create `EmbeddingModelSelector.tsx` component
- [ ] Create `EmailAccountSettings.tsx` page
- [ ] Add backend API endpoint `/api/v1/models/embedding`
- [ ] Add backend API endpoint `/api/v1/email-sync/accounts/{id}/embedding-model`
- [ ] Enhance `ChatMessage.tsx` with react-markdown
- [ ] Create `EmailDetailModal.tsx` for email deep linking
- [ ] Add email reference click handlers
- [ ] Update `EnhancedEmailChat.tsx` to handle email links

### Phase 2: Backend Sync Refactor (Week 2)
- [ ] Create dual database session manager in `database.py`
- [ ] Create `SyncEmailSyncService` class
- [ ] Migrate IMAP connector to ensure sync compatibility
- [ ] Create sync embedding generation method
- [ ] Update Celery tasks to use sync sessions
- [ ] Remove all `asyncio.new_event_loop()` code
- [ ] Test sync tasks thoroughly

### Phase 3: Testing & Validation (Week 3)
- [ ] Unit tests for sync email service
- [ ] Integration tests for Celery tasks
- [ ] End-to-end tests for email sync workflow
- [ ] Frontend UI/UX testing
- [ ] Performance testing (embedding generation speed)
- [ ] Load testing (multiple concurrent syncs)

### Phase 4: Documentation & Deployment (Week 4)
- [ ] Update API documentation
- [ ] Create user guide for embedding model selection
- [ ] Update developer documentation
- [ ] Migration guide for database changes
- [ ] Deployment runbook
- [ ] Monitoring and alerting setup

---

## 🎓 Best Practices Rationale

### Why Sync for Celery?

**Q:** Why not use async everywhere for consistency?

**A:** Celery's process model (forking) is fundamentally incompatible with asyncio. Key reasons:

1. **Process Forking**: When Celery forks, it copies the parent process's memory, including any event loops. These loops are in an invalid state in the child process.

2. **Connection Pooling**: Async connection pools use event loop-aware locks and semaphores. These don't transfer correctly across process boundaries.

3. **Library Support**: Most system libraries (IMAP, SMTP, etc.) are synchronous. Wrapping them in async adds complexity without benefit.

4. **Reliability**: Sync code in forked processes is battle-tested. Async in forked processes is error-prone.

### Why Keep Async for API?

1. **Concurrency**: FastAPI handles thousands of concurrent connections efficiently with async
2. **I/O Efficiency**: Database queries don't block the event loop
3. **WebSocket Support**: Real-time features require async
4. **Modern Ecosystem**: Most modern Python web frameworks use async

### The Hybrid Advantage

By using the right tool for each job:
- **APIs are fast and responsive** (async)
- **Background jobs are reliable** (sync)
- **No impedance mismatch** (clean boundaries)
- **Each component optimized** for its use case

This follows the **"Use boring technology"** principle - use proven patterns that work reliably at scale.

---

## 📚 Additional Resources

- [Celery Best Practices](https://docs.celeryproject.org/en/stable/userguide/tasks.html#best-practices)
- [SQLAlchemy 2.0 Sync vs Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [React Query Best Practices](https://tanstack.com/query/latest/docs/react/guides/important-defaults)

