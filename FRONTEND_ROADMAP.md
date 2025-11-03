# 🎨 ROADMAP FRONTEND - OHAD'AI Expert-Comptable

## 📋 Document de Référence

**Objectif**: Remplacer Streamlit par une application Vite.js full responsive
**Stack**: Vite.js + React + TypeScript + Tailwind CSS + shadcn/ui
**Timeline**: 7-8 semaines après finalisation backend

---

## 🎯 OBJECTIFS FRONTEND

### Vision

Créer une application web moderne, **full responsive**, **performante** et **accessible** pour remplacer l'interface Streamlit actuelle, avec une expérience utilisateur de qualité professionnelle adaptée à tous les supports (mobile, tablette, desktop).

### Contraintes Techniques

```yaml
Compatibilité:
  - Navigateurs: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
  - Mobile: iOS 14+, Android 8+
  - Tablets: iPad, Android tablets

Performance:
  - First Contentful Paint: < 1.5s
  - Time to Interactive: < 3.5s
  - Lighthouse Score: > 90/100

Accessibilité:
  - WCAG 2.1 Level AA
  - Screen reader compatible
  - Keyboard navigation

Responsive:
  - Mobile: 320px - 768px
  - Tablet: 768px - 1024px
  - Desktop: 1024px+
```

---

## 🏗️ ARCHITECTURE FRONTEND

### Stack Technique Complète

```yaml
Core:
  Build Tool: Vite 5.x
  Framework: React 18.x
  Language: TypeScript 5.x
  Package Manager: pnpm (recommandé) ou npm

UI & Styling:
  CSS Framework: Tailwind CSS 3.x
  Component Library: shadcn/ui (headless, accessible)
  Icons: Lucide React
  Animations: Framer Motion

State Management:
  Global State: Zustand 4.x (léger et simple)
  Server State: TanStack Query v5 (React Query)
  Form State: React Hook Form

Routing & Navigation:
  Router: React Router v6
  URL State: Use query params for filters

Data Fetching:
  HTTP Client: Axios
  API Layer: TanStack Query (caching, refetching)
  Real-time: EventSource API (SSE)

Forms & Validation:
  Forms: React Hook Form
  Validation: Zod
  Auto-complete: Downshift

Content Rendering:
  Markdown: react-markdown
  Code Highlighting: Prism React Renderer
  Math: KaTeX (si nécessaire)

Testing:
  Unit: Vitest + Testing Library
  E2E: Playwright
  Coverage: Vitest coverage

Code Quality:
  Linting: ESLint
  Formatting: Prettier
  Type Checking: TypeScript strict mode
  Pre-commit: Husky + lint-staged

PWA:
  Service Worker: Vite PWA Plugin
  Offline: Workbox
  Manifest: Auto-generated

Build & Deploy:
  Build: Vite build
  Preview: Vite preview
  CI/CD: GitHub Actions
  Hosting: Nginx (self-hosted) ou Vercel/Netlify
```

### Structure des Dossiers

