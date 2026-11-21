# SAM AI Chatbot v2 — Frontend Component Spec

**Version:** 1.0
**Date:** 2026-11-21
**Parent:** [01-PRD.md](./01-PRD.md)

---

## 1. Overview

The frontend is a Next.js 14 (App Router) application using:
- **React 18** with Server Components where possible
- **shadcn/ui** component library (built on Radix UI primitives)
- **Tailwind CSS** for styling
- **Vercel AI SDK** (`ai` package) for SSE streaming via `useChat()`
- **Supabase Auth Helpers** for authentication state
- **Zustand** for lightweight global state (sidebar, theme)

---

## 2. Route Structure

```
app/
├── (auth)/
│   ├── login/page.tsx          # Login form
│   └── signup/page.tsx         # Signup form
├── (chat)/
│   ├── layout.tsx              # Sidebar + main area layout
│   ├── page.tsx                # Redirect to new chat or last thread
│   └── [threadId]/page.tsx     # Chat conversation view
├── settings/page.tsx           # User settings + OAuth connections
├── layout.tsx                  # Root layout (providers, theme, auth)
└── middleware.ts               # Auth guard — redirect to /login if no session
```

**Route behavior:**
| Route | Auth required | Description |
|-------|--------------|-------------|
| `/login` | No | Login form with email + Google social |
| `/signup` | No | Registration form |
| `/` | Yes | Redirect to `/[last-thread]` or new chat |
| `/[threadId]` | Yes | Chat conversation |
| `/settings` | Yes | Account settings, OAuth connections, memories |

---

## 3. Component Tree

```
RootLayout
├── ThemeProvider (next-themes)
├── AuthProvider (Supabase session context)
├── ToastProvider (shadcn/ui Sonner)
│
├── (auth routes)
│   ├── LoginPage
│   │   ├── LoginForm
│   │   │   ├── Input (email)
│   │   │   ├── Input (password)
│   │   │   ├── Button (submit)
│   │   │   └── Button (Google social login)
│   │   └── Link (to signup)
│   └── SignupPage
│       ├── SignupForm
│       │   ├── Input (email)
│       │   ├── Input (password)
│       │   ├── Input (confirm password)
│       │   └── Button (submit)
│       └── Link (to login)
│
├── (chat routes)
│   └── ChatLayout
│       ├── Sidebar
│       │   ├── SidebarHeader
│       │   │   ├── Logo
│       │   │   └── NewChatButton
│       │   ├── ThreadList
│       │   │   └── ThreadItem[] (map)
│       │   │       ├── ThreadTitle
│       │   │       └── ThreadActions (rename, delete)
│       │   └── SidebarFooter
│       │       ├── SettingsLink
│       │       └── UserAvatar + email
│       │
│       └── MainArea
│           ├── ChatHeader
│           │   ├── SidebarToggle (mobile)
│           │   ├── ThreadTitle
│           │   └── DocumentIndicator (if PDF attached)
│           │
│           ├── MessageList
│           │   ├── WelcomeScreen (when no messages)
│           │   │   ├── Logo
│           │   │   ├── Greeting
│           │   │   └── SuggestionChips[]
│           │   └── MessageBubble[] (map)
│           │       ├── UserMessage
│           │       │   └── Markdown content
│           │       └── AssistantMessage
│           │           ├── Markdown content (streaming)
│           │           ├── ToolIndicator (when tool in use)
│           │           └── CopyButton
│           │
│           └── InputArea
│               ├── FileUploadZone (drag & drop PDF)
│               ├── FilePreview (attached PDF name)
│               ├── Textarea (auto-resize)
│               ├── LocationBadge (optional)
│               └── SendButton
│
├── SettingsPage
│   ├── ProfileSection
│   │   └── email display
│   ├── ConnectionsSection
│   │   ├── ConnectionCard (Google Drive)
│   │   │   ├── ProviderIcon
│   │   │   ├── Status (connected/disconnected)
│   │   │   └── ConnectButton / DisconnectButton
│   │   └── ConnectionCard (GitHub)
│   ├── MemoriesSection
│   │   └── MemoryItem[] (map)
│   │       ├── MemoryContent
│   │       ├── MemoryCategory badge
│   │       └── DeleteButton
│   └── ThemeSection
│       └── ThemeToggle (light/dark/system)
```

---

## 4. Key Component Specifications

### 4.1 ChatLayout

The main chat layout with responsive sidebar.

**State:**
```typescript
interface ChatLayoutState {
  sidebarOpen: boolean       // Zustand store
  isMobile: boolean          // from useMediaQuery(768px)
}
```

**Behavior:**
- Desktop (>=768px): sidebar always visible, 280px wide
- Mobile (<768px): sidebar hidden by default, slides in as overlay
- Sidebar toggle button visible on mobile only

### 4.2 MessageList + useChat()

The core chat interface using Vercel AI SDK.

