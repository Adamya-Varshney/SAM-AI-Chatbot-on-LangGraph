# SAM AI Chatbot v2 — Auth & OAuth Flows Spec

**Version:** 1.0
**Date:** 2026-11-21
**Parent:** [01-PRD.md](./01-PRD.md)

---

## 1. Overview

Two separate auth systems:

1. **User authentication** — Supabase Auth (email/password + Google social login). Identifies users and scopes their data.
2. **MCP OAuth connections** — Google Drive and GitHub OAuth. Per-user tokens stored in the database, used by the backend to connect MCP servers on the user's behalf.

---

## 2. User Authentication (Supabase Auth)

### 2.1 Setup

Supabase Auth is configured in the Supabase dashboard:
- **Email/password** provider: enabled
- **Google** social login: enabled (uses the same Google Cloud OAuth credentials, but with Supabase as the redirect target)
- **Email confirmation**: enabled (sends verification email)
- **JWT expiry**: 3600 seconds (1 hour)
- **Refresh token rotation**: enabled

### 2.2 Signup Flow

```
Frontend (Next.js)                    Supabase Auth
       |                                    |
       |-- supabase.auth.signUp({          |
       |     email, password             }) |
       |-------------------------------------->
       |                                    |-- create user in auth.users
       |                                    |-- send verification email
       |<--------------------------------------
       |   { user, session: null }          |
       |                                    |
       |-- show "Check your email"          |
       |                                    |
       |   [user clicks email link]         |
       |-------------------------------------->
       |                                    |-- verify email
       |<--------------------------------------
       |   redirect to /login?verified=true |
```

### 2.3 Login Flow

```
Frontend (Next.js)                    Supabase Auth              Backend (FastAPI)
       |                                    |                          |
       |-- supabase.auth.signInWithPassword |                          |
       |     ({ email, password })          |                          |
       |-------------------------------------->                        |
       |                                    |-- validate credentials   |
       |<--------------------------------------                        |
       |   { session: {                     |                          |
       |       access_token,                |                          |
       |       refresh_token,               |                          |
       |       expires_at                   |                          |
       |   }}                               |                          |
       |                                    |                          |
       |-- store tokens in memory           |                          |
       |-- set httpOnly cookie via          |                          |
       |   Next.js API route                |                          |
       |                                    |                          |
       |-- GET /api/threads ---------------------------------->        |
       |   Authorization: Bearer <token>    |                          |
       |                                    |              validate JWT|
       |                                    |              extract uid |
       |<-------------------------------------------------------------|
       |   { threads: [...] }               |                          |
```

### 2.4 Google Social Login Flow

```
Frontend                          Supabase Auth              Google
    |                                  |                        |
    |-- supabase.auth.signInWithOAuth  |                        |
    |     ({ provider: 'google' })     |                        |
    |--------------------------------->|                        |
    |                                  |-- redirect to Google -->|
    |   [browser redirects]            |                        |
    |                                  |                        |
    |   [user consents]                |                        |
    |                                  |<-- auth code ----------|
    |                                  |-- exchange for tokens  |
    |                                  |-- create/link user     |
    |<---------------------------------|                        |
    |   redirect to app with session   |                        |
```

### 2.5 Token Refresh

```
Frontend                          Supabase Auth
    |                                  |
    |-- [access_token expired]         |
    |                                  |
    |-- supabase.auth.refreshSession() |
    |--------------------------------->|
    |                                  |-- validate refresh_token
    |                                  |-- issue new access_token
    |                                  |-- rotate refresh_token
    |<---------------------------------|
    |   { session: { new tokens } }    |
```

The Supabase client library handles this automatically via `onAuthStateChange` listener. The frontend wraps API calls to retry on 401 after a token refresh.

### 2.6 JWT Validation (Backend)

The backend validates JWTs without calling Supabase:

