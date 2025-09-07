#!/bin/bash

# SSL Certificate Setup Script for Agentic Backend
# This script helps set up SSL certificates for HTTPS support

echo "🔐 SSL Certificate Setup for Agentic Backend"
echo "=============================================="

# Create SSL directory if it doesn't exist
mkdir -p nginx/ssl

echo ""
echo "Choose your SSL certificate option:"
echo "1. Use existing certificates (if you have them)"
echo "2. Generate self-signed certificates (for testing)"
echo "3. Setup Let's Encrypt with Certbot (recommended for production)"
echo ""

read -p "Enter your choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "📁 Using existing certificates"
        echo "Please copy your certificates to nginx/ssl/ with these names:"
        echo "  - fullchain.pem (certificate + intermediate certificates)"
        echo "  - privkey.pem (private key)"
        echo ""
        echo "Example commands:"
        echo "  cp /path/to/your/fullchain.pem nginx/ssl/"
        echo "  cp /path/to/your/privkey.pem nginx/ssl/"
        ;;
    2)
        echo ""
        echo "🧪 Generating self-signed certificates (for testing only!)"
        echo "⚠️  These certificates will show security warnings in browsers"
        echo ""
        
        # Generate self-signed certificate
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout nginx/ssl/privkey.pem \
            -out nginx/ssl/fullchain.pem \
            -subj "/C=US/ST=State/L=City/O=Organization/OU=IT Department/CN=whyland-ai.nakedsun.xyz"
        
        if [ $? -eq 0 ]; then
            echo "✅ Self-signed certificates generated successfully!"
            echo "   Location: nginx/ssl/"
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
            echo "3. Copy certificates to nginx/ssl/"
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
                
                # Copy certificates to nginx directory
                sudo cp /etc/letsencrypt/live/whyland-ai.nakedsun.xyz/fullchain.pem nginx/ssl/
                sudo cp /etc/letsencrypt/live/whyland-ai.nakedsun.xyz/privkey.pem nginx/ssl/
                
                # Set appropriate permissions
                sudo chown $(whoami):$(whoami) nginx/ssl/*.pem
                sudo chmod 600 nginx/ssl/privkey.pem
                sudo chmod 644 nginx/ssl/fullchain.pem
                
                echo "📋 Certificate renewal:"
                echo "Add this to your crontab for automatic renewal:"
                echo "0 3 * * * certbot renew --quiet --deploy-hook 'docker-compose restart nginx'"
                
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
echo "🔍 Verifying certificate files..."

if [[ -f "nginx/ssl/fullchain.pem" && -f "nginx/ssl/privkey.pem" ]]; then
    echo "✅ Certificate files found:"
    echo "   - nginx/ssl/fullchain.pem"
    echo "   - nginx/ssl/privkey.pem"
    
    # Check certificate validity
    echo ""
    echo "📜 Certificate information:"
    openssl x509 -in nginx/ssl/fullchain.pem -text -noout | grep -E "(Subject:|Not Before|Not After|DNS:)"
    
    echo ""
    echo "🚀 Ready to start with HTTPS!"
    echo "Run: docker-compose up -d"
    echo ""
    echo "Your API will be available at:"
    echo "  - https://whyland-ai.nakedsun.xyz/api/v1/"
    echo "  - https://whyland-ai.nakedsun.xyz/docs (if debug is enabled)"
    echo "  - https://whyland-ai.nakedsun.xyz/flower/ (Celery monitoring)"
else
    echo "❌ Certificate files not found!"
    echo "Please ensure both fullchain.pem and privkey.pem are in nginx/ssl/"
    exit 1
fi