```
frontend/
├── public/
│   ├── icons/                    # PWA icons
│   ├── manifest.json             # PWA manifest
│   └── robots.txt
│
├── src/
│   ├── app/                      # Application entry
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── router.tsx
│   │
│   ├── pages/                    # Pages/Routes
│   │   ├── HomePage.tsx
│   │   ├── SearchPage.tsx
│   │   ├── ConversationsPage.tsx
│   │   ├── ConversationDetailPage.tsx
│   │   ├── DocumentsPage.tsx    # NEW (admin)
│   │   ├── AdminPage.tsx        # NEW (analytics)
│   │   ├── LoginPage.tsx
│   │   ├── RegisterPage.tsx
│   │   ├── ProfilePage.tsx
│   │   └── NotFoundPage.tsx
│   │
│   ├── components/               # Composants
│   │   ├── ui/                   # shadcn/ui base components
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   ├── card.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── dropdown-menu.tsx
│   │   │   ├── tabs.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── skeleton.tsx
│   │   │   └── ...
│   │   │
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── MobileNav.tsx
│   │   │   ├── Footer.tsx
│   │   │   └── Layout.tsx
│   │   │
│   │   ├── search/
│   │   │   ├── SearchBar.tsx
│   │   │   ├── SearchFilters.tsx # NEW (filtres avancés)
│   │   │   ├── SearchResults.tsx
│   │   │   ├── SourceCard.tsx
│   │   │   ├── StreamingAnswer.tsx
│   │   │   └── ExampleQuestions.tsx
│   │   │
│   │   ├── conversations/
│   │   │   ├── ConversationList.tsx
│   │   │   ├── ConversationItem.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── MessageList.tsx
│   │   │   └── NewConversationDialog.tsx
│   │   │
│   │   ├── documents/           # NEW (gestion documents)
│   │   │   ├── DocumentList.tsx
│   │   │   ├── DocumentCard.tsx
│   │   │   ├── DocumentUpload.tsx
│   │   │   ├── DocumentViewer.tsx
│   │   │   └── DocumentVersions.tsx
│   │   │
│   │   ├── admin/               # NEW (analytics)
│   │   │   ├── Dashboard.tsx
│   │   │   ├── StatsCard.tsx
│   │   │   ├── UsageChart.tsx
│   │   │   └── UserManagement.tsx
│   │   │
│   │   └── common/
│   │       ├── LoadingSpinner.tsx
│   │       ├── ErrorBoundary.tsx
│   │       ├── ProgressBar.tsx
│   │       ├── Markdown.tsx
│   │       ├── Avatar.tsx
│   │       ├── Toast.tsx
│   │       └── ThemeToggle.tsx
│   │
│   ├── features/                 # Features avec logique métier
│   │   ├── auth/
│   │   │   ├── hooks/
│   │   │   │   ├── useAuth.ts
│   │   │   │   ├── useLogin.ts
│   │   │   │   └── useRegister.ts
│   │   │   ├── services/
│   │   │   │   └── authService.ts
│   │   │   ├── types.ts
│   │   │   └── utils.ts
│   │   │
│   │   ├── search/
│   │   │   ├── hooks/
│   │   │   │   ├── useSearch.ts
│   │   │   │   ├── useStreamingSearch.ts
│   │   │   │   └── useAdvancedSearch.ts  # NEW
│   │   │   ├── services/
│   │   │   │   └── searchService.ts
│   │   │   ├── types.ts
│   │   │   └── utils.ts
│   │   │
│   │   ├── conversations/
│   │   │   ├── hooks/
│   │   │   │   ├── useConversations.ts
│   │   │   │   ├── useMessages.ts
│   │   │   │   └── useConversationDetail.ts
│   │   │   ├── services/
│   │   │   │   └── conversationService.ts
│   │   │   ├── types.ts
│   │   │   └── utils.ts
│   │   │
│   │   └── documents/          # NEW
│   │       ├── hooks/
│   │       │   ├── useDocuments.ts
│   │       │   ├── useDocumentUpload.ts
│   │       │   └── useDocumentVersions.ts
│   │       ├── services/
│   │       │   └── documentService.ts
│   │       ├── types.ts
│   │       └── utils.ts
│   │
│   ├── lib/                      # Utilitaires & config
│   │   ├── api/
│   │   │   ├── axios.ts          # Config Axios
│   │   │   ├── queryClient.ts    # TanStack Query config
│   │   │   ├── endpoints.ts      # API endpoints constants
│   │   │   └── sse.ts            # SSE helper
│   │   │
│   │   ├── utils/
│   │   │   ├── cn.ts             # classnames utility (shadcn)
│   │   │   ├── formatters.ts     # Date, number formatting
│   │   │   ├── validators.ts     # Validation helpers
│   │   │   └── storage.ts        # localStorage wrapper
│   │   │
│   │   └── constants.ts
│   │
│   ├── stores/                   # State management
│   │   ├── authStore.ts
│   │   ├── searchStore.ts
│   │   ├── themeStore.ts
│   │   └── conversationStore.ts
│   │
│   ├── hooks/                    # Custom hooks globaux
│   │   ├── useDebounce.ts
│   │   ├── useIntersectionObserver.ts
│   │   ├── useLocalStorage.ts
│   │   ├── useMediaQuery.ts
│   │   └── useOnClickOutside.ts
│   │
│   ├── styles/                   # Styles globaux
│   │   ├── globals.css
│   │   └── themes.css
│   │
│   └── types/                    # Types TypeScript globaux
│       ├── api.ts
│       ├── models.ts
│       └── env.d.ts
│
├── tests/                        # Tests
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── .env.development
├── .env.production
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
├── .eslintrc.json
├── .prettierrc
└── README.md
```