```python
from jose import jwt, JWTError

SUPABASE_JWT_SECRET = os.environ["SUPABASE_JWT_SECRET"]

def get_current_user(authorization: str) -> dict:
    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return {
            "user_id": payload["sub"],
            "email": payload.get("email"),
            "role": payload.get("role"),
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

**JWT claims used:**
| Claim | Type | Purpose |
|-------|------|---------|
| `sub` | UUID | user_id for all database queries |
| `email` | string | Display in UI, logging |
| `role` | string | Must be "authenticated" |
| `exp` | timestamp | Reject expired tokens |
| `aud` | string | Must be "authenticated" |

### 2.7 Logout

```
Frontend                          Supabase Auth
    |                                  |
    |-- supabase.auth.signOut()        |
    |--------------------------------->|
    |                                  |-- invalidate refresh_token
    |<---------------------------------|
    |                                  |
    |-- clear local tokens             |
    |-- clear httpOnly cookie          |
    |-- redirect to /login             |
```

---

## 3. MCP OAuth Connections

These are separate from user auth. They let the backend access Google Drive and GitHub on the user's behalf via MCP servers.

### 3.1 Google Drive OAuth

**Google Cloud Console setup:**
- Create OAuth 2.0 Client ID (Web application type)
- Authorized redirect URI: `https://<railway-host>/api/auth/callback/google`
- Scopes: `https://www.googleapis.com/auth/drive.readonly`

**Connect flow:**

```
Frontend              Backend (FastAPI)                    Google OAuth
    |                        |                                  |
    |-- click "Connect       |                                  |
    |   Google Drive"        |                                  |
    |                        |                                  |
    |-- GET /api/auth/connect/google ------>                    |
    |                        |                                  |
    |                        |-- build OAuth URL:               |
    |                        |   client_id                      |
    |                        |   redirect_uri                   |
    |                        |   scope: drive.readonly          |
    |                        |   access_type: offline           |
    |                        |   state: encrypt(user_id+nonce)  |
    |                        |                                  |
    |<-- 302 redirect -------|                                  |
    |                        |                                  |
    |-- [browser goes to Google consent page] ----------------->|
    |                        |                                  |
    |   [user clicks Allow]  |                                  |
    |                        |                                  |
    |<-- redirect to callback with code ------------------------|
    |                        |                                  |
    |-- GET /api/auth/callback/google?code=...&state=... ------>|
    |                        |                                  |
    |                        |-- decrypt state, verify nonce    |
    |                        |-- POST token exchange ---------->|
    |                        |<-- access_token, refresh_token --|
    |                        |                                  |
    |                        |-- encrypt tokens                 |
    |                        |-- INSERT into user_oauth_tokens  |
    |                        |                                  |
    |<-- 302 redirect to /settings?connected=google             |
```

**Key parameters:**
| Parameter | Value | Why |
|-----------|-------|-----|
| `access_type` | `offline` | Gets a refresh_token for unattended access |
| `prompt` | `consent` | Forces consent screen even if previously approved (ensures refresh_token) |
| `state` | encrypted payload | CSRF protection + carries user_id through redirect |

### 3.2 GitHub OAuth

**GitHub OAuth App setup:**
- Create at github.com/settings/developers
- Authorization callback URL: `https://<railway-host>/api/auth/callback/github`
- Scopes: `repo`, `read:user`

**Connect flow:** Same pattern as Google, with differences:

| Aspect | Google | GitHub |
|--------|--------|--------|
| Token endpoint | `https://oauth2.googleapis.com/token` | `https://github.com/login/oauth/access_token` |
| Refresh token | Yes — access_token expires in 1 hour | No — token doesn't expire |
| Scopes | `drive.readonly` | `repo`, `read:user` |
| Token format | Bearer token | Bearer token |

### 3.3 Disconnect Flow

```
Frontend              Backend (FastAPI)
    |                        |
    |-- DELETE /api/auth/disconnect/google -->|
    |                        |
    |                        |-- DELETE FROM user_oauth_tokens
    |                        |   WHERE user_id = $1 AND provider = 'google'
    |                        |
    |<-- 200 { disconnected: true } ---------|
```

Optionally, the backend also revokes the token at the provider:
- Google: `POST https://oauth2.googleapis.com/revoke?token=<access_token>`
- GitHub: `DELETE https://api.github.com/applications/<client_id>/token`

### 3.4 Token Refresh (Google)

Google access tokens expire after 1 hour. The backend refreshes automatically when needed:

