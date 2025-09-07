#!/bin/bash

# Frontend SSL Certificate Setup Script
# For domain: whyland-ai.nakedsun.xyz

# Create ssl directory if it doesn't exist
mkdir -p frontend/ssl

echo ""
echo "🔐 Frontend SSL Certificate Setup"
echo "=================================="
echo ""
echo "Choose your SSL certificate option:"
echo "1. Use existing certificates from backend (recommended if backend is on same server)"
echo "2. Generate self-signed certificates (for testing)"
echo "3. Setup Let's Encrypt with Certbot (if backend certificates don't exist)"
echo ""

read -p "Enter your choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "📁 Using existing certificates from backend/Let's Encrypt"
        echo ""
        
        # Common paths where backend certificates might be stored
        BACKEND_PATHS=(
            "../Agentic-Backend/nginx/ssl"
            "/etc/letsencrypt/live/whyland-ai.nakedsun.xyz"
            "../nginx/ssl"
            "./backend/nginx/ssl"
        )
        
        FOUND=false
        
        for path in "${BACKEND_PATHS[@]}"; do
            if [[ -f "$path/fullchain.pem" && -f "$path/privkey.pem" ]]; then
                echo "✅ Found certificates in: $path"
                
                # Copy certificates to frontend ssl directory
                cp "$path/fullchain.pem" frontend/ssl/
                cp "$path/privkey.pem" frontend/ssl/
                
                # Set appropriate permissions
                chmod 644 frontend/ssl/fullchain.pem
                chmod 600 frontend/ssl/privkey.pem
                
                FOUND=true
                break
            fi
        done
        
        if [ "$FOUND" = false ]; then
            echo "❌ No existing certificates found in common locations."
            echo ""
            echo "Please manually copy your certificates:"
            echo "  cp /path/to/fullchain.pem frontend/ssl/"
            echo "  cp /path/to/privkey.pem frontend/ssl/"
            echo ""
            echo "Or run this script again with option 3 to generate new certificates."
            exit 1
        fi
        ;;
    2)
        echo ""
        echo "🧪 Generating self-signed certificates (for testing only!)"
        echo "⚠  These certificates will show security warnings in browsers"
        echo ""
        
        # Generate self-signed certificate
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout frontend/ssl/privkey.pem \
            -out frontend/ssl/fullchain.pem \
            -subj "/C=US/ST=State/L=City/O=Organization/OU=IT Department/CN=whyland-ai.nakedsun.xyz"
        
        if [ $? -eq 0 ]; then
            echo "✅ Self-signed certificates generated successfully!"
            echo "   Location: frontend/ssl/"
        else
            echo "❌ Failed to generate certificates"
            exit 1
        fi
        ;;
    3)
        echo ""
        echo "🌐 Setting up Let's Encrypt with Certbot"
        echo ""
        echo "Prerequisites:"
        echo "1. Your domain (whyland-ai.nakedsun.xyz) must point to this server"
        echo "2. Ports 80 and 443 must be accessible from the internet"
        echo "3. Certbot must be installed on this system"
        echo "4. No other services should be using ports 80/443 during setup"
        echo ""
        
        read -p "Have you met all prerequisites? (y/n): " prereq
        
        if [[ $prereq == "y" || $prereq == "Y" ]]; then
            echo "Installing certbot if not already installed..."
            
            # Check if certbot is installed
            if ! command -v certbot &> /dev/null; then
                echo "Installing certbot..."
                if command -v apt &> /dev/null; then
                    sudo apt update && sudo apt install -y certbot
                elif command -v yum &> /dev/null; then
                    sudo yum install -y certbot
                else
                    echo "❌ Please install certbot manually"
                    exit 1
                fi
            fi
            
            echo ""
            echo "🔄 Obtaining certificates from Let's Encrypt..."
            echo "This will:"
            echo "1. Temporarily stop any services using port 80"
            echo "2. Obtain certificates using standalone mode"
            echo "3. Copy certificates to frontend/ssl/"
            echo ""
            
            # Stop services that might be using port 80
            sudo docker-compose down 2>/dev/null || true
            
            # Obtain certificate
            sudo certbot certonly --standalone \
                --preferred-challenges http \
                --email admin@whyland-ai.nakedsun.xyz \
                --agree-tos \
                --no-eff-email \
                -d whyland-ai.nakedsun.xyz
            
            if [ $? -eq 0 ]; then
                echo "✅ Certificates obtained successfully!"
                
                # Copy certificates to frontend ssl directory
                sudo cp /etc/letsencrypt/live/whyland-ai.nakedsun.xyz/fullchain.pem frontend/ssl/
                sudo cp /etc/letsencrypt/live/whyland-ai.nakedsun.xyz/privkey.pem frontend/ssl/
                
                # Set appropriate permissions
                sudo chown $(whoami):$(whoami) frontend/ssl/*.pem
                sudo chmod 644 frontend/ssl/fullchain.pem
                sudo chmod 600 frontend/ssl/privkey.pem
                
                echo "📋 Certificate renewal:"
                echo "Add this to your crontab for automatic renewal:"
                echo "0 3 * * * certbot renew --quiet --deploy-hook 'docker-compose restart frontend'"
                
            else
                echo "❌ Failed to obtain certificates"
                echo "Please check:"
                echo "1. Domain DNS is pointing to this server"
                echo "2. Firewall allows ports 80 and 443"
                echo "3. No other services are using port 80"
                exit 1
            fi
        else
            echo "Please meet the prerequisites first, then run this script again."
            exit 1
        fi
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "🔧 Updating nginx configuration for production..."

# Update nginx.conf to use the correct certificate paths and server name
cat > frontend/nginx.conf << 'EOF'
# HTTP server - redirect all traffic to HTTPS
server {
    listen 80;
    server_name whyland-ai.nakedsun.xyz;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name whyland-ai.nakedsun.xyz;
    root /usr/share/nginx/html;
    index index.html;

    # SSL configuration
    ssl_certificate /etc/ssl/certs/fullchain.pem;
    ssl_certificate_key /etc/ssl/private/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Enable gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/javascript
        application/xml+rss
        application/json;

    # Handle static assets with proper headers
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        try_files $uri =404;
    }
    
    # Handle client routing for SPA - fallback for everything else
    location / {
        try_files $uri $uri/ /index.html;
        
        # Add security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }

    # Security - deny access to sensitive files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

    location ~ ~$ {
        deny all;
        access_log off;
        log_not_found off;
    }

    # Error pages
    error_page 404 /index.html;
}
EOF

echo "✅ Updated nginx.conf with production SSL configuration"

# Update docker-compose.yml to mount SSL certificates
echo ""
echo "🔧 Updating docker-compose.yml to mount SSL certificates..."

# Create a backup of the current docker-compose.yml
cp docker-compose.yml docker-compose.yml.backup

# Update docker-compose.yml to include SSL volume mounts
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  # Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        VITE_API_BASE_URL: https://whyland-ai.nakedsun.xyz
        VITE_WS_URL: wss://whyland-ai.nakedsun.xyz/ws
        VITE_APP_NAME: Agentic Frontend
        VITE_APP_VERSION: 0.1.0
    restart: unless-stopped
    ports:
      - "3000:80"
      - "3443:443"
    environment:
      - VITE_API_BASE_URL=https://whyland-ai.nakedsun.xyz
      - VITE_WS_URL=wss://whyland-ai.nakedsun.xyz/ws
      - VITE_APP_NAME=Agentic Frontend
      - VITE_APP_VERSION=0.1.0
    volumes:
      - ./frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./frontend/ssl/fullchain.pem:/etc/ssl/certs/fullchain.pem:ro
      - ./frontend/ssl/privkey.pem:/etc/ssl/private/privkey.pem:ro
EOF

echo "✅ Updated docker-compose.yml with SSL certificate mounts"

echo ""
echo "🔍 Verifying certificate files..."

if [[ -f "frontend/ssl/fullchain.pem" && -f "frontend/ssl/privkey.pem" ]]; then
    echo "✅ Certificate files found:"
    echo "   - frontend/ssl/fullchain.pem"
    echo "   - frontend/ssl/privkey.pem"
    
    # Check certificate validity
    echo ""
    echo "📜 Certificate information:"
    openssl x509 -in frontend/ssl/fullchain.pem -text -noout | grep -E "(Subject:|Not Before|Not After|DNS:)"
    
    echo ""
    echo "🚀 Frontend is ready for HTTPS!"
    echo "Run: docker-compose up -d --build"
    echo ""
    echo "Your frontend will be available at:"
    echo "  - https://whyland-ai.nakedsun.xyz:3443/"
    echo "  - http://whyland-ai.nakedsun.xyz:3000/ (redirects to HTTPS)"
else
    echo "❌ Certificate files not found!"
    echo "Please ensure both fullchain.pem and privkey.pem are in frontend/ssl/"
    exit 1
fi

echo ""
echo "💡 Pro tip: If you're running both frontend and backend on the same server,"
echo "   you can use a reverse proxy (like Cloudflare, nginx, or Traefik) to"
echo "   serve both services on standard ports (80/443) with path-based routing."