# InterviewAI Frontend

A modern, AI-powered technical interview platform built with Next.js 14, TypeScript, and Tailwind CSS.

## 🚀 Features

### Core Functionality
- **AI-Powered Interviews**: Dynamic question generation and real-time evaluation
- **Code Editor**: Multi-language support with AI-powered code analysis
- **Practice Mode**: Targeted skill development with progress tracking
- **Dashboard**: Comprehensive analytics and performance insights
- **Anti-Cheat System**: Webcam monitoring, audio analysis, and behavioral tracking

### Technical Features
- **Modern Stack**: Next.js 14, TypeScript, Tailwind CSS
- **Component Library**: Shadcn/ui components with Radix UI primitives
- **Code Editor**: Monaco Editor with syntax highlighting and IntelliSense
- **Real-time Updates**: WebSocket integration for live collaboration
- **Responsive Design**: Mobile-first approach with adaptive layouts

## 🛠️ Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Components**: Shadcn/ui + Radix UI
- **Icons**: Lucide React
- **Code Editor**: Monaco Editor
- **State Management**: React Hooks + Context
- **HTTP Client**: Fetch API with custom wrapper
- **Authentication**: NextAuth.js (planned)

## 📁 Project Structure

```
frontend/
├── app/                    # Next.js app directory
│   ├── (auth)/            # Authentication routes
│   ├── api/               # API routes
│   ├── dashboard/         # Dashboard page
│   ├── ide/               # Code editor page
│   ├── interview/         # Interview interface
│   ├── practice/          # Practice mode
│   ├── globals.css        # Global styles
│   ├── layout.tsx         # Root layout
│   └── page.tsx           # Landing page
├── components/            # Reusable components
│   ├── ui/               # Shadcn/ui components
│   ├── anti-cheat/       # Security components
│   ├── ide/              # Code editor components
│   ├── interview/        # Interview components
│   └── navigation.tsx    # Navigation component
├── lib/                  # Utility libraries
│   ├── api-client.ts     # Backend API client
│   └── utils.ts          # Helper functions
├── types/                # TypeScript type definitions
├── public/               # Static assets
├── package.json          # Dependencies
├── tailwind.config.js    # Tailwind configuration
└── tsconfig.json         # TypeScript configuration
```

## 🚀 Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn
- Backend server running (Flask API)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   # or
   yarn install
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env.local
   ```
   
   Update `.env.local` with your configuration:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:5000
   NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
   ```

4. **Start the development server**
   ```bash
   npm run dev
   # or
   yarn dev
   ```

