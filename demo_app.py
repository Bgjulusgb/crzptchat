"""
Beispiel-Skript für die Secure Chat Application
Demonstriert die Verwendung der EncryptionManager und AuthenticationManager Klassen
"""

import sys
import os

# Importiere die Hauptanwendung
sys.path.insert(0, os.path.dirname(__file__))

from secure_chat_enhanced import (
    DatabaseManager,
    AuthenticationManager,
    EncryptionManager,
    InputValidator,
    Config
)


def demo_user_registration():
    """Demonstriert Benutzerregistrierung"""
    print("\n" + "=" * 60)
    print("DEMO 1: Benutzerregistrierung und Authentifizierung")
    print("=" * 60)
    
    db = DatabaseManager()
    auth = AuthenticationManager(db)
    
    # Validiere Eingaben
    username = "testuser123"
    email = "test@example.com"
    password = "SecurePass123!"
    
    print(f"\n1. Validiere Benutzerdaten...")
    print(f"   Username: {username}")
    print(f"   Email: {email}")
    
    if not InputValidator.validate_username(username):
        print("   ❌ Ungültiger Username")
        return
    print("   ✓ Username gültig")
    
    if not InputValidator.validate_email(email):
        print("   ❌ Ungültige Email")
        return
    print("   ✓ Email gültig")
    
    is_valid, errors = InputValidator.validate_password(password)
    if not is_valid:
        print("   ❌ Passwort-Fehler:")
        for error in errors:
            print(f"      - {error}")
        return
    print("   ✓ Passwort gültig")
    
    # Hash Passwort
    print(f"\n2. Hash Passwort...")
    password_hash = auth.hash_password(password)
    print(f"   Hash (erste 50 Zeichen): {password_hash[:50]}...")
    
    # Erstelle Benutzer
    print(f"\n3. Erstelle Benutzer...")
    try:
        user = db.create_user(username, email, password_hash)
        if user:
            print(f"   ✓ Benutzer erstellt: ID={user.id}, Username={user.username}")
    except Exception as e:
        print(f"   ℹ Benutzer existiert bereits oder Fehler: {e}")
        user = db.get_user_by_username(username)
    
    if not user:
        print("   ❌ Fehler beim Erstellen/Abrufen des Benutzers")
        return
    
    # Verifiziere Passwort
    print(f"\n4. Verifiziere Passwort...")
    if auth.verify_password(password, user.password_hash):
        print("   ✓ Passwort korrekt")
    else:
        print("   ❌ Passwort falsch")
    
    # Erstelle JWT Token
    print(f"\n5. Erstelle JWT Token...")
    token = ""
    if user:
        token = auth.create_jwt_token(user.id, user.username)
        print(f"   Token (erste 50 Zeichen): {token[:50]}...")
    
    # Verifiziere Token
    print(f"\n6. Verifiziere JWT Token...")
    if token:
        payload = auth.verify_jwt_token(token)
        if payload:
            print(f"   ✓ Token gültig")
            print(f"   User ID: {payload['user_id']}")
            print(f"   Username: {payload['username']}")
        else:
            print("   ❌ Token ungültig")


def demo_message_encryption():
    """Demonstriert Nachrichtenverschlüsselung"""
    print("\n" + "=" * 60)
    print("DEMO 2: Nachrichtenverschlüsselung")
    print("=" * 60)
    
    encryption = EncryptionManager()
    
    # Nachricht verschlüsseln
    message = "Dies ist eine geheime Nachricht! 🔒"
    print(f"\n1. Original-Nachricht:")
    print(f"   '{message}'")
    
    print(f"\n2. Verschlüssele Nachricht...")
    encrypted_data, nonce = encryption.encrypt(message)
    print(f"   Verschlüsselt (erste 50 Zeichen): {encrypted_data[:50]}...")
    print(f"   Nonce: {nonce}")
    
    # Nachricht entschlüsseln
    print(f"\n3. Entschlüssele Nachricht...")
    decrypted_message = encryption.decrypt(encrypted_data, nonce)
    print(f"   Entschlüsselt: '{decrypted_message}'")
    
    if decrypted_message == message:
        print("   ✓ Verschlüsselung erfolgreich!")
    else:
        print("   ❌ Verschlüsselung fehlgeschlagen!")


