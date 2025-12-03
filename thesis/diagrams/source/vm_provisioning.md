
flowchart TD
    %% Nodes
    Start([1. Terraform Config<br/>2 vCPU, 4GB RAM])
    Plan[2. Terraform Plan]
    Apply[3. Terraform Apply]
    Boot[4. VM Boot &<br/>Cloud-init]
    SSH{5. SSH<br/>Check}
    Destroy[6. Terraform Destroy]
    Loop{7. 20x<br/>Ciklus}
    
    %% Logic Flow
    Start --> Plan --> Apply --> Boot --> SSH
    SSH -- OK --> Destroy --> Loop
    Loop -- Még van --> Start
    Loop -- Kész --> Success([✓ EREDMÉNY: SIKERES])

    %% Subgraph for Results
    subgraph Results [Mérési Eredmények]
        direction TB
        R1[20/20 Provisioning OK]
        R2[Nincs Orphaned VM]
        R3[DHCP: 100% OK]
        R4[Cloud-init: OK]
        
        Success --- R1 & R2 & R3 & R4
    end

    %% Subgraph for Issues
    subgraph Issues [Talált Hibák és Javítások]
        H1[Hiba #1: Cloud-init Timeout] -.-> F1[Javítás: Timeout 60s]
        H2[Hiba #2: QEMU Agent késés] -.-> F2[Javítás: Systemd dependency]
    end

    %% Styling
    style Success fill:#d4edda,stroke:#28a745,stroke-width:2px
    style R1 fill:#fff,stroke:none
    style R2 fill:#fff,stroke:none
    style R3 fill:#fff,stroke:none
    style R4 fill:#fff,stroke:none
    style H1 fill:#f8d7da,stroke:#dc3545
    style H2 fill:#f8d7da,stroke:#dc3545
    style F1 fill:#e2e3e5,stroke:#333,stroke-dasharray: 5 5
    style F2 fill:#e2e3e5,stroke:#333,stroke-dasharray: 5 5