---

## 🎨 DESIGN SYSTEM

### Palette de Couleurs

```css
/* Design system OHADA */

:root {
  /* Primary - Vert OHADA */
  --primary-50: #f0fdf4;
  --primary-100: #dcfce7;
  --primary-200: #bbf7d0;
  --primary-300: #86efac;
  --primary-400: #4ade80;
  --primary-500: #0e766e;  /* Main brand color */
  --primary-600: #0c6460;
  --primary-700: #0a5450;
  --primary-800: #084340;
  --primary-900: #063630;

  /* Neutral - Gris */
  --neutral-50: #fafafa;
  --neutral-100: #f5f5f5;
  --neutral-200: #e5e5e5;
  --neutral-300: #d4d4d4;
  --neutral-400: #a3a3a3;
  --neutral-500: #737373;
  --neutral-600: #525252;
  --neutral-700: #404040;
  --neutral-800: #262626;
  --neutral-900: #171717;

  /* Semantic colors */
  --success: #22c55e;
  --warning: #f59e0b;
  --error: #ef4444;
  --info: #3b82f6;

  /* Backgrounds */
  --bg-primary: #ffffff;
  --bg-secondary: #f9fafb;
  --bg-tertiary: #f3f4f6;

  /* Text */
  --text-primary: #1e293b;
  --text-secondary: #64748b;
  --text-tertiary: #94a3b8;

  /* Borders */
  --border-color: #e2e8f0;
  --border-hover: #cbd5e1;

  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
}

/* Dark mode */
[data-theme="dark"] {
  --bg-primary: #0f172a;
  --bg-secondary: #1e293b;
  --bg-tertiary: #334155;

  --text-primary: #f1f5f9;
  --text-secondary: #cbd5e1;
  --text-tertiary: #94a3b8;

  --border-color: #334155;
  --border-hover: #475569;
}
```

### Typography

```css
/* Typographie */

font-family:
  - Primary: Inter, system-ui, -apple-system, sans-serif
  - Monospace: 'JetBrains Mono', 'Fira Code', monospace

font-sizes:
  - xs: 0.75rem (12px)
  - sm: 0.875rem (14px)
  - base: 1rem (16px)
  - lg: 1.125rem (18px)
  - xl: 1.25rem (20px)
  - 2xl: 1.5rem (24px)
  - 3xl: 1.875rem (30px)
  - 4xl: 2.25rem (36px)

font-weights:
  - normal: 400
  - medium: 500
  - semibold: 600
  - bold: 700

line-heights:
  - tight: 1.25
  - normal: 1.5
  - relaxed: 1.75
```

### Spacing System

```javascript
// Tailwind spacing (rem)
const spacing = {
  0: '0',
  1: '0.25rem',   // 4px
  2: '0.5rem',    // 8px
  3: '0.75rem',   // 12px
  4: '1rem',      // 16px
  5: '1.25rem',   // 20px
  6: '1.5rem',    // 24px
  8: '2rem',      // 32px
  10: '2.5rem',   // 40px
  12: '3rem',     // 48px
  16: '4rem',     // 64px
  20: '5rem',     // 80px
  24: '6rem',     // 96px
  32: '8rem',     // 128px
}
```

### Breakpoints

```javascript
// Responsive breakpoints
const breakpoints = {
  sm: '640px',   // Mobile landscape
  md: '768px',   // Tablet
  lg: '1024px',  // Desktop
  xl: '1280px',  // Large desktop
  '2xl': '1536px' // Extra large
}
```

---

## 📱 RESPONSIVE DESIGN

### Layout Adaptatif

```typescript
// Layout par breakpoint

Mobile (< 640px):
  - Navigation: Bottom tab bar
  - Search: Full-screen modal
  - Sources: Accordion/collapsed
  - Conversations: Full-screen list
  - Messages: Full-screen thread

Tablet (640px - 1024px):
  - Navigation: Sidebar collapsible
  - Search: Main area
  - Sources: Grid 2 columns
  - Conversations: Slide-over panel

Desktop (> 1024px):
  - Navigation: Permanent sidebar
  - Search: Central column
  - Sources: Right panel (3-column layout)
  - Conversations: Left panel
```