5. **Open your browser**
   Navigate to [http://localhost:3000](http://localhost:3000)

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | Yes |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL | Yes |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anonymous key | Yes |

### Tailwind CSS

The project uses Tailwind CSS with custom configuration. Key features:

- **Custom Colors**: Brand colors and semantic color system
- **Component Variants**: Pre-built component styles
- **Responsive Breakpoints**: Mobile-first responsive design
- **Dark Mode**: Built-in dark mode support (planned)

### TypeScript

Strict TypeScript configuration with:

- **Strict Mode**: Enabled for better type safety
- **Path Mapping**: Clean import paths with `@/` alias
- **Type Definitions**: Comprehensive interfaces for all components
- **ESLint Integration**: TypeScript-aware linting rules

## 📱 Pages & Components

### Landing Page (`/`)
- Hero section with feature overview
- Navigation to main features
- Call-to-action buttons

### Interview Hub (`/interview`)
- Interview configuration
- Session management
- Anti-cheat monitoring
- Real-time evaluation

### Practice Mode (`/practice`)
- Topic selection (Algorithms, Data Structures, etc.)
- Difficulty levels
- Progress tracking
- Performance analytics

### Dashboard (`/dashboard`)
- Session history
- Performance metrics
- Skill breakdown
- Improvement suggestions

### Code IDE (`/ide`)
- Multi-language code editor
- Code execution
- AI-powered evaluation
- Syntax highlighting

## 🔌 API Integration

### Backend API Client

The frontend communicates with the Flask backend through a custom API client (`lib/api-client.ts`):

```typescript
import { apiClient } from '@/lib/api-client'

// Start interview session
const session = await apiClient.startSession('technical')

// Get question
const question = await apiClient.getQuestion(session.id, 'technical')

// Submit answer
const result = await apiClient.submitAnswer(session.id, question.id, answer)

// Submit code
const evaluation = await apiClient.submitCode(session.id, question.id, code, 'python')
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/start_session` | POST | Start new interview session |
| `/api/get_question` | GET | Get interview question |
| `/api/submit_answer` | POST | Submit text answer |
| `/api/submit_code` | POST | Submit code for evaluation |
| `/api/security/check` | POST | Perform security check |
| `/api/log_event` | POST | Log system event |
| `/api/end_session` | POST | End interview session |

## 🛡️ Security Features

### Anti-Cheat System

- **Webcam Monitoring**: Face detection and tracking
- **Audio Analysis**: Suspicious sound detection
- **Behavioral Analysis**: Typing patterns and timing
- **Browser Security**: Tab switching and devtools detection
- **Real-time Alerts**: Immediate flagging of suspicious activity

### Security Components

- `AntiCheatGuard`: Main security monitoring component
- `SecurityService`: Backend security analysis
- `SecurityEvents`: Database logging of security incidents

## 🎨 UI Components

### Component Library

Built on Shadcn/ui with custom enhancements:

- **Form Components**: Input, Select, Textarea, Button
- **Layout Components**: Card, Container, Grid, Flex
- **Feedback Components**: Alert, Badge, Progress, Toast
- **Navigation Components**: Tabs, Breadcrumb, Pagination

### Custom Components

- **InterviewInterface**: Complete interview experience
- **EnhancedCodeEditor**: Advanced code editor with evaluation
- **InterviewChat**: AI-powered interview assistance
- **PracticeSession**: Interactive practice interface

## 📊 State Management

### React Hooks

- **useState**: Local component state
- **useEffect**: Side effects and lifecycle
- **useRef**: DOM references and persistent values
- **useCallback**: Memoized functions
- **useMemo**: Memoized values

### Context API

- **Theme Context**: Dark/light mode switching
- **Auth Context**: User authentication state
- **Session Context**: Interview session management

## 🚀 Performance Optimization

### Code Splitting

- **Dynamic Imports**: Lazy loading of heavy components
- **Route-based Splitting**: Automatic code splitting by route
- **Component Splitting**: Lazy loading of large components

### Optimization Techniques

- **Image Optimization**: Next.js Image component
- **Font Optimization**: Google Fonts with display swap
- **Bundle Analysis**: Webpack bundle analyzer
- **Tree Shaking**: Unused code elimination

## 🧪 Testing

### Testing Strategy

- **Unit Tests**: Component testing with Jest
- **Integration Tests**: API integration testing
- **E2E Tests**: Full user journey testing
- **Performance Tests**: Lighthouse and Core Web Vitals

### Running Tests

```bash
# Unit tests
npm run test

# Integration tests
npm run test:integration

# E2E tests
npm run test:e2e

# Performance tests
npm run test:performance
```

## 📦 Build & Deployment

### Build Commands

```bash
# Development build
npm run dev

# Production build
npm run build

# Production start
npm start

# Static export
npm run export
```

### Deployment

The frontend can be deployed to:

- **Vercel**: Recommended for Next.js apps
- **Netlify**: Static site hosting
- **AWS S3**: Static website hosting
- **Docker**: Containerized deployment

## 🔄 Development Workflow

### Git Workflow

1. **Feature Branch**: Create feature branch from main
2. **Development**: Implement features with tests
3. **Code Review**: Submit pull request for review
4. **Testing**: Automated and manual testing
5. **Merge**: Merge to main after approval

### Code Quality

- **ESLint**: JavaScript/TypeScript linting
- **Prettier**: Code formatting
- **Husky**: Git hooks for quality checks
- **Commitizen**: Conventional commit messages

## 🐛 Troubleshooting

### Common Issues

1. **Build Errors**
   - Check Node.js version (18+ required)
   - Clear `.next` folder and reinstall dependencies
   - Verify TypeScript configuration

2. **API Connection Issues**
   - Ensure backend server is running
   - Check environment variables
   - Verify CORS configuration

3. **Component Rendering Issues**
   - Check browser console for errors
   - Verify component imports
   - Check TypeScript type definitions

### Debug Mode

Enable debug mode for detailed logging:

```bash
DEBUG=* npm run dev
```

## 🤝 Contributing

### Development Setup

1. Fork the repository
2. Create feature branch
3. Implement changes with tests
4. Submit pull request
5. Address review feedback

### Code Standards

- **TypeScript**: Strict mode enabled
- **ESLint**: Airbnb configuration
- **Prettier**: Consistent formatting
- **Testing**: Minimum 80% coverage

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Getting Help

- **Documentation**: Check this README and inline code comments
- **Issues**: Create GitHub issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions
- **Email**: Contact the development team

### Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Shadcn/ui Documentation](https://ui.shadcn.com)
- [TypeScript Handbook](https://www.typescriptlang.org/docs)

---

**Built with ❤️ by the InterviewAI Team**
