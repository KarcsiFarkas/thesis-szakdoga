# Fázis 1: Felhasználói Regisztráció és Bejelentkezés

```mermaid
%%{init: {"theme": "base", "themeVariables": { "fontSize": "14px"}}}%%
flowchart LR
    subgraph PHASE1 ["Fázis 1: Felhasználói Regisztráció és Bejelentkezés"]
        direction TB
        
        subgraph SUB1 ["Regisztráció"]
            direction TB
            P1["1. Új Felhasználó"] --> P2["2. Form Kitöltés"]
            P2 --> P3["3. Validálás"]
            P3 --> P4["4. bcrypt Hash"]
            P4 --> P5["5. SQLite Mentés"]
        end
        
        subgraph SUB2 ["Bejelentkezés"]
            direction TB
            P6["6. Meglévő User"] --> P7["7. Credentials"]
            P7 --> P8["8. Hash Ellenőrzés"]
            P8 --> P9["9. Session Init"]
            P9 --> P10["10. Cookie Set"]
        end
        
        subgraph SUB3 ["Dashboard"]
            direction TB
            P11["11. Dashboard"] --> P12["12. Akció"]
            P12 --> P13["13. Új Config"]
            P12 --> P14["14. Deploy"]
        end
        
        SUB1 --> SUB2 --> SUB3
    end

    %% --- STYLING ---
    style PHASE1 fill:#f9f9f9,stroke:#333,stroke-width:2px
    
    style SUB1 fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style SUB2 fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style SUB3 fill:#e1bee7,stroke:#7b1fa2,stroke-width:2px
    
    style P1 fill:#e3f2fd,stroke:#1976d2,stroke-width:1px
    style P2 fill:#e3f2fd,stroke:#1976d2,stroke-width:1px
    style P3 fill:#e3f2fd,stroke:#1976d2,stroke-width:1px
    style P4 fill:#e3f2fd,stroke:#1976d2,stroke-width:1px
    style P5 fill:#e3f2fd,stroke:#1976d2,stroke-width:1px

    style P6 fill:#fff3e0,stroke:#f57c00,stroke-width:1px
    style P7 fill:#fff3e0,stroke:#f57c00,stroke-width:1px
    style P8 fill:#fff3e0,stroke:#f57c00,stroke-width:1px
    style P9 fill:#fff3e0,stroke:#f57c00,stroke-width:1px
    style P10 fill:#fff3e0,stroke:#f57c00,stroke-width:1px

    style P11 fill:#e1bee7,stroke:#7b1fa2,stroke-width:1px
    style P12 fill:#e1bee7,stroke:#7b1fa2,stroke-width:1px
    style P13 fill:#e1bee7,stroke:#7b1fa2,stroke-width:1px
    style P14 fill:#28a745,stroke:#1e7e34,color:#ffffff,stroke-width:2px
```