### Composants Responsifs

```tsx
// Exemple: SearchBar responsive

interface SearchBarProps {
  onSearch: (query: string) => void;
}

const SearchBar: React.FC<SearchBarProps> = ({ onSearch }) => {
  const isMobile = useMediaQuery('(max-width: 640px)');

  return (
    <div className={cn(
      "search-bar",
      isMobile ? "fixed bottom-0 left-0 right-0 p-4" : "relative w-full"
    )}>
      <input
        type="text"
        placeholder={isMobile ? "Rechercher..." : "Posez votre question sur le plan comptable OHADA"}
        className={cn(
          "w-full rounded-lg border px-4",
          isMobile ? "py-3 text-base" : "py-2 text-sm"
        )}
        onChange={(e) => onSearch(e.target.value)}
      />
    </div>
  );
};
```

---

## 🔌 INTÉGRATION API

### Configuration Axios

```typescript
// src/lib/api/axios.ts

import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Intercepteur pour JWT
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Intercepteur pour refresh token
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Try to refresh token
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        const response = await axios.post('/auth/refresh', { refresh_token: refreshToken });

        localStorage.setItem('access_token', response.data.access_token);

        // Retry original request
        return apiClient(error.config);
      } catch {
        // Redirect to login
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

### TanStack Query Setup

```typescript
// src/lib/api/queryClient.ts

import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
});
```

### Hooks API

```typescript
// src/features/search/hooks/useSearch.ts

import { useQuery, useMutation } from '@tanstack/react-query';
import { searchService } from '../services/searchService';
import type { SearchQuery, SearchResult } from '../types';

export const useSearch = (query: string, options?: SearchOptions) => {
  return useQuery({
    queryKey: ['search', query, options],
    queryFn: () => searchService.search(query, options),
    enabled: query.length > 0,
    staleTime: 10 * 60 * 1000, // Cache 10 minutes
  });
};

export const useStreamingSearch = () => {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamedResponse, setStreamedResponse] = useState('');

  const search = useCallback(async (query: string) => {
    setIsStreaming(true);
    setStreamedResponse('');

    const eventSource = new EventSource(
      `/api/v1/query/stream?query=${encodeURIComponent(query)}`
    );

    eventSource.addEventListener('chunk', (e) => {
      const data = JSON.parse(e.data);
      setStreamedResponse(prev => prev + data.text);
    });

    eventSource.addEventListener('complete', (e) => {
      setIsStreaming(false);
      eventSource.close();
    });

    eventSource.addEventListener('error', (e) => {
      setIsStreaming(false);
      eventSource.close();
    });

    return () => eventSource.close();
  }, []);

  return { search, isStreaming, streamedResponse };
};
```

---

## 🧩 COMPOSANTS CLÉS

### 1. StreamingAnswer Component

```tsx
// src/components/search/StreamingAnswer.tsx

import React, { useEffect, useState } from 'react';
import { Markdown } from '@/components/common/Markdown';
import { ProgressBar } from '@/components/common/ProgressBar';

interface StreamingAnswerProps {
  query: string;
  onComplete?: (answer: string) => void;
}

export const StreamingAnswer: React.FC<StreamingAnswerProps> = ({
  query,
  onComplete
}) => {
  const [answer, setAnswer] = useState('');
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<'analyzing' | 'retrieving' | 'generating'>('analyzing');

  useEffect(() => {
    const eventSource = new EventSource(
      `/api/v1/query/stream?query=${encodeURIComponent(query)}`
    );

    eventSource.addEventListener('progress', (e) => {
      const data = JSON.parse(e.data);
      setProgress(data.completion * 100);
      setStatus(data.status);
    });

    eventSource.addEventListener('chunk', (e) => {
      const data = JSON.parse(e.data);
      setAnswer(prev => prev + data.text);
    });

    eventSource.addEventListener('complete', (e) => {
      const data = JSON.parse(e.data);
      setAnswer(data.answer);
      setProgress(100);
      onComplete?.(data.answer);
      eventSource.close();
    });

    return () => eventSource.close();
  }, [query]);

  return (
    <div className="streaming-answer">
      <ProgressBar value={progress} status={status} />
      <div className="mt-4 prose prose-slate max-w-none">
        <Markdown content={answer} />
        {progress < 100 && <span className="animate-pulse">▊</span>}
      </div>
    </div>
  );
};
```

### 2. SourceCard Component

```tsx
// src/components/search/SourceCard.tsx

