#!/bin/bash
# Quick GitHub Setup Script for cryptoscanner

echo "🚀 GitHub & Vercel Setup for cryptoscanner"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo -e "${YELLOW}Git not found. Installing...${NC}"
    # Installation instructions vary by OS
fi

# Configure Git
echo -e "${BLUE}Setting up Git...${NC}"
read -p "Enter your GitHub username: " GITHUB_USER
read -p "Enter your GitHub email: " GITHUB_EMAIL

git config --global user.name "$GITHUB_USER"
git config --global user.email "$GITHUB_EMAIL"

# Initialize Git if needed
if [ ! -d .git ]; then
    echo -e "${BLUE}Initializing Git repository...${NC}"
    git init
    git branch -M main
fi

# Add all files
echo -e "${BLUE}Adding files to Git...${NC}"
git add .

# Create initial commit
echo -e "${BLUE}Creating initial commit...${NC}"
git commit -m "Initial commit: Secure Chat App - Production Ready"

# Get repository URL
read -p "Enter your GitHub repository URL (https://github.com/username/cryptoscanner.git): " REPO_URL

# Add remote
echo -e "${BLUE}Adding remote repository...${NC}"
git remote add origin "$REPO_URL" 2>/dev/null || git remote set-url origin "$REPO_URL"

# Push to GitHub
echo -e "${BLUE}Pushing to GitHub...${NC}"
git push -u origin main

echo -e "${GREEN}✅ GitHub setup complete!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Go to https://vercel.com/new"
echo "2. Connect your GitHub account"
echo "3. Select 'cryptoscanner' repository"
echo "4. Add environment variables:"
echo "   - JWT_SECRET_KEY=<generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\">"
echo "   - FLASK_ENV=production"
echo "   - CORS_ORIGIN=*"
echo "5. Click Deploy!"
echo ""
echo -e "${GREEN}Done! 🎉${NC}"
