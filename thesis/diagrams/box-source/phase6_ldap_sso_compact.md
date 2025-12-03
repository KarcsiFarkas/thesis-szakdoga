# Fázis 6: LDAP & Authelia SSO Integráció

```mermaid
%%{init: {"theme": "base", "themeVariables": { "fontSize": "14px"}}}%%
flowchart LR

    subgraph PHASE6_LDAP_SSO ["Fázis 6: LDAP & Authelia SSO Integráció"]
        direction TB

        subgraph LDAP_SETUP ["LDAP Beállítás"]
            direction TB
            P1["1. LLDAP Konténer Indítás"] --> P2["2. Adatbázis Inicializálás"]
            P2 --> P3["3. Base DN Létrehozás"]
            P3 --> P4["4. Admin Felhasználó Létrehozás"]
        end

        subgraph USER_PROVISIONING ["Felhasználó Provisioning"]
            direction TB
            P5["5. Provisioning Script"] --> P6["6. GraphQL API Hívás"]
            P6 --> P7{7. Jelszó Típus?}
            P7 -->|Univerzális| P8["8. Azonos Jelszó Beállítása"]
            P7 -->|Generált| P9["9. Egyedi Jelszó Generálás"]
            P8 & P9 --> P10["10. Felhasználó LDAP-ban"]
        end

        subgraph AUTHELIA_CONFIG ["Authelia Konfiguráció"]
            direction TB
            P11["11. Authelia Config Olvasás"] --> P12["12. LLDAP-hez Csatlakozás"]
            P12 --> P13["13. Session Beállítás"]
            P13 --> P14["14. 2FA Beállítás"]
        end

        subgraph SERVICE_INTEGRATION ["Szolgáltatás Integráció"]
            direction TB
            P15["15. Traefik Middleware"] --> P16["16. Védett Útvonalak"]
            P16 --> P17{17. Felhasználó Hitelesítve?}
            P17 -->|Nem| P18["18. Átirányítás Login-ra"]
            P17 -->|Igen| P19["19. Fejlécek Beállítása"]
            P19 --> P20["20. Továbbítás Szolgáltatáshoz"]
        end

        subgraph LOGIN_FLOW ["Login Folyamat"]
            direction TB
            P21["21. Felhasználói Login Form"] --> P22["22. LDAP Bind"]
            P22 --> P23{23. 2FA Engedélyezve?}
            P23 -->|Igen| P24["24. TOTP Kód Bekérés"]
            P23 -->|Nem| P25(["25. SSO Aktív"])
            P24 --> P25
        end

        LDAP_SETUP --> USER_PROVISIONING
        USER_PROVISIONING --> AUTHELIA_CONFIG
        AUTHELIA_CONFIG --> SERVICE_INTEGRATION
        SERVICE_INTEGRATION --> LOGIN_FLOW

        P4 --> P5
        P10 --> P11
        P14 --> P15
        P18 --> P21
    end

    %% --- STYLING ---
    style PHASE6_LDAP_SSO fill:#f9f9f9,stroke:#333,stroke-width:2px
    style LDAP_SETUP fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style USER_PROVISIONING fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style AUTHELIA_CONFIG fill:#e1bee7,stroke:#7b1fa2,stroke-width:2px
    style SERVICE_INTEGRATION fill:#bbdefb,stroke:#1976d2,stroke-width:2px
    style LOGIN_FLOW fill:#c5e1a5,stroke:#558b2f,stroke-width:2px

    style P25 fill:#28a745,stroke:#1e7e34,color:#ffffff,stroke-width:2px
```
