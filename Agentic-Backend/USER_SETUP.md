# User Authentication Setup Guide

This guide explains how to set up and manage users for the Agentic Backend API.

## Overview

The backend now supports JWT-based authentication with the following endpoints:
- `POST /api/v1/auth/login` - OAuth2 form-based login
- `POST /api/v1/auth/login-json` - JSON-based login

## Prerequisites

1. Install the new authentication dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables in your `.env` file:
   ```env
   SECRET_KEY=your-secret-key-here
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   ```

## Database Setup

1. Run the database migration to create the users table:
   ```bash
   # If you have alembic installed
   alembic upgrade head
   
   # Or manually run the migration SQL (see alembic/versions/001_add_user_table.py)
   ```

## Creating Users

### Method 1: Using the Create User Script

Use the provided script to create users. **Important:** Run this from the project root directory:

```bash
# From the project root directory (where requirements.txt is located)
python scripts/create_user.py <username> <email> <password> [--superuser]
```

Examples:
```bash
# Make sure you're in the project root directory first
cd /path/to/Agentic-Backend

# Create a regular user
python scripts/create_user.py john john@example.com mypassword123

# Create a superuser
python scripts/create_user.py admin admin@example.com adminpass123 --superuser
```

**Troubleshooting the script:**
- Make sure you're running from the project root directory
- Ensure your virtual environment is activated: `source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`
- Check that your `.env` file has the correct `DATABASE_URL`

### Method 2: Programmatically

You can also create users programmatically in your application:

```python
from app.db.database import get_session_context
from app.db.models.user import User
from app.utils.auth import get_password_hash

async def create_user_example():
    async with get_session_context() as db:
        hashed_password = get_password_hash("userpassword")
        new_user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=False
        )
        db.add(new_user)
        await db.commit()
```

## Authentication Endpoints

### Login (Form-based)

**Endpoint:** `POST /api/v1/auth/login`

**Content-Type:** `application/x-www-form-urlencoded`

**Body:**
```
username=your_username&password=your_password
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

### Login (JSON-based)

**Endpoint:** `POST /api/v1/auth/login-json`

**Content-Type:** `application/json`

**Body:**
```json
{
  "username": "your_username",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

## Using Authentication Tokens

Once you receive an access token, include it in the Authorization header for protected endpoints:

```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

### Example with curl

```bash
# Login and get token
curl -X POST "http://localhost:8000/api/v1/auth/login-json" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'

# Use token for authenticated requests
curl -X GET "http://localhost:8000/api/v1/some-protected-endpoint" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Example with JavaScript/Frontend

```javascript
// Login
const loginResponse = await fetch('/api/v1/auth/login-json', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    username: 'your_username',
    password: 'your_password'
  })
});

const { access_token } = await loginResponse.json();

// Store token (consider security implications)
localStorage.setItem('access_token', access_token);

// Use token for subsequent requests
const apiResponse = await fetch('/api/v1/some-endpoint', {
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});
```

## Security Considerations

1. **Secret Key**: Use a strong, random secret key in production
2. **Token Expiration**: Tokens expire after 30 minutes by default
3. **HTTPS**: Always use HTTPS in production
4. **Token Storage**: Be careful about where you store tokens in frontend applications

## User Management

The user model includes the following fields:
- `id`: Unique identifier
- `username`: Unique username (max 50 characters)
- `email`: Unique email address
- `is_active`: Whether the user account is active
- `is_superuser`: Whether the user has superuser privileges
- `created_at`: Account creation timestamp
- `updated_at`: Last update timestamp

## Protecting Endpoints

To protect an endpoint with JWT authentication, use the `get_current_user` dependency:

```python
from app.api.dependencies import get_current_user
from app.db.models.user import User

@router.get("/protected-endpoint")
async def protected_endpoint(current_user: User = Depends(get_current_user)):
    return {"message": f"Hello {current_user.username}!"}
```

## Changing Passwords

### Method 1: Using the API Endpoint (Recommended for Users)

Users can change their own passwords through the authenticated API endpoint:

**Endpoint:** `POST /api/v1/auth/change-password`

**Headers:**
```
Authorization: Bearer <your_jwt_token>
Content-Type: application/json
```

**Body:**
```json
{
  "current_password": "your_current_password",
  "new_password": "your_new_password"
}
```

**Example with curl:**
```bash
# First, get your authentication token
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login-json" \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_current_password"}' | jq -r '.access_token')

# Then change your password
curl -X POST "http://localhost:8000/api/v1/auth/change-password" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "current_password": "your_current_password",
    "new_password": "your_new_secure_password"
  }'
```

### Method 2: Admin Password Change (API)

Superusers can change any user's password through the admin API endpoint:

**Endpoint:** `POST /api/v1/auth/admin/change-password`

**Headers:**
```
Authorization: Bearer <superuser_jwt_token>
Content-Type: application/json
```

**Body:**
```json
{
  "username": "target_username",
  "new_password": "new_password"
}
```

### Method 3: Admin Script (Server-Side)

For server administration, use the password change script:

```bash
# Run inside Docker container (recommended)
docker compose exec api python change_password.py <username> <new_password>

# Or run with password prompt for security
docker compose exec api python change_password.py <username>

# Examples:
docker compose exec api python change_password.py nepenthe mynewpassword123
docker compose exec api python change_password.py john  # Will prompt for password
```

**Running outside Docker:**
```bash
# Make sure you're in the project root and virtual environment is activated
source venv/bin/activate
python scripts/change_password.py <username> [new_password]
```

### Security Notes

1. **Password Requirements**: Minimum 6 characters (can be customized)
2. **Current Password**: Users must provide their current password when changing via API
3. **Admin Override**: Superusers can change any password without knowing the current one
4. **Secure Input**: The script supports secure password input (hidden typing)

## User Information

### Get Current User Info

**Endpoint:** `GET /api/v1/auth/me`

**Headers:**
```
Authorization: Bearer <your_jwt_token>
```

**Response:**
```json
{
  "id": 1,
  "username": "your_username",
  "email": "your_email@example.com",
  "is_active": true,
  "is_superuser": false
}
```

## Troubleshooting

### Common Issues

1. **"Could not validate credentials"**
   - Check that the token is properly formatted in the Authorization header
   - Ensure the token hasn't expired
   - Verify the SECRET_KEY matches what was used to sign the token

2. **"Incorrect username or password"**
   - Verify the user exists in the database
   - Check that the user account is active (`is_active=True`)
   - Confirm the password is correct

3. **Database Connection Issues**
   - Ensure the database is running and accessible
   - Verify the DATABASE_URL environment variable is correct
   - Run database migrations if needed

### Testing Authentication

You can test the authentication endpoints using the interactive API documentation at:
- `http://localhost:8000/docs` (when DEBUG=True)

This provides a web interface to test the login endpoints and see the expected request/response formats.