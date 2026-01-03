# GitHub Setup Script für cryptoscanner (PowerShell Version)
# Führe aus: .\setup-github.ps1

Write-Host "🚀 GitHub & Vercel Setup für cryptoscanner" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""

# Git konfigurieren
Write-Host "Git wird konfiguriert..." -ForegroundColor Blue
$username = Read-Host "GitHub Benutzername eingeben"
$email = Read-Host "GitHub Email eingeben"

git config --global user.name $username
git config --global user.email $email

# Git initialisieren (falls nötig)
if (-Not (Test-Path ".git")) {
    Write-Host "Initialisiere Git Repository..." -ForegroundColor Blue
    git init
    git branch -M main
}

# Alle Dateien hinzufügen
Write-Host "Dateien zu Git hinzufügen..." -ForegroundColor Blue
git add .

# Initial commit
Write-Host "Erstelle initial commit..." -ForegroundColor Blue
git commit -m "Initial commit: Secure Chat App - Production Ready"

# Repository URL
Write-Host ""
$repoUrl = Read-Host "GitHub Repository URL eingeben (https://github.com/username/cryptoscanner.git)"

# Remote hinzufügen/aktualisieren
Write-Host "Remote Repository hinzufügen..." -ForegroundColor Blue
try {
    git remote add origin $repoUrl
} catch {
    git remote set-url origin $repoUrl
}

# Push zu GitHub
Write-Host "Zu GitHub pushen..." -ForegroundColor Blue
git push -u origin main

Write-Host ""
Write-Host "✅ GitHub Setup fertig!" -ForegroundColor Green
Write-Host ""
Write-Host "Nächste Schritte:" -ForegroundColor Yellow
Write-Host "1. Gehe zu https://vercel.com/new" -ForegroundColor White
Write-Host "2. GitHub Account verbinden" -ForegroundColor White
Write-Host "3. Repository 'cryptoscanner' wählen" -ForegroundColor White
Write-Host "4. Environment Variables setzen:" -ForegroundColor White
Write-Host "   - JWT_SECRET_KEY = (generieren mit:)" -ForegroundColor White
Write-Host "     python -c `"import secrets; print(secrets.token_urlsafe(32))`"" -ForegroundColor Cyan
Write-Host "   - FLASK_ENV = production" -ForegroundColor White
Write-Host "   - CORS_ORIGIN = *" -ForegroundColor White
Write-Host "5. Deploy Button drücken!" -ForegroundColor White
Write-Host ""
Write-Host "🎉 Fertig!" -ForegroundColor Green
