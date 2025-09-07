# 🔀 API Route Design Patterns & Conflict Resolution

## 📋 **Overview**

This document outlines the route design patterns used in the Agentic Backend API and provides guidelines for resolving and preventing route conflicts in FastAPI applications.

## 🚨 **Common Route Conflicts**

### **1. Path Parameter vs Static Segment Conflict**

**Problem:**
```python
# ❌ CONFLICT: FastAPI may interpret "/history" as a task_id
@router.get("/{task_id}")  # Matches any single segment
@router.get("/history")   # Also matches "/history"
```

**Solution:**
```python
# ✅ FIXED: Order specific routes before parameterized ones
@router.get("/history")   # Specific route first
@router.get("/{task_id}") # Parameterized route second
```

### **2. Query Parameter Conflicts**

**Problem:**
```python
# ❌ CONFLICT: Same path with different query params
@router.get("/items")
@router.get("/items?type=active")
```

**Solution:**
```python
# ✅ FIXED: Use query parameters in the same endpoint
@router.get("/items")
async def get_items(type: Optional[str] = None):
    # Handle both cases in one endpoint
```

### **3. HTTP Method Conflicts**

**Problem:**
```python
# ❌ CONFLICT: Same path, same method
@router.get("/users/{user_id}")  # In users.py
@router.get("/users/{user_id}")  # In admin.py
```

**Solution:**
```python
# ✅ FIXED: Use different prefixes or combine routers
api_router.include_router(users_router, prefix="/users")
api_router.include_router(admin_router, prefix="/admin")
```

## 📏 **Route Design Guidelines**

### **1. Path Structure Hierarchy**

```
✅ GOOD:
/api/v1/users                    # Collection
/api/v1/users/{id}               # Individual resource
/api/v1/users/{id}/posts         # Sub-resource collection
/api/v1/users/{id}/posts/{post_id} # Sub-resource item

❌ BAD:
/api/v1/user/{id}               # Inconsistent singular/plural
/api/v1/users/posts/{id}        # Missing parent resource ID
```

### **2. HTTP Method Usage**

| Method | Usage | Example |
|--------|-------|---------|
| GET | Retrieve resources | `GET /api/v1/users` |
| POST | Create resources | `POST /api/v1/users` |
| PUT | Update entire resource | `PUT /api/v1/users/{id}` |
| PATCH | Partial update | `PATCH /api/v1/users/{id}` |
| DELETE | Remove resource | `DELETE /api/v1/users/{id}` |

### **3. Query Parameter Patterns**

```python
# ✅ GOOD: Consistent query parameters
@router.get("/items")
async def get_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: str = Query("asc", regex="^(asc|desc)$")
):
```

### **4. Path Parameter Validation**

```python
# ✅ GOOD: Use Pydantic models for validation
from pydantic import BaseModel, Field
from uuid import UUID

class ItemId:
    item_id: UUID = Field(..., description="Item identifier")

@router.get("/{item_id}")
async def get_item(item_id: UUID):  # Automatic validation
```

## 🔧 **Conflict Resolution Strategies**

### **1. Route Ordering (Most Important)**

**Rule:** FastAPI processes routes in the order they are defined. More specific routes must come before general ones.

```python
# ✅ CORRECT ORDER
@router.get("/users/active")      # Specific route
@router.get("/users/{user_id}")   # Parameterized route
@router.get("/users")            # General route

# ❌ WRONG ORDER (will cause conflicts)
@router.get("/users/{user_id}")   # This will match "/users/active"
@router.get("/users/active")      # This will never be reached
```

### **2. Path Converters**

```python
# ✅ GOOD: Use path converters for better matching
@router.get("/items/{item_id:int}")    # Only matches integers
@router.get("/items/{slug:str}")       # Only matches strings
@router.get("/files/{path:path}")      # Matches full paths
```

### **3. Router Prefixes**

```python
# ✅ GOOD: Use prefixes to avoid conflicts
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
```

### **4. Sub-applications**

```python
# ✅ GOOD: Use sub-applications for complex routing
from fastapi import FastAPI

auth_app = FastAPI()
auth_app.include_router(auth_router)

main_app.mount("/auth", auth_app)
```

## 📊 **Current API Route Analysis**

