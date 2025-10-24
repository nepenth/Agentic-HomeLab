# Chain-of-Thought Testing Guide

## System Status ✅

### Backend Services
- ✅ API Server: Running on port 8000
- ✅ Worker: Running (Celery)
- ✅ Database: PostgreSQL with pgvector
- ✅ Redis: Message broker active
- ✅ Ollama: Connected to whyland-ai.nakedsun.xyz:11434

### Tool Registry
All 4 tools registered successfully:
1. ✅ `search_emails` - Semantic email search
2. ✅ `extract_entities` - Entity extraction (tracking, orders, etc.)
3. ✅ `get_email_thread` - Thread/conversation retrieval
4. ✅ `analyze_email_content` - LLM-powered analysis

### Frontend
- ✅ Built successfully (1.7MB bundle)
- ✅ Nginx serving on HTTPS
- ✅ ReasoningChain component integrated
- ✅ SSE client functional

---

## How to Test Chain-of-Thought

### Step 1: Access the Frontend
1. Open browser to: `https://whyland-ai.nakedsun.xyz:8443`
2. Login with your credentials
3. Navigate to **Email Assistant** → **Assistant** tab

### Step 2: Enable Chain-of-Thought Mode
1. Look for the **robot icon** (🤖) button next to the message input
2. Click it to toggle Chain-of-Thought mode
3. When active, the button will be highlighted in blue
4. Tooltip will show: "Chain-of-Thought enabled"

### Step 3: Send a Test Query

Try these example queries to see the AI's reasoning:

#### Query 1: Email Search with Reasoning
```
Find emails from Amazon about deliveries in the last week
```

**Expected Reasoning Steps:**
1. **Planning**: AI decides to use `search_emails` tool
2. **Tool Call**: Executes search with parameters (query="Amazon delivery", days_back=7)
3. **Tool Result**: Shows number of emails found
4. **Synthesis**: AI analyzes results
5. **Final Answer**: Formatted response with email details

#### Query 2: Complex Multi-Step Query
```
Am I expecting any deliveries today? What's in the orders?
```

**Expected Reasoning Steps:**
1. **Planning**: Search for delivery-related emails
2. **Tool Call**: `search_emails` for tracking/delivery keywords
3. **Planning**: Extract tracking numbers from results
4. **Tool Call**: `extract_entities` with entity_type="tracking_number"
5. **Planning**: Find order details
6. **Tool Call**: `search_emails` with tracking numbers
7. **Synthesis**: Combine all information
8. **Final Answer**: Complete delivery summary

#### Query 3: Email Analysis
```
Analyze my most recent email from support@company.com
```

**Expected Reasoning Steps:**
1. **Planning**: Search for email from specific sender
2. **Tool Call**: `search_emails` with sender filter
3. **Planning**: Analyze the email content
4. **Tool Call**: `analyze_email_content` for sentiment/summary
5. **Final Answer**: Analysis results

---

## What to Look For

### Visual Elements in ReasoningChain Component

1. **Collapsible Header**
   - Shows "Chain of Thought Reasoning"
   - Displays step count badge
   - Shows spinner when active
   - Click to expand/collapse

2. **Step Icons & Colors**
   - 🧠 **Blue** = Planning (AI thinking)
   - 🔧 **Green** = Tool Call (executing tools)
   - 📊 **Orange** = Analysis (processing results)
   - 💜 **Purple** = Synthesis (combining info)
   - ✅ **Green** = Final Answer
   - ❌ **Red** = Error

3. **Step Details**
   - **Description**: What the AI is doing
   - **Content**: AI's reasoning explanation
   - **Tool Call**: Tool name + JSON parameters
   - **Tool Result**: Success/failure + data counts
   - **Duration**: Time taken in milliseconds

4. **Connector Lines**
   - Visual flow from step to step
   - Shows progression through reasoning chain

---

## Troubleshooting

### If Chain-of-Thought Doesn't Appear

1. **Check Console Logs**
   ```javascript
   // Open browser DevTools (F12)
   // Look for errors in Console tab
   ```

2. **Verify Network Request**
   - Network tab should show POST to `/api/v1/email/chat/stream-agentic`
   - Response type should be `text/event-stream`
   - Status should be 200

3. **Check Browser Support**
   - Ensure browser supports Fetch API streams
   - Chrome/Edge 93+, Firefox 100+, Safari 15.4+

### If API Returns Errors

1. **Check Backend Logs**
   ```bash
   docker compose logs api --tail=100
   ```

2. **Verify Authentication**
   - Token stored in localStorage
   - Token not expired
   - User has email access

3. **Check Ollama Connection**
   - Ollama service must be running
   - Model `qwen3:30b-a3b-thinking-2507-q8_0` must be available

---

## API Testing (Command Line)

Test the backend directly:

```bash
TOKEN="your_access_token_here"

curl -N -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find recent emails about deliveries",
    "model_name": "qwen3:30b-a3b-thinking-2507-q8_0",
    "max_days_back": 7
  }' \
  http://localhost:8000/api/v1/email/chat/stream-agentic
```

**Expected Output:**
```
data: {"step_number": 1, "step_type": "planning", ...}

data: {"step_number": 2, "step_type": "tool_call", ...}

data: {"step_number": 3, "step_type": "synthesis", ...}

data: {"type": "complete"}
```

---

## Performance Notes

- **First Query**: May be slower (LLM warm-up)
- **Typical Response Time**: 10-60 seconds depending on:
  - Number of tool calls (max 7)
  - Email database size
  - LLM response time
  - Network latency
- **Steps**: Usually 3-8 steps for typical queries

---

## Success Criteria ✅

The system is working correctly if you see:

1. ✅ Robot icon toggles to blue when clicked
2. ✅ Reasoning chain appears above the final answer
3. ✅ Steps stream in real-time (not all at once)
4. ✅ Tool calls show formatted JSON parameters
5. ✅ Tool results show success/failure with counts
6. ✅ Final answer appears after all reasoning
7. ✅ Can expand/collapse the reasoning chain
8. ✅ Duration metrics shown for each step

---

## Next Steps After Testing

Once chain-of-thought is confirmed working:

### Phase 3: UI/UX Polish (Optional Enhancements)
- Add step-by-step animations
- Auto-collapse after completion
- Copy/share reasoning chain
- Export to PDF/Markdown
- Performance optimizations

### Phase 4: Advanced Features (Future)
- Additional specialized tools
- Tool result caching
- Multi-turn conversation context
- Reasoning analytics dashboard
- Voice interaction support

---

## Support

If you encounter issues:

1. Check this guide's troubleshooting section
2. Review backend logs: `docker compose logs api -f`
3. Review frontend console (F12 → Console tab)
4. Verify all services are running: `docker compose ps`

---

**Last Updated**: 2025-10-23
**Version**: Phase 1 & 2 Complete
