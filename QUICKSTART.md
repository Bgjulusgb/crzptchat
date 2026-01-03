# 🚀 Secure Chat - Schnellstart-Anleitung

## ⚡ In 3 Schritten starten

### Schritt 1: Installation

```powershell
# Installiere alle Dependencies
pip install -r requirements.txt
```

### Schritt 2: Server starten

```powershell
# Starte den Chat-Server
python chat_server.py
```

### Schritt 3: Browser öffnen

Öffne deinen Browser und gehe zu: **http://localhost:5000**

---

## 📱 Was kann die App?

### ✨ Features

1. **Moderne Web-UI**
   - Schönes, dunkles Design
   - Echtzeit-Messaging
   - Responsive für Mobile & Desktop

2. **Secure Messaging**
   - End-to-End Verschlüsselung
   - JWT Authentication
   - Sichere Passwörter (bcrypt)

3. **Real-time Features**
   - WebSocket Support
   - Sofortige Nachrichtenübermittlung
   - Online/Offline Status
   - Tipp-Indikatoren

4. **Chat Features**
   - Private 1-zu-1 Chats
   - Gruppenchats
   - Nachrichtenverlauf
   - Benutzersuche

---

## 🎯 Erste Schritte in der App

### 1. Registrierung

1. Klicke auf **"Registrieren"**
2. Gib einen Benutzernamen ein (3-50 Zeichen, nur Buchstaben, Zahlen, _ und -)
3. E-Mail-Adresse
4. Passwort (mind. 8 Zeichen mit Groß-/Kleinbuchstaben, Zahlen, Sonderzeichen)
5. Passwort bestätigen
6. Klick auf **"Registrieren"**

### 2. Anmeldung

1. Gib deinen Benutzernamen oder E-Mail ein
2. Passwort
3. Klick auf **"Anmelden"**

### 3. Chat starten

1. Wechsle zum **"Benutzer"**-Tab in der Seitenleiste
2. Klicke auf einen Benutzer
3. Schreibe deine Nachricht
4. Drücke Enter oder klicke auf den Senden-Button

### 4. Gruppe erstellen

1. Wechsle zum **"Gruppen"**-Tab
2. Klicke auf **"Neue Gruppe erstellen"**
3. Gib einen Namen und Beschreibung ein
4. Klick auf **"Erstellen"**

---

## 🛠️ Alternative Nutzung

### Demo-Anwendung (CLI)

Teste alle Features in der Konsole:

```powershell
python demo_app.py
```

Dies zeigt:
- ✅ Benutzerregistrierung und Authentifizierung
- ✅ Nachrichtenverschlüsselung
- ✅ Nachrichtenaustausch
- ✅ Gruppenchats

### Enhanced CLI Version

Vollständige CLI-Anwendung:

```powershell
python secure_chat_enhanced.py
```

Features:
- Komplette Chat-Funktionalität
- Datenbankmanagement
- Benutzerverwaltung
- Verschlüsseltes Messaging

---

## 🔧 Konfiguration

### Umgebungsvariablen

Erstelle eine `.env` Datei im Projektverzeichnis:

```env
# Security
JWT_SECRET=dein-super-geheimer-schluessel-hier

# Database
SECURE_CHAT_DATA_DIR=secure_chat_data

# Server
FLASK_ENV=development
```

### Empfohlene Produktions-Einstellungen

Für Produktionsumgebung:

```env
JWT_SECRET=<generiere-mit-secrets.token_urlsafe(64)>
JWT_EXPIRATION_HOURS=24
MAX_LOGIN_ATTEMPTS=5
LOGIN_ATTEMPT_WINDOW=300
MAX_FILE_SIZE=10485760
FLASK_ENV=production
```

---

## 📊 Architektur

### Technologie-Stack

**Backend:**
- Flask (Web Framework)
- Flask-SocketIO (WebSocket Support)
- SQLAlchemy (ORM)
- Cryptography (AES Verschlüsselung)
- PyJWT (Token Authentication)

**Frontend:**
- Vanilla JavaScript
- Socket.IO Client
- Modern CSS3
- Font Awesome Icons

**Datenbank:**
- SQLite (Development)
- Unterstützt PostgreSQL/MySQL (Produktion)

### Projektstruktur

```
cryptoscanner/
├── chat_server.py              # Flask Web Server
├── secure_chat_enhanced.py     # CLI Version
├── demo_app.py                 # Demo-Anwendung
├── templates/
│   └── chat.html              # Web UI
├── static/
│   ├── css/
│   │   └── style.css          # Styling
│   └── js/
│       └── app.js             # Frontend Logic
├── secure_chat/               # Python Package
│   ├── models/                # Datenmodelle
│   ├── services/              # Business Logic
│   ├── auth/                  # Authentifizierung
│   └── utils/                 # Hilfsfunktionen
└── requirements.txt           # Dependencies
```