```typescript
const { messages, input, handleInputChange, handleSubmit, isLoading, error } = useChat({
  api: `${process.env.NEXT_PUBLIC_API_URL}/api/chat`,
  headers: {
    Authorization: `Bearer ${session.access_token}`,
  },
  body: {
    thread_id: threadId,
    location: userLocation,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  },
  onFinish: (message) => {
    // Refresh thread list if title was generated
  },
  onError: (error) => {
    toast.error(error.message)
  },
})
```

**SSE event handling:**
The Vercel AI SDK `useChat()` handles `token` events natively. Custom events (`tool_start`, `tool_end`, `memory_stored`, `done`) are parsed from the stream and dispatched to UI state:

```typescript
// Custom stream parser for non-token events
onResponse: async (response) => {
  const reader = response.body.getReader()
  // Parse SSE events, update tool indicator state
}
```

### 4.3 MessageBubble

Renders a single message (user or assistant).

**Props:**
```typescript
interface MessageBubbleProps {
  role: 'user' | 'assistant'
  content: string            // Markdown string
  isStreaming: boolean       // Show cursor animation
  toolsUsed?: string[]      // Tool names used during generation
}
```

**Rendering:**
- User messages: right-aligned, primary color background
- Assistant messages: left-aligned, muted background
- Markdown rendered with `react-markdown` + `remark-gfm`
- Code blocks with syntax highlighting via `rehype-highlight`
- Copy button appears on hover

### 4.4 InputArea

Multi-line input with file upload support.

**Props/State:**
```typescript
interface InputAreaProps {
  onSubmit: (message: string, file?: File) => void
  isLoading: boolean
  threadId: string
}

// Internal state
const [input, setInput] = useState('')
const [attachedFile, setAttachedFile] = useState<File | null>(null)
```

**Behavior:**
- `Enter` sends message, `Shift+Enter` adds newline
- Textarea auto-resizes up to 200px, then scrolls
- Drag-and-drop zone for PDF files (visual feedback on dragover)
- File preview chip shows filename + remove button when PDF attached
- Send button disabled when input is empty and no file attached
- Send button disabled while `isLoading` is true

### 4.5 Sidebar + ThreadList

Conversation history sidebar.

**Data fetching:**
```typescript
// Fetch threads on mount + after new message
const { data: threads, mutate } = useSWR(
  '/api/threads',
  fetcher,
  { revalidateOnFocus: false }
)
```

**Thread item behavior:**
- Click: navigate to `/[threadId]`
- Active thread highlighted
- Right-click or `...` menu: Rename, Delete
- Rename: inline edit with Enter to confirm, Escape to cancel
- Delete: confirmation dialog before deletion

### 4.6 WelcomeScreen

Shown when a new chat has no messages.

**Content:**
- SAM AI logo/icon
- Greeting: "How can I help you today?"
- 4 suggestion chips with example prompts:
  - "Search the web for today's top tech news"
  - "Help me debug a Python error"
  - "Summarize this PDF for me"
  - "What's the weather in my area?"
- Clicking a chip inserts the text into the input and submits

### 4.7 ToolIndicator

Shows when the AI agent is using a tool during response generation.

**Props:**
```typescript
interface ToolIndicatorProps {
  tool: string    // e.g. "tavily_search_results_json"
  label: string   // e.g. "Searching the web..."
}
```

**Rendering:**
- Appears inline in the assistant message area
- Animated spinner + label text
- Fades out when `tool_end` event received

---

## 5. State Management

### 5.1 Server State (SWR)

| Data | Key | Revalidation |
|------|-----|-------------|
| Thread list | `/api/threads` | On new message, on delete |
| Thread messages | `/api/threads/[id]` | On route change |
| User connections | `/api/auth/connections` | On settings page load |
| User memories | `/api/memories` | On settings page load |

### 5.2 Client State (Zustand)

```typescript
interface AppStore {
  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void
  
  theme: 'light' | 'dark' | 'system'
  setTheme: (theme: string) => void
}
```

### 5.3 Auth State (Supabase Context)

```typescript
interface AuthContext {
  session: Session | null      // Supabase session with access_token
  user: User | null            // User profile
  isLoading: boolean           // Initial session check
  signOut: () => Promise<void>
}
```

---

## 6. Theming

### 6.1 Color Tokens

Using CSS custom properties with Tailwind:

