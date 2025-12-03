# Fázis 1: Felhasználói Regisztráció és Bejelentkezés

Felhasználói regisztráció, bejelentkezés és kezdeti dashboard elérés folyamata.

```mermaid
sequenceDiagram
    autonumber
    participant U as Felhasználó
    participant F as Flask Alkalmazás
    participant DB as SQLite Adatbázis
    participant S as Session Manager

    Note over U,DB: Regisztrációs Útvonal (Új Felhasználó)
    U->>F: POST /register
    F->>F: Form Adatok Validálása
    F->>F: Jelszó Hash (bcrypt)
    F->>DB: INSERT User Rekord
    DB-->>F: Felhasználó Létrehozva (ID)
    F-->>U: Átirányítás /login-ra

    Note over U,DB: Bejelentkezési Útvonal (Meglévő Felhasználó)
    U->>F: POST /login
    F->>DB: SELECT FelhasználóUsername alapján
    DB-->>F: User Rekord + Hash
    F->>F: Jelszó Hash Ellenőrzése
    F->>S: Session Cookie Létrehozása
    S-->>F: Session Token
    F-->>U: Cookie Beállítás & Átirányítás /dashboard-ra

    Note over U: Eredmény: Hitelesített Felhasználó<br/>Hozzáférés a Dashboard-hoz
```

## Folyamat Leírása

A felhasználói onboarding folyamat két fő útvonalon halad. Az új felhasználók regisztrációkor megadják felhasználónevüket, email címüket és jelszavukat, amelyet a Flask alkalmazás bcrypt algoritmussal hashel mielőtt az SQLite adatbázisba mentené. A sikeres regisztráció után a felhasználó automatikusan átirányításra kerül a bejelentkezési oldalra.

A meglévő felhasználók bejelentkezéskor a rendszer lekéri a felhasználói rekordot az adatbázisból, ellenőrzi a megadott jelszó hash-ét a tárolt hash-sel szemben, és sikeres autentikáció esetén létrehoz egy session cookie-t. Ez a cookie biztonságosan tárolja a felhasználói munkamenet azonosítóját, amely lehetővé teszi az állapotmegőrzést a HTTP kérések között.

## Technikai Részletek

- **Autentikáció**: Flask-Login extension használata
- **Jelszó Biztonság**: Bcrypt hash (work factor: 12)
- **Session Tárolás**: Server-side sessions Flask-SQLAlchemy-vel
- **CSRF Védelem**: WTForms automatic token generation
- **Kimenet**: Sikeres bejelentkezés után hozzáférés a felhasználói dashboard-hoz