def demo_messaging():
    """Demonstriert Nachrichtenaustausch"""
    print("\n" + "=" * 60)
    print("DEMO 3: Nachrichtenaustausch")
    print("=" * 60)
    
    db = DatabaseManager()
    auth = AuthenticationManager(db)
    encryption = EncryptionManager()
    
    # Erstelle zwei Benutzer
    print("\n1. Erstelle Benutzer...")
    
    users = []
    for i, (username, email) in enumerate([
        ("alice", "alice@example.com"),
        ("bob", "bob@example.com")
    ], 1):
        password_hash = auth.hash_password("SecurePass123!")
        try:
            user = db.create_user(username, email, password_hash)
            print(f"   ✓ Benutzer {i}: {username}")
        except Exception:
            user = db.get_user_by_username(username)
            print(f"   ℹ Benutzer {i}: {username} (bereits vorhanden)")
        users.append(user)
    
    alice, bob = users
    
    # Sende Nachricht von Alice an Bob
    print(f"\n2. Alice sendet Nachricht an Bob...")
    message_text = "Hallo Bob! Wie geht es dir? 👋"
    encrypted_data, nonce = encryption.encrypt(message_text)
    
    if not alice or not bob:
        print("   ❌ Fehler: Benutzer nicht gefunden")
        return
    
    message = db.create_message(
        sender_id=alice.id,
        recipient_id=bob.id,
        content=encrypted_data,
        content_nonce=nonce
    )
    if message:
        print(f"   ✓ Nachricht gesendet (ID: {message.id})")
    
    # Bob liest die Nachricht
    print(f"\n3. Bob liest die Nachricht...")
    messages = db.get_messages_between_users(alice.id, bob.id, limit=10)
    
    for msg in messages:
        decrypted = encryption.decrypt(msg.content, msg.content_nonce)
        sender = db.get_user_by_id(msg.sender_id)
        if sender:
            print(f"   Von {sender.username}: '{decrypted}'")


def demo_groups():
    """Demonstriert Gruppenchat"""
    print("\n" + "=" * 60)
    print("DEMO 4: Gruppenchat")
    print("=" * 60)
    
    db = DatabaseManager()
    auth = AuthenticationManager(db)
    
    # Erstelle Benutzer
    print("\n1. Erstelle Benutzer...")
    password_hash = auth.hash_password("SecurePass123!")
    
    try:
        user1 = db.create_user("user1", "user1@example.com", password_hash)
    except Exception:
        user1 = db.get_user_by_username("user1")
    
    try:
        user2 = db.create_user("user2", "user2@example.com", password_hash)
    except Exception:
        user2 = db.get_user_by_username("user2")
    
    if not user1 or not user2:
        print("   ❌ Fehler: Benutzer nicht gefunden")
        return
    
    print(f"   ✓ {user1.username}, {user2.username}")
    
    # Erstelle Gruppe
    print(f"\n2. Erstelle Gruppe...")
    group = db.create_group(
        name="Entwickler-Chat",
        created_by=user1.id,
        description="Gruppe für Entwickler"
    )
    
    if not group:
        print("   ❌ Fehler beim Erstellen der Gruppe")
        return
    
    print(f"   ✓ Gruppe erstellt: {group.name} (ID: {group.id})")
    
    # Füge Mitglied hinzu
    print(f"\n3. Füge Mitglied hinzu...")
    db.add_group_member(group.id, user2.id)
    print(f"   ✓ {user2.username} zur Gruppe hinzugefügt")
    
    # Zeige Gruppenmitglieder
    print(f"\n4. Gruppenmitglieder:")
    members = db.get_group_members(group.id)
    for member in members:
        user = db.get_user_by_id(member.user_id)
        if user:
            print(f"   - {user.username} ({member.role})")


def main():
    """Hauptfunktion"""
    # Set UTF-8 encoding for Windows console
    import sys
    if sys.platform == 'win32':
        try:
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8')  # type: ignore
            else:
                import codecs
                sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')  # type: ignore
        except Exception:
            pass
    
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "SECURE CHAT - BEISPIEL-DEMOS" + " " * 20 + "║")
    print("╚" + "=" * 58 + "╝")
    
    try:
        # Führe alle Demos aus
        demo_user_registration()
        demo_message_encryption()
        demo_messaging()
        demo_groups()
        
        print("\n" + "=" * 60)
        print("✅ Alle Demos erfolgreich abgeschlossen!")
        print("=" * 60)
        print()
        
    except KeyboardInterrupt:
        print("\n\n❌ Abgebrochen durch Benutzer")
    except Exception as e:
        print(f"\n\n❌ Fehler: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