### **Phase 1 Routes (Fixed)**
- ✅ `GET /api/v1/logs/history` - Moved before parameterized routes
- ✅ `GET /api/v1/logs/{task_id}` - Now works correctly
- ✅ `PUT /api/v1/workflows/definitions/{id}` - WorkflowStep access fixed
- ✅ `POST /api/v1/workflows/execute` - Resource management implemented

### **Phase 2 Routes (Implemented)**
- ✅ `POST /api/v1/connectors/{name}/discover` - Content discovery
- ✅ `POST /api/v1/connectors/{name}/fetch` - Content fetching
- ✅ `POST /api/v1/connectors/validate` - Content validation
- ✅ `POST /api/v1/connectors/process` - Content processing

### **Phase 3 Routes (Planned)**
- 🔄 Vision AI routes: `/api/v1/vision/*`
- 🔄 Audio AI routes: `/api/v1/audio/*`
- 🔄 Semantic processing: `/api/v1/semantic/*`

## 🛠️ **Route Testing & Validation**

### **Automated Route Conflict Detection**

```python
# Add to your FastAPI app for route validation
def validate_routes(app: FastAPI):
    """Validate routes for conflicts."""
    routes = []
    conflicts = []

    for route in app.routes:
        if hasattr(route, 'path'):
            route_info = {
                'path': route.path,
                'methods': route.methods,
                'name': route.name
            }
            routes.append(route_info)

    # Check for conflicts
    for i, route1 in enumerate(routes):
        for j, route2 in enumerate(routes[i+1:], i+1):
            if route1['path'] == route2['path']:
                if route1['methods'] & route2['methods']:
                    conflicts.append({
                        'path': route1['path'],
                        'methods': route1['methods'] & route2['methods'],
                        'routes': [route1['name'], route2['name']]
                    })

    return conflicts
```

### **Route Documentation**

```python
# Add route documentation decorator
def document_route(description: str, example: str = None):
    """Decorator to document route conflicts and usage."""
    def decorator(func):
        func.__route_docs__ = {
            'description': description,
            'example': example,
            'conflicts': [],  # List of potential conflicts
            'last_updated': datetime.now().isoformat()
        }
        return func
    return decorator

@router.get("/users/{user_id}")
@document_route(
    description="Get user by ID",
    example="/users/123"
)
async def get_user(user_id: int):
    pass
```

## 📈 **Monitoring & Maintenance**

### **Route Health Checks**

```python
@router.get("/routes/health")
async def check_route_health():
    """Check for route conflicts and issues."""
    conflicts = validate_routes(app)
    return {
        "status": "healthy" if not conflicts else "warning",
        "total_routes": len(app.routes),
        "conflicts": conflicts,
        "timestamp": datetime.now().isoformat()
    }
```

### **Route Usage Analytics**

```python
# Track route usage patterns
route_usage = defaultdict(int)

@app.middleware("http")
async def track_route_usage(request, call_next):
    route_usage[request.url.path] += 1
    response = await call_next(request)
    return response
```

## 🎯 **Best Practices Summary**

### **✅ Do's**
1. **Order routes from specific to general**
2. **Use descriptive path segments**
3. **Validate path parameters**
4. **Use consistent HTTP methods**
5. **Document route conflicts**
6. **Test routes thoroughly**

### **❌ Don'ts**
1. **Don't use same path for different methods without good reason**
2. **Don't rely on query parameters for resource identification**
3. **Don't create deeply nested paths (>3 levels)**
4. **Don't use special characters in path segments**
5. **Don't change route patterns without migration plan**

### **🔧 Tools & Commands**

```bash
# Check for route conflicts
curl -X GET "http://localhost:8000/api/v1/routes/health"

# List all routes
curl -X GET "http://localhost:8000/docs"  # OpenAPI documentation

# Test specific routes
curl -X GET "http://localhost:8000/api/v1/logs/history"
curl -X GET "http://localhost:8000/api/v1/logs/123e4567-e89b-12d3-a456-426614174000"
```

## 📞 **Contact & Support**

For route design questions or conflict resolution:
- Check this document first
- Review existing route patterns
- Test changes in development environment
- Document any new patterns discovered

---

**Last Updated:** 2025-09-02
**Version:** 1.0
**Author:** Kilo Code