---

## 🔐 Sicherheit

### Implementierte Sicherheitsmaßnahmen

1. **Verschlüsselung**
   - AES-128 (Fernet)
   - Unique Keys pro Benutzer/Gruppe
   - Nonce für jede Nachricht

2. **Authentication**
   - JWT Tokens
   - Sichere Passwort-Hashes (PBKDF2)
   - Rate Limiting

3. **Input Validation**
   - Email Validierung
   - Username Pattern Matching
   - Passwort-Komplexität
   - Message Sanitization

4. **Datenschutz**
   - SQLite mit eingeschränkten Permissions
   - Secure Key Storage
   - Session Management

---

## 🐛 Troubleshooting

### Problem: Server startet nicht

**Lösung:**
```powershell
# Prüfe ob Dependencies installiert sind
pip list | Select-String -Pattern "Flask|socketio"

# Reinstalliere Dependencies
pip install -r requirements.txt --force-reinstall
```

### Problem: "Module not found" Fehler

**Lösung:**
```powershell
# Stelle sicher, dass du im richtigen Verzeichnis bist
cd C:\Users\gillm\Desktop\Signaller\Projekts\cryptoscanner

# Aktiviere Virtual Environment
.venv\Scripts\activate

# Installiere Package im Entwicklungsmodus
pip install -e .
```

### Problem: WebSocket Verbindung fehlgeschlagen

**Lösung:**
1. Prüfe ob Server läuft
2. Lösche Browser-Cache
3. Prüfe Firewall-Einstellungen
4. Verwende `localhost` statt `127.0.0.1`

### Problem: Datenbank-Fehler

**Lösung:**
```powershell
# Lösche alte Datenbank und starte neu
Remove-Item -Recurse -Force secure_chat_data
python chat_server.py
```

---

## 📝 API Dokumentation

### REST Endpoints

#### POST /api/register
Registriere neuen Benutzer
```json
Request:
{
    "username": "testuser",
    "email": "test@example.com",
    "password": "SecurePass123!"
}

Response:
{
    "success": true,
    "token": "eyJhbGc...",
    "user": {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com"
    }
}
```

#### POST /api/login
Benutzer anmelden
```json
Request:
{
    "username": "testuser",
    "password": "SecurePass123!"
}

Response:
{
    "success": true,
    "token": "eyJhbGc...",
    "user": {...}
}
```

#### GET /api/users
Alle Benutzer abrufen (authentifiziert)
```
Headers:
Authorization: Bearer <token>

Response:
{
    "success": true,
    "users": [...]
}
```

#### GET /api/messages/:userId
Nachrichten mit Benutzer abrufen
```
Headers:
Authorization: Bearer <token>

Response:
{
    "success": true,
    "messages": [...]
}
```

### WebSocket Events

#### Client → Server

- `authenticate`: Authentifizierung mit Token
- `send_message`: Nachricht senden
- `typing`: Tipp-Indikator senden

#### Server → Client

- `connected`: Verbindung hergestellt
- `authenticated`: Authentifizierung erfolgreich
- `new_message`: Neue Nachricht empfangen
- `user_status`: Benutzer-Status geändert
- `user_typing`: Benutzer tippt
- `message_sent`: Nachricht gesendet bestätigt
- `error`: Fehler aufgetreten

---

## 🎓 Weitere Informationen

### Dokumentation
- [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) - Ausführliche Beispiele
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Detaillierte Setup-Anleitung
- [README.md](README.md) - Vollständige Dokumentation

### Support
Bei Problemen oder Fragen:
1. Prüfe die Troubleshooting-Sektion
2. Schaue in die Log-Dateien (`secure_chat_data/logs/`)
3. Erstelle ein Issue im Repository

---

## ✅ Checkliste für Produktions-Deployment

- [ ] Ändere `JWT_SECRET` in `.env`
- [ ] Setze `FLASK_ENV=production`
- [ ] Konfiguriere PostgreSQL/MySQL statt SQLite
- [ ] Aktiviere HTTPS/TLS
- [ ] Konfiguriere Reverse Proxy (nginx/Apache)
- [ ] Setze Rate Limits
- [ ] Aktiviere Logging und Monitoring
- [ ] Backup-Strategie implementieren
- [ ] Security Headers konfigurieren
- [ ] CORS richtig konfigurieren

---

## 🎉 Viel Erfolg!

Die App ist jetzt einsatzbereit. Viel Spaß beim sicheren Chatten!

**Wichtig:** Dies ist eine Demonstration. Für Produktionsumgebungen sollten zusätzliche Sicherheitsmaßnahmen implementiert werden.
