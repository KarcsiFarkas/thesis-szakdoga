
sequenceDiagram
    autonumber
    participant User as Tesztelő
    participant Flake as Nix Flakes
    participant System as NixOS Host (WSL)
    participant Service as Systemd Services

    Note over User, System: Fázis 1: Build és Aktiválás
    User->>Flake: 1. nix flake check
    User->>System: 2. nixos-rebuild build
    User->>System: 3. nixos-rebuild switch (Activation)
    
    rect rgb(240, 255, 240)
        Note over System, Service: Fázis 2: Validáció
        System->>Service: Start Services (Traefik, LLDAP...)
        Service-->>User: 4. Status: Active (Running)
    end

    rect rgb(255, 240, 240)
        Note over User, System: Fázis 3: Rollback Teszt
        User->>System: 5. switch --rollback
        System-->>User: Visszaállás kész (< 5mp)
    end

    Note right of User: Eredmény (10x ciklus):<br/>✓ 10/10 Siker<br/>✓ Cache Hit: 92%