```python
async def get_google_token(user_id: str) -> str:
    row = db.execute(
        "SELECT access_token, refresh_token, token_expiry FROM user_oauth_tokens "
        "WHERE user_id = %s AND provider = 'google'",
        (user_id,),
    ).fetchone()

    if not row:
        return None

    access_token = decrypt(row["access_token"])
    refresh_token = decrypt(row["refresh_token"])
    expiry = row["token_expiry"]

    if expiry and expiry > datetime.utcnow() + timedelta(minutes=5):
        return access_token

    # Token expired or expiring soon — refresh it
    new_tokens = refresh_google_token(refresh_token)

    db.execute(
        "UPDATE user_oauth_tokens SET access_token = %s, token_expiry = %s, updated_at = now() "
        "WHERE user_id = %s AND provider = 'google'",
        (encrypt(new_tokens["access_token"]), new_tokens["expires_at"], user_id),
    )

    return new_tokens["access_token"]
```

---

## 4. Token Encryption

OAuth tokens are encrypted at rest using AES-256-GCM:

```python
from cryptography.fernet import Fernet

ENCRYPTION_KEY = os.environ["ENCRYPTION_KEY"]  # Fernet key (base64-encoded 32 bytes)
fernet = Fernet(ENCRYPTION_KEY)

def encrypt(plaintext: str) -> str:
    return fernet.encrypt(plaintext.encode()).decode()

def decrypt(ciphertext: str) -> str:
    return fernet.decrypt(ciphertext.encode()).decode()
```

**Key management:**
- `ENCRYPTION_KEY` stored as Railway environment variable
- Generated once: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- Never stored in code or database
- If compromised: generate new key, re-encrypt all tokens in a migration

---

## 5. Security Checklist

| Concern | Mitigation |
|---------|-----------|
| CSRF on OAuth | `state` parameter with encrypted nonce, verified on callback |
| Token theft from DB | AES-256-GCM encryption at rest |
| JWT replay | Short expiry (1 hour) + audience validation |
| XSS token theft | httpOnly cookies for refresh token, access token in memory only |
| Open redirect | Callback URLs hardcoded, not from user input |
| Scope escalation | Minimal scopes requested (drive.readonly, repo) |
| Token in logs | Tokens never logged; only user_id and provider |

---

## 6. Frontend Auth State Management

Using Supabase client library with Next.js:

```typescript
// lib/supabase.ts — client-side instance
import { createBrowserSupabaseClient } from '@supabase/auth-helpers-nextjs'

// Layout wrapper — listens for auth changes
supabase.auth.onAuthStateChange((event, session) => {
  if (event === 'SIGNED_IN') {
    // Store session, redirect to chat
  }
  if (event === 'SIGNED_OUT') {
    // Clear state, redirect to login
  }
  if (event === 'TOKEN_REFRESHED') {
    // Update stored access token
  }
})
```

**Protected routes:** Next.js middleware checks for a valid session cookie and redirects to `/login` if missing:

```typescript
// middleware.ts
export async function middleware(req: NextRequest) {
  const session = await getSession(req)
  if (!session && !req.nextUrl.pathname.startsWith('/login')) {
    return NextResponse.redirect(new URL('/login', req.url))
  }
}
```

---

## 7. Environment Variables Summary

| Variable | Where | Purpose |
|----------|-------|---------|
| `NEXT_PUBLIC_SUPABASE_URL` | Vercel | Supabase project URL (public) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Vercel | Supabase anon key (public, safe for client) |
| `SUPABASE_JWT_SECRET` | Railway | Validate JWTs server-side |
| `SUPABASE_DB_URL` | Railway | Direct PostgreSQL connection |
| `GOOGLE_CLIENT_ID` | Railway | Google OAuth (MCP connection) |
| `GOOGLE_CLIENT_SECRET` | Railway | Google OAuth (MCP connection) |
| `GITHUB_CLIENT_ID` | Railway | GitHub OAuth (MCP connection) |
| `GITHUB_CLIENT_SECRET` | Railway | GitHub OAuth (MCP connection) |
| `ENCRYPTION_KEY` | Railway | Fernet key for token encryption |
| `FRONTEND_URL` | Railway | Allowed CORS origin + OAuth redirect base |
