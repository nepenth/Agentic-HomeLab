# Agentic Frontend

A modern, extensible React-based frontend for AI/agentic workflows with Apple-inspired design. Built with TypeScript, Material-UI, and Docker for seamless integration with FastAPI backends.

## 🚀 Features

- **Apple-Inspired Design**: Clean, minimalist UI with subtle animations and elegant typography
- **Modular Architecture**: Easily extensible for new AI workflows and agents
- **Real-time Updates**: WebSocket integration for live notifications and task updates
- **Secure Authentication**: JWT-based auth with protected routes
- **Backend Management**: Integrated tools for monitoring and managing backend services
- **Responsive Design**: Optimized for desktop and mobile devices
- **Dark Mode Support**: Theme switching capability
- **Docker Ready**: Complete containerization with multi-stage builds

## 🏗️ Architecture

### Tech Stack

- **Frontend**: React 18 + TypeScript + Vite
- **UI Framework**: Material-UI (MUI) v5 with custom Apple-inspired theme
- **State Management**: Redux Toolkit + React Query
- **Routing**: React Router v6
- **Real-time**: Socket.io-client
- **HTTP Client**: Axios with interceptors
- **Testing**: Jest + React Testing Library
- **Containerization**: Docker + Nginx

### Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable components
│   │   ├── Layout/         # Navigation and layout components
│   │   ├── ErrorBoundary.tsx
│   │   └── LoadingSpinner.tsx
│   ├── pages/              # Main page components
│   │   ├── Dashboard.tsx
│   │   ├── Login.tsx
│   │   ├── Utilities.tsx
│   │   └── Settings.tsx
│   ├── modules/            # Workflow-specific modules
│   │   ├── email-assistant/
│   │   └── document-analyzer/
│   ├── services/           # API clients and services
│   │   ├── api.ts
│   │   └── websocket.ts
│   ├── store/              # Redux store and slices
│   ├── theme/              # MUI theme configuration
│   ├── types/              # TypeScript type definitions
│   └── hooks/              # Custom React hooks
├── public/
├── Dockerfile
├── nginx.conf
└── package.json
```

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ or Docker
- Backend API running on configured endpoints

### Local Development

1. **Clone and install dependencies**:
   ```bash
   git clone <repository-url>
   cd Agentic-Frontend/frontend
   npm install
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your backend URLs
   ```

3. **Start development server**:
   ```bash
   npm run dev
   ```

4. **Access the application**:
   - Frontend: http://localhost:3000
   - Login with: `admin` / `password` (default)

### Docker Deployment

1. **Build and start all services**:
   ```bash
   docker-compose up -d --build
   ```

2. **Access services**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - Database UI: http://localhost:8080
   - Task Monitor: http://localhost:5555

## 🔧 Configuration

### Environment Variables

Create `.env` file from `.env.example`:

```env
# Production Configuration
VITE_API_BASE_URL=https://whyland-ai.nakedsun.xyz:8000
VITE_WS_URL=wss://whyland-ai.nakedsun.xyz:8000/ws

# Development Configuration
# VITE_API_BASE_URL=http://localhost:8000
# VITE_WS_URL=ws://localhost:8000/ws