import React from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { Source } from '@/features/search/types';

interface SourceCardProps {
  source: Source;
  index: number;
}

export const SourceCard: React.FC<SourceCardProps> = ({ source, index }) => {
  return (
    <Card className="source-card p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <Badge variant="secondary">{index + 1}</Badge>
          <h3 className="font-semibold text-sm">{source.metadata.title}</h3>
        </div>
        <span className="text-xs text-muted-foreground">
          Score: {(source.relevance_score * 100).toFixed(0)}%
        </span>
      </div>

      <div className="text-xs text-muted-foreground mb-2">
        {source.metadata.partie && `Partie ${source.metadata.partie}`}
        {source.metadata.chapitre && ` • Chapitre ${source.metadata.chapitre}`}
      </div>

      <p className="text-sm text-foreground/80 line-clamp-3">
        {source.preview}
      </p>
    </Card>
  );
};
```

### 3. SearchBar with Autocomplete

```tsx
// src/components/search/SearchBar.tsx

import React, { useState } from 'react';
import { useDebounce } from '@/hooks/useDebounce';
import { useSuggestions } from '@/features/search/hooks/useSuggestions';

export const SearchBar: React.FC = () => {
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, 300);

  const { data: suggestions } = useSuggestions(debouncedQuery);

  return (
    <div className="relative">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Posez votre question..."
        className="w-full px-4 py-3 rounded-lg border focus:ring-2 focus:ring-primary"
      />

      {suggestions && suggestions.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-white border rounded-lg shadow-lg z-10">
          {suggestions.map((suggestion, i) => (
            <button
              key={i}
              onClick={() => setQuery(suggestion.text)}
              className="w-full px-4 py-2 text-left hover:bg-gray-50 flex items-center justify-between"
            >
              <span>{suggestion.text}</span>
              <span className="text-xs text-gray-400">{suggestion.count}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
```

---

## 📊 PAGES PRINCIPALES

### 1. HomePage / SearchPage

```tsx
// src/pages/SearchPage.tsx

import React, { useState } from 'react';
import { SearchBar } from '@/components/search/SearchBar';
import { SearchFilters } from '@/components/search/SearchFilters';
import { StreamingAnswer } from '@/components/search/StreamingAnswer';
import { SourceCard } from '@/components/search/SourceCard';
import { ExampleQuestions } from '@/components/search/ExampleQuestions';

export const SearchPage: React.FC = () => {
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState({});

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8 text-center">
          OHAD'AI Expert-Comptable
        </h1>

        <SearchBar onSearch={setQuery} />

        {!query && <ExampleQuestions onSelect={setQuery} />}

        {query && (
          <>
            <SearchFilters onChange={setFilters} />
            <StreamingAnswer query={query} />
            {/* Sources will be shown after response completes */}
          </>
        )}
      </div>
    </div>
  );
};
```

### 2. ConversationsPage

```tsx
// src/pages/ConversationsPage.tsx

import React from 'react';
import { useConversations } from '@/features/conversations/hooks/useConversations';
import { ConversationList } from '@/components/conversations/ConversationList';
import { Button } from '@/components/ui/button';

export const ConversationsPage: React.FC = () => {
  const { data: conversations, isLoading } = useConversations();

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Mes Conversations</h1>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Nouvelle conversation
        </Button>
      </div>

      {isLoading ? (
        <LoadingSpinner />
      ) : (
        <ConversationList conversations={conversations} />
      )}
    </div>
  );
};
```

### 3. DocumentsPage (Admin)

```tsx
// src/pages/DocumentsPage.tsx

import React from 'react';
import { useDocuments } from '@/features/documents/hooks/useDocuments';
import { DocumentList } from '@/components/documents/DocumentList';
import { DocumentUpload } from '@/components/documents/DocumentUpload';

export const DocumentsPage: React.FC = () => {
  const { data: documents, isLoading } = useDocuments();

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Gestion des Documents</h1>
        <DocumentUpload />
      </div>

      {isLoading ? (
        <LoadingSpinner />
      ) : (
        <DocumentList documents={documents} />
      )}
    </div>
  );
};
```

---

## ⚡ OPTIMISATIONS PERFORMANCE

### Code Splitting

```typescript
// src/app/router.tsx

import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';

// Pages lazy loaded
const SearchPage = lazy(() => import('@/pages/SearchPage'));
const ConversationsPage = lazy(() => import('@/pages/ConversationsPage'));
const DocumentsPage = lazy(() => import('@/pages/DocumentsPage'));

export const AppRouter = () => (
  <BrowserRouter>
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        <Route path="/" element={<SearchPage />} />
        <Route path="/conversations" element={<ConversationsPage />} />
        <Route path="/documents" element={<DocumentsPage />} />
      </Routes>
    </Suspense>
  </BrowserRouter>
);
```

### Image Optimization

```typescript
// src/components/common/OptimizedImage.tsx

interface OptimizedImageProps {
  src: string;
  alt: string;
  width?: number;
  height?: number;
}

export const OptimizedImage: React.FC<OptimizedImageProps> = ({
  src,
  alt,
  width,
  height
}) => {
  return (
    <img
      src={src}
      alt={alt}
      width={width}
      height={height}
      loading="lazy"
      decoding="async"
      className="object-cover"
    />
  );
};
```

### PWA Configuration

```typescript
// vite.config.ts

import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: "OHAD'AI Expert-Comptable",
        short_name: "OHAD'AI",
        description: "Assistant expert-comptable OHADA",
        theme_color: '#0e766e',
        icons: [
          {
            src: 'icon-192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'icon-512.png',
            sizes: '512x512',
            type: 'image/png'
          }
        ]
      },
      workbox: {
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/api\.ohada\.com\/.*/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 60 * 60 // 1 hour
              }
            }
          }
        ]
      }
    })
  ]
});
```

---

## 🧪 TESTS

### Test Unitaire (Vitest)

```typescript
// src/components/search/SearchBar.test.tsx

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SearchBar } from './SearchBar';

