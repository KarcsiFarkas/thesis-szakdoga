%%{init: {"theme": "base", "themeVariables": { "fontSize": "14px"}}}%%
flowchart LR
    %% --- PHASE 1: LEFT TO RIGHT ---
    subgraph PHASE1 ["Fázis 1: Előkészítés"]
        direction TB
        subgraph USER["Felhasználó"]
            direction TB
            P1["1. Regisztráció"] --> P2["2. Konfiguráció"]
        end

        subgraph INFRA["Infrastruktúra"]
            direction TB
            P3["3. VM Provisioning<br/>(Terraform)"]
        end
        
        USER --> INFRA
    end

    %% --- PHASE 2: RIGHT TO LEFT ---
    subgraph PHASE2 ["Fázis 2: Platform & Hálózat"]
        direction TB
        
        subgraph DEPLOY["Deployment"]
            direction LR
            P4A["4A. Docker"]
            P4B["4B. NixOS"]
        end
        
        subgraph SSL["SSL"]
            direction TB
            P5["5. Traefik SSL"]
        end
        
        subgraph NETWORK["Biztonság"]
            direction TB
            P6["6. LDAP/SSO"]
        end
        
        DEPLOY --> SSL --> NETWORK
    end

    %% --- PHASE 3: LEFT TO RIGHT ---
    subgraph PHASE3 ["Fázis 3: Szolgáltatás"]
        direction TB
        
        subgraph SERVICES["Szolgáltatások"]
            direction TB
            P7["7. Provisioning"] --> P8["8. Access"]
        end
        
        subgraph OPS["Működés"]
            direction TB
            P9["9. Monitoring"] --> FINAL(["✓ Kész PaaS"])
        end
        
        SERVICES --> OPS
    end

    %% --- SNAKE CONNECTIONS ---
    INFRA ==> DEPLOY
    NETWORK ==> SERVICES

    %% --- STYLING ---
    style PHASE1 fill:#f9f9f9,stroke:#333,stroke-width:2px
    style PHASE2 fill:#f9f9f9,stroke:#333,stroke-width:2px
    style PHASE3 fill:#f9f9f9,stroke:#333,stroke-width:2px

    style USER fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style INFRA fill:#e1bee7,stroke:#7b1fa2,stroke-width:2px
    style DEPLOY fill:#c5e1a5,stroke:#558b2f,stroke-width:2px
    style SSL fill:#ffecb3,stroke:#ffa000,stroke-width:2px
    style NETWORK fill:#ffccbc,stroke:#e64a19,stroke-width:2px
    style SERVICES fill:#d1c4e9,stroke:#5e35b1,stroke-width:2px
    style OPS fill:#c8e6c9,stroke:#43a047,stroke-width:2px

    style P1 fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style P2 fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style P3 fill:#e1bee7,stroke:#7b1fa2,stroke-width:2px
    style P4A fill:#c5e1a5,stroke:#558b2f,stroke-width:2px
    style P4B fill:#c5e1a5,stroke:#558b2f,stroke-width:2px
    style P5 fill:#ffecb3,stroke:#ffa000,stroke-width:2px
    style P6 fill:#ffccbc,stroke:#e64a19,stroke-width:2px
    style P7 fill:#d1c4e9,stroke:#5e35b1,stroke-width:2px
    style P8 fill:#d1c4e9,stroke:#5e35b1,stroke-width:2px
    style P9 fill:#c8e6c9,stroke:#43a047,stroke-width:2px
    style FINAL fill:#28a745,stroke:#1e7e34,color:#ffffff,stroke-width:2px