```css
:root {
  --background: 0 0% 100%;
  --foreground: 240 10% 3.9%;
  --card: 0 0% 100%;
  --card-foreground: 240 10% 3.9%;
  --primary: 240 5.9% 10%;
  --primary-foreground: 0 0% 98%;
  --secondary: 240 4.8% 95.9%;
  --secondary-foreground: 240 5.9% 10%;
  --muted: 240 4.8% 95.9%;
  --muted-foreground: 240 3.8% 46.1%;
  --accent: 240 4.8% 95.9%;
  --accent-foreground: 240 5.9% 10%;
  --destructive: 0 84.2% 60.2%;
  --border: 240 5.9% 90%;
  --input: 240 5.9% 90%;
  --ring: 240 5.9% 10%;
  --radius: 0.5rem;
}

.dark {
  --background: 240 10% 3.9%;
  --foreground: 0 0% 98%;
  --card: 240 10% 3.9%;
  --card-foreground: 0 0% 98%;
  --primary: 0 0% 98%;
  --primary-foreground: 240 5.9% 10%;
  --secondary: 240 3.7% 15.9%;
  --secondary-foreground: 0 0% 98%;
  --muted: 240 3.7% 15.9%;
  --muted-foreground: 240 5% 64.9%;
  --accent: 240 3.7% 15.9%;
  --accent-foreground: 0 0% 98%;
  --destructive: 0 62.8% 30.6%;
  --border: 240 3.7% 15.9%;
  --input: 240 3.7% 15.9%;
  --ring: 240 4.9% 83.9%;
}
```

### 6.2 Theme Switching

Using `next-themes` with system preference detection:

```typescript
<ThemeProvider attribute="class" defaultTheme="system" enableSystem>
  {children}
</ThemeProvider>
```

---

## 7. Responsive Breakpoints

| Breakpoint | Width | Layout changes |
|-----------|-------|---------------|
| `sm` | 640px | — |
| `md` | 768px | Sidebar becomes persistent (not overlay) |
| `lg` | 1024px | Message area max-width increases |
| `xl` | 1280px | — |

**Key responsive behaviors:**
- **<768px (mobile):** Sidebar is hidden overlay. Full-width message area. Smaller font sizes.
- **>=768px (tablet/desktop):** Sidebar permanently visible at 280px. Message area has max-width of 768px, centered.
- **Input area:** Always full-width at bottom. On mobile, sticks to bottom with safe area inset for iOS.

---

## 8. Accessibility

| Concern | Implementation |
|---------|---------------|
| Keyboard navigation | All interactive elements focusable, Enter/Space to activate |
| Screen reader | ARIA labels on icons, role="log" on message list, live region for streaming |
| Color contrast | WCAG AA minimum (4.5:1 for text, 3:1 for large text) |
| Focus management | Focus moves to new message when sent, to input after thread switch |
| Reduced motion | `prefers-reduced-motion` disables streaming cursor animation |
| Skip link | "Skip to chat" link before sidebar |

---

## 9. Dependencies

```json
{
  "dependencies": {
    "next": "^14.2",
    "react": "^18.3",
    "react-dom": "^18.3",
    "@supabase/auth-helpers-nextjs": "^0.10",
    "@supabase/supabase-js": "^2.45",
    "ai": "^3.4",
    "zustand": "^4.5",
    "swr": "^2.2",
    "react-markdown": "^9.0",
    "remark-gfm": "^4.0",
    "rehype-highlight": "^7.0",
    "next-themes": "^0.3",
    "lucide-react": "^0.400",
    "class-variance-authority": "^0.7",
    "clsx": "^2.1",
    "tailwind-merge": "^2.5"
  },
  "devDependencies": {
    "typescript": "^5.5",
    "tailwindcss": "^3.4",
    "@types/react": "^18.3",
    "@types/node": "^20"
  }
}
```

shadcn/ui components are installed via CLI (`npx shadcn-ui@latest add <component>`) and live in `components/ui/`. They are not an npm dependency.

---

## 10. File Structure

```
frontend/
├── app/
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   └── signup/page.tsx
│   ├── (chat)/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── [threadId]/page.tsx
│   ├── settings/page.tsx
│   ├── globals.css
│   ├── layout.tsx
│   └── middleware.ts
├── components/
│   ├── ui/                     # shadcn/ui primitives
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   ├── dialog.tsx
│   │   ├── dropdown-menu.tsx
│   │   ├── textarea.tsx
│   │   ├── toast.tsx
│   │   └── ...
│   ├── chat/
│   │   ├── message-list.tsx
│   │   ├── message-bubble.tsx
│   │   ├── input-area.tsx
│   │   ├── tool-indicator.tsx
│   │   ├── welcome-screen.tsx
│   │   └── chat-header.tsx
│   ├── sidebar/
│   │   ├── sidebar.tsx
│   │   ├── thread-list.tsx
│   │   ├── thread-item.tsx
│   │   └── sidebar-footer.tsx
│   ├── settings/
│   │   ├── connection-card.tsx
│   │   ├── memory-item.tsx
│   │   └── theme-toggle.tsx
│   └── auth/
│       ├── login-form.tsx
│       └── signup-form.tsx
├── lib/
│   ├── supabase.ts             # Supabase client init
│   ├── api.ts                  # Backend API client (fetch wrapper)
│   ├── store.ts                # Zustand store
│   └── utils.ts                # cn() helper, formatters
├── hooks/
│   ├── use-auth.ts             # Auth context hook
│   └── use-media-query.ts      # Responsive hook
├── public/
│   └── logo.svg
├── tailwind.config.ts
├── next.config.js
├── tsconfig.json
└── package.json
```
