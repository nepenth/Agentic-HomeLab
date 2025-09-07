# Multi-stage build for production
FROM node:20-alpine AS build

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci --silent

# Copy source code
COPY . .

# Set build-time environment variables
ARG VITE_API_BASE_URL=https://whyland-ai.nakedsun.xyz:8443
ARG VITE_WS_URL=wss://whyland-ai.nakedsun.xyz:8443/ws
ARG VITE_API_TIMEOUT
ARG VITE_WS_MAX_MESSAGES_PER_MINUTE
ARG VITE_WS_RATE_LIMIT_WINDOW_MS
ARG VITE_WS_HEARTBEAT_INTERVAL
ARG VITE_WS_CONNECTION_TIMEOUT
ARG VITE_WS_MAX_RECONNECT_ATTEMPTS
ARG VITE_WS_RECONNECT_DELAY
ARG VITE_APP_NAME
ARG VITE_APP_VERSION

# Build the app
RUN npm run build

# Production stage with Nginx
FROM nginx:alpine AS production

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy SSL certificates
COPY ssl/fullchain.pem /etc/ssl/certs/fullchain.pem
COPY ssl/privkey.pem /etc/ssl/private/privkey.pem

# Copy built assets from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Expose ports for HTTP and HTTPS
EXPOSE 80 443

# Start nginx
CMD ["nginx", "-g", "daemon off;"]