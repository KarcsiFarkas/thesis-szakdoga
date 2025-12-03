
graph LR
    %% Main Flow
    Clean[1. Clean State<br/>docker-compose down -v] --> Script[2. Deploy Script<br/>deploy-docker-with-ldap...]
    Script --> Health[3. Service<br/>Health Check]
    Health --> Smoke[4. Smoke Test<br/>Nextcloud Login]
    Smoke --> Loop{15x<br/>Ismétlés}
    
    Loop -- Siker --> Final([✓ EREDMÉNY: 100%])

    %% Details Container
    subgraph Validation [Validációs Kritériumok]
        V1[Services: Healthy]
        V2[LDAP Auth: OK]
        V3[Traefik Routing: OK]
        V4[SSL: Let's Encrypt OK]
    end
    
    Final -.-> V1 & V2 & V3 & V4

    %% Styling
    style Final fill:#d4edda,stroke:#28a745,stroke-width:2px,font-weight:bold
    style Clean fill:#e1f5fe,stroke:#0277bd
    style Script fill:#e1f5fe,stroke:#0277bd
    style Health fill:#fff9c4,stroke:#fbc02d
    style Smoke fill:#fff9c4,stroke:#fbc02d
