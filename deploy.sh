#!/bin/bash

# ContextSnap Deployment Script
# This script helps you deploy the backend to Render via GitHub

echo "🚀 ContextSnap Deployment Script"
echo "================================"

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed. Please install Git first."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "backend/index.js" ] || [ ! -f "extension/manifest.json" ]; then
    echo "❌ Please run this script from the root directory of the project"
    exit 1
fi

echo "📋 Step 1: Initialize Git repository"
echo "-----------------------------------"

# Initialize git if not already done
if [ ! -d ".git" ]; then
    git init
    echo "✅ Git repository initialized"
else
    echo "✅ Git repository already exists"
fi

# Create .gitignore
cat > .gitignore << EOF
# Dependencies
node_modules/
npm-debug.log*

# Environment variables
.env
.env.local
.env.production

# API keys (security)
apikey.txt

# OS files
.DS_Store
Thumbs.db

# IDE files
.vscode/
.idea/

# Logs
*.log

# Runtime data
pids
*.pid
*.seed
*.pid.lock

# Coverage directory used by tools like istanbul
coverage/

# Dependency directories
jspm_packages/

# Optional npm cache directory
.npm

# Optional REPL history
.node_repl_history

# Output of 'npm pack'
*.tgz

# Yarn Integrity file
.yarn-integrity
EOF

echo "✅ .gitignore created"

echo ""
echo "📋 Step 2: Add files to Git"
echo "----------------------------"

# Add all files
git add .

# Check if there are changes to commit
if git diff --cached --quiet; then
    echo "ℹ️  No changes to commit"
else
    git commit -m "Initial commit: ContextSnap with secure multi-provider support"
    echo "✅ Changes committed"
fi

echo ""
echo "📋 Step 3: GitHub Repository Setup"
echo "---------------------------------"

echo "Please follow these steps:"
echo ""
echo "1. Go to https://github.com/new"
echo "2. Create a new repository named 'contextsnap'"
echo "3. Make it public or private (your choice)"
echo "4. DON'T initialize with README (we already have one)"
echo "5. Copy the repository URL"
echo ""

read -p "Enter your GitHub repository URL (e.g., https://github.com/username/contextsnap.git): " GITHUB_URL

if [ -z "$GITHUB_URL" ]; then
    echo "❌ No URL provided. Exiting."
    exit 1
fi

# Add remote and push
git remote add origin "$GITHUB_URL"
git branch -M main
git push -u origin main

echo "✅ Code pushed to GitHub"

echo ""
echo "📋 Step 4: Render Deployment"
echo "----------------------------"

echo "Now let's deploy to Render:"
echo ""
echo "1. Go to https://render.com"
echo "2. Sign up/Login with your GitHub account"
echo "3. Click 'New +' → 'Web Service'"
echo "4. Connect your GitHub repository"
echo "5. Configure the service:"
echo "   - Name: contextsnap-backend"
echo "   - Root Directory: backend"
echo "   - Build Command: npm install"
echo "   - Start Command: npm start"
echo "   - Plan: Free"
echo "6. Click 'Create Web Service'"
echo ""

read -p "Press Enter when your Render service is deployed and you have the URL..."

echo ""
echo "📋 Step 5: Update Extension Configuration"
echo "----------------------------------------"

read -p "Enter your Render service URL (e.g., https://contextsnap-backend.onrender.com): " RENDER_URL

if [ -z "$RENDER_URL" ]; then
    echo "❌ No URL provided. Please update the extension manually."
    exit 1
fi

# Update the extension files with the new backend URL
echo "Updating extension configuration..."

# Update security.js
sed -i "s|http://localhost:3000|$RENDER_URL|g" extension/security.js

# Update sidebar.js
sed -i "s|http://localhost:3000|$RENDER_URL|g" extension/sidebar.js

echo "✅ Extension configuration updated"

# Commit and push the changes
git add .
git commit -m "Update backend URL for production deployment"
git push

echo ""
echo "🎉 Deployment Complete!"
echo "======================"
echo ""
echo "✅ Backend deployed to Render"
echo "✅ Extension configured for production"
echo "✅ Code pushed to GitHub"
echo ""
echo "📋 Next Steps:"
echo "1. Test your extension with the new backend"
echo "2. Share the extension with users"
echo "3. Monitor usage on Render dashboard"
echo ""
echo "🔗 Your Render service: $RENDER_URL"
echo "🔗 Your GitHub repository: $GITHUB_URL"
echo ""
echo "Happy coding! 🚀" 