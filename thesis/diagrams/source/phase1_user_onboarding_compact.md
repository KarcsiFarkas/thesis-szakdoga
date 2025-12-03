# Fázis 1: Felhasználói Regisztráció és Bejelentkezés

```mermaid
%%{init: {'theme':'base', 'themeVariables': { 'fontSize':'14px'}}}%%
flowchart LR
    subgraph REG[Regisztráció]
        direction TB
        A[Új Felhasználó] --> B[Form Kitöltés<br/>user/email/pwd]
        B --> C[Validálás]
        C --> D[bcrypt Hash]
        D --> E[SQLite Mentés]
    end

    subgraph LOGIN[Bejelentkezés]
        direction TB
        F[Meglévő User] --> G[Credentials<br/>Megadás]
        G --> H[Hash<br/>Ellenőrzés]
        H --> I[Session<br/>Létrehozás]
        I --> J[Cookie<br/>Beállítás]
    end

    E --> K[Dashboard]
    J --> K

    K --> L{Akció}
    L -->|Új Config| M[Konfiguráció<br/>Létrehozás]
    L -->|View| N[Meglévő<br/>Configs]
    L -->|Deploy| O[Deployment<br/>Indítás]

    style K fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style M fill:#e3f2fd,stroke:#1976d2
    style N fill:#e3f2fd,stroke:#1976d2
    style O fill:#c8e6c9,stroke:#43a047
```