VITE_APP_NAME=Agentic Frontend
VITE_APP_VERSION=0.1.0
```

### Backend Integration

The frontend expects these API endpoints:

- `POST /api/v1/auth/login` - Authentication
- `GET /api/v1/health` - Health check
- `GET /api/v1/dashboard/summary` - Dashboard data
- `GET /api/v1/agents` - List agents
- `POST /api/v1/tasks/run` - Execute tasks
- WebSocket `/ws/logs` - Real-time logs

## 🎨 Design System

### Apple-Inspired Theme

- **Typography**: SF Pro-inspired font stack
- **Colors**: iOS color palette (blues, purples, system colors)
- **Spacing**: 8px grid system
- **Shadows**: Subtle, layered shadows
- **Borders**: 12px radius for modern feel
- **Animations**: Smooth transitions and micro-interactions

### Component Guidelines

- Use MUI components as base
- Apply theme consistently
- Implement proper loading states
- Handle errors gracefully
- Ensure accessibility (WCAG compliance)

## 🔌 Extending the Frontend

### Adding New Workflows

1. **Create module directory**:
   ```bash
   mkdir src/modules/your-workflow
   ```

2. **Implement workflow component**:
   ```tsx
   // src/modules/your-workflow/YourWorkflow.tsx
   import WorkflowTemplate from '../../pages/WorkflowTemplate';
   
   const YourWorkflow = () => {
     return (
       <WorkflowTemplate
         title="Your Workflow"
         description="Description of your workflow"
         status="active"
         icon={<YourIcon />}
       >
         {/* Your workflow UI */}
       </WorkflowTemplate>
     );
   };
   ```

3. **Add route in App.tsx**:
   ```tsx
   <Route
     path="/workflows/your-workflow"
     element={
       <PrivateRoute>
         <Layout>
           <YourWorkflow />
         </Layout>
       </PrivateRoute>
     }
   />
   ```

4. **Update navigation in Sidebar.tsx**

### Adding New Pages

1. Create page component in `src/pages/`
2. Add route in `App.tsx`
3. Update navigation if needed

## 🔒 Security Features

- **JWT Authentication**: Secure token-based auth
- **Protected Routes**: Route-level access control
- **Input Validation**: Client-side validation
- **XSS Protection**: Content security policies
- **Secure Headers**: Nginx security headers
- **Environment Variables**: Sensitive data protection

## 🧪 Testing

```bash
# Run tests
npm run test

# Run tests in watch mode
npm run test:watch

# Generate coverage report
npm run test:coverage
```

## 📦 Building for Production

```bash
# Build optimized bundle
npm run build

# Preview production build
npm run preview
```

## 🐳 Docker Production

```bash
# Build production image
docker build -t agentic-frontend .

# Run container
docker run -p 3000:80 agentic-frontend
```

## 🚀 Deployment

### Manual Deployment

1. Build the application: `npm run build`
2. Deploy `dist/` folder to web server
3. Configure server for SPA routing
4. Set environment variables

### Docker Deployment

1. Use provided `Dockerfile` and `docker-compose.yml`
2. Configure environment variables
3. Deploy with `docker-compose up -d`

## 🔍 Backend Management Tools

The Utilities page provides access to:

| Service | URL | Description |
|---------|-----|-------------|
| **🔗 API Documentation** | `/docs` | Interactive Swagger UI |
| **📖 ReDoc Documentation** | `/redoc` | Alternative API docs |
| **🌸 Flower** | `:5555` | Celery task monitoring |
| **🗄️ Adminer** | `:8080` | Database browser |
| **📊 Metrics** | `/api/v1/metrics` | Prometheus metrics |

## 🛠️ Development Scripts

```bash
npm run dev          # Start development server
npm run build        # Build for production
npm run preview      # Preview production build
npm run lint         # Run ESLint
npm run test         # Run tests
npm run test:watch   # Run tests in watch mode
```

## 🐛 Troubleshooting

### Common Issues

1. **Build failures**: Check Node.js version (18+ required)
2. **API connection errors**: Verify backend URL and CORS settings
3. **Authentication issues**: Check JWT token format and expiration
4. **WebSocket connection fails**: Ensure WebSocket URL is correct
5. **Docker build issues**: Check Dockerfile and .dockerignore

### Debug Mode

Set `NODE_ENV=development` for additional debugging:
- Error stack traces
- Redux DevTools support
- Detailed API logging

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -m 'Add your feature'`
4. Push to branch: `git push origin feature/your-feature`
5. Submit pull request

### Code Style

- Use TypeScript for type safety
- Follow ESLint rules
- Use Prettier for formatting
- Write tests for new features
- Document complex logic

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🎯 Roadmap

- [ ] **Enhanced Theming**: Complete dark mode implementation
- [ ] **Mobile Optimization**: Improved mobile experience
- [ ] **PWA Support**: Service worker and offline capability
- [ ] **Advanced Analytics**: Detailed usage analytics
- [ ] **Plugin System**: Runtime plugin loading
- [ ] **Multi-language Support**: Internationalization
- [ ] **Advanced Caching**: Redis-based caching
- [ ] **Real-time Collaboration**: Multi-user features

## 📞 Support

For questions or issues:

1. Check the troubleshooting section
2. Search existing issues on GitHub
3. Create new issue with detailed description
4. Join our community discussions

---

**Built with ❤️ for the AI community**