describe('SearchBar', () => {
  it('should render search input', () => {
    render(<SearchBar onSearch={vi.fn()} />);
    const input = screen.getByPlaceholderText(/rechercher/i);
    expect(input).toBeInTheDocument();
  });

  it('should call onSearch when typing', () => {
    const onSearch = vi.fn();
    render(<SearchBar onSearch={onSearch} />);

    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'test query' } });

    expect(onSearch).toHaveBeenCalledWith('test query');
  });
});
```

### Test E2E (Playwright)

```typescript
// tests/e2e/search.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Search functionality', () => {
  test('should search and display results', async ({ page }) => {
    await page.goto('/');

    // Enter search query
    await page.fill('input[placeholder*="question"]', 'amortissement');
    await page.press('input[placeholder*="question"]', 'Enter');

    // Wait for streaming to complete
    await page.waitForSelector('.streaming-answer');

    // Check answer is displayed
    const answer = await page.textContent('.streaming-answer');
    expect(answer).toBeTruthy();
    expect(answer).toContain('amortissement');

    // Check sources are displayed
    const sources = await page.$$('.source-card');
    expect(sources.length).toBeGreaterThan(0);
  });
});
```

---

## 📦 DÉPLOIEMENT

### Build Production

```bash
# Build optimisé
pnpm build

# Preview build
pnpm preview

# Analyze bundle
pnpm run build -- --analyze
```

### Nginx Configuration

```nginx
# /etc/nginx/sites-available/ohada-frontend

