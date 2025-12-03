# Fázis 8: Végfelhasználói Hozzáférés SSO-val

```mermaid
%%{init: {"theme": "base", "themeVariables": { "fontSize": "14px"}}}%%
flowchart LR

    subgraph PHASE8_USER_ACCESS_SSO ["Fázis 8: Végfelhasználói Hozzáférés SSO-val"]
        direction TB

        subgraph INITIAL_REQUEST ["Első Kérés - Nincs Session"]
            direction TB
            P1["1. Felhasználó Böngésző"] --> P2["2. Traefik"]
            P2 --> P3["3. Authelia Forward Auth"]
            P3 --> P4{4. Session?}
            P4 -->|No| P5["5. 302 Átirányítás:<br/>auth.example.com"]
        end

        subgraph USER_AUTHENTICATION ["Felhasználó Autentikáció"]
            direction TB
            P6["6. Login Form"] --> P7["7. Username + Jelszó"]
            P7 --> P8["8. LDAP Bind Kérés"]
            P8 --> P9{9. 2FA Engedélyezve?}
            P9 -->|Yes| P10["10. TOTP Kód Bekérés"]
            P9 -->|No| P11["11. Session Létrehozás"]
            P10 --> P11
            P11 --> P12["12. Set-Cookie: authelia_session"]
        end

        subgraph AUTHENTICATED_ACCESS ["Hozzáférés Engedélyezve"]
            direction TB
            P13["13. Böngésző + Cookie"] --> P14["14. Traefik"]
            P14 --> P15["15. Authelia Forward Auth"]
            P15 --> P16{16. Session Érvényes?}
            P16 -->|Yes| P17["17. 200 OK + Fejlécek"]
            P17 --> P18["18. Kérés Továbbítás Szolgáltatáshoz"]
            P18 --> P19["19. Szolgáltatás Válasz"]
            P19 --> P20["20. Válasz - Felhasználó Bejelentkezve"]
        end

        subgraph SSO_BENEFIT ["SSO Előny"]
            direction TB
            P21["21. Következő Szolgáltatás Elérés"] --> P22["22. Ugyanaz a Session Cookie"]
            P22 --> P23(["23. SSO Zökkenőmentes Login"])
        end

        INITIAL_REQUEST --> USER_AUTHENTICATION
        USER_AUTHENTICATION --> AUTHENTICATED_ACCESS
        AUTHENTICATED_ACCESS --> SSO_BENEFIT

        P5 --> P6
        P12 --> P13
        P20 --> P21
        P16 -->|No| P5 %% Redirect to login if session invalid
    end

    %% --- STYLING ---
    style PHASE8_USER_ACCESS_SSO fill:#f9f9f9,stroke:#333,stroke-width:2px
    style INITIAL_REQUEST fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style USER_AUTHENTICATION fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style AUTHENTICATED_ACCESS fill:#e1bee7,stroke:#7b1fa2,stroke-width:2px
    style SSO_BENEFIT fill:#bbdefb,stroke:#1976d2,stroke-width:2px

    style P23 fill:#28a745,stroke:#1e7e34,color:#ffffff,stroke-width:2px
```