server {
    listen 80;
    server_name ohada-ai.com;

    root /var/www/ohada/frontend/dist;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API proxy
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### Docker (Optional)

```dockerfile
# frontend/Dockerfile

FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

---

## ⏱️ TIMELINE DÉTAILLÉE

### Semaine 1-2: Setup & Infrastructure

```bash
✓ Initialiser projet Vite + React + TypeScript
✓ Configurer Tailwind CSS + shadcn/ui
✓ Setup ESLint, Prettier, Husky
✓ Configurer TanStack Query + Axios
✓ Créer structure dossiers
✓ Setup routing (React Router)
✓ Implémenter layout de base (Header, Sidebar, Footer)
✓ Implémenter système de thème (dark/light)
```

### Semaine 3-4: Authentification & Pages Core

```bash
✓ Page Login/Register
✓ Intégration API auth (JWT)
✓ Context/Store auth (Zustand)
✓ Protected routes
✓ Page Home/Search
✓ SearchBar component
✓ ExampleQuestions component
✓ Tests unitaires auth
```

### Semaine 5-6: Features Recherche & Streaming

```bash
✓ StreamingAnswer component
✓ Hook useStreamingSearch
✓ SourceCard component
✓ SearchResults component
✓ Filtres avancés (partie, chapitre)
✓ Auto-complete/suggestions
✓ Markdown rendering
✓ Code highlighting
✓ Tests intégration
```

### Semaine 7: Conversations

```bash
✓ Page Conversations
✓ ConversationList component
✓ ConversationItem component
✓ MessageBubble component
✓ MessageList component
✓ Hook useConversations
✓ Hook useMessages
✓ Export conversation (PDF/Markdown)
```

### Semaine 8: Responsive & PWA

```bash
✓ Adapter toutes pages mobile/tablet
✓ Navigation mobile (bottom tabs)
✓ Layout responsive (3 modes)
✓ Touch gestures
✓ PWA setup (manifest, service worker)
✓ Offline mode basique
✓ Tests E2E (Playwright)
```

### Semaine 9: Documents & Admin (Optional)

```bash
✓ Page Documents (admin)
✓ DocumentList component
✓ DocumentUpload component
✓ DocumentViewer component
✓ Page Admin (analytics)
✓ Dashboard component
✓ StatsCard component
✓ UsageChart component
```

### Semaine 10: Optimisation & Déploiement

```bash
✓ Code splitting
✓ Bundle optimization
✓ Image optimization
✓ Performance testing (Lighthouse)
✓ Accessibility audit
✓ E2E testing complet
✓ Documentation
✓ Déploiement staging
✓ Déploiement production
```

---

## 🎯 CHECKLIST QUALITÉ

### Performance

```yaml
✓ Lighthouse Score > 90
✓ First Contentful Paint < 1.5s
✓ Time to Interactive < 3.5s
✓ Bundle size < 500KB (gzipped)
✓ Code splitting implémenté
✓ Images optimisées (lazy loading)
✓ API caching (TanStack Query)
```

### Accessibilité

```yaml
✓ WCAG 2.1 Level AA
✓ Semantic HTML
✓ ARIA labels
✓ Keyboard navigation
✓ Screen reader tested
✓ Color contrast > 4.5:1
✓ Focus indicators visible
```

### Responsive

```yaml
✓ Mobile (320px - 768px) tested
✓ Tablet (768px - 1024px) tested
✓ Desktop (1024px+) tested
✓ Touch gestures implemented
✓ Orientation changes handled
```

### Tests

```yaml
✓ Unit tests > 80% coverage
✓ Integration tests pour features clés
✓ E2E tests pour parcours utilisateur
✓ Visual regression tests (optionnel)
```

### Security

```yaml
✓ XSS protection
✓ CSRF protection
✓ Secure cookies (HttpOnly)
✓ JWT validation
✓ Input sanitization
✓ Content Security Policy (CSP)
```

---

## 📚 RESSOURCES

### Documentation

- [Vite Documentation](https://vitejs.dev/)
- [React Documentation](https://react.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Tailwind CSS](https://tailwindcss.com/)
- [shadcn/ui](https://ui.shadcn.com/)
- [TanStack Query](https://tanstack.com/query)
- [React Router](https://reactrouter.com/)

### Design Inspiration

- [Perplexity AI](https://www.perplexity.ai/)
- [ChatGPT](https://chat.openai.com/)
- [Claude.ai](https://claude.ai/)

---

## ✅ CONCLUSION

Ce roadmap frontend permettra de créer une application web moderne, performante et full responsive qui remplacera avantageusement l'interface Streamlit actuelle.

**Avantages clés:**
- ✅ Full responsive (mobile, tablet, desktop)
- ✅ Performance optimisée (< 3s load time)
- ✅ PWA (installation, offline mode)
- ✅ UX moderne et intuitive
- ✅ Maintenabilité (TypeScript, tests)
- ✅ Scalabilité (architecture modulaire)

**Next Steps:**
1. Finaliser améliorations backend (prioritaire)
2. Valider design system avec stakeholders
3. Commencer implémentation frontend
4. Tests & itérations
5. Déploiement progressif

Prêt à démarrer! 🚀
