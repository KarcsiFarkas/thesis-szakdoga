# Fázis 6: LDAP & Authelia SSO

```mermaid
%%{init: {'theme':'base', 'themeVariables': { 'fontSize':'13px'}}}%%
flowchart TB
    subgraph LDAP[LLDAP Setup]
        direction LR
        A[SQLite DB] --> B[Base DN<br/>dc=example,dc=com]
        B --> C[Admin User]
    end

    subgraph PROV[User Provisioning]
        direction TB
        D[GraphQL API] --> E{Password?}
        E -->|Universal| F[Same for All]
        E -->|Generated| G[Unique<br/>Vaultwarden]
        F --> H[LDAP User<br/>Created]
        G --> H
    end

    subgraph AUTH[Authelia Config]
        direction LR
        I[LDAP Backend] --> J[Redis<br/>Session]
        J --> K[2FA TOTP]
    end

    subgraph MIDDLEWARE[Traefik Integration]
        direction TB
        L[Service<br/>Request] --> M{Authenticated?}
        M -->|No| N[Redirect<br/>Login]
        M -->|Yes| O[Set Headers<br/>Remote-User]
        O --> P[Forward to<br/>Service]
    end

    subgraph LOGIN[Login Flow]
        direction LR
        Q[Credentials] --> R[LDAP Bind]
        R --> S[2FA Check?]
        S --> T[Session<br/>Cookie]
    end

    C --> D
    H --> I
    K --> L
    N --> Q
    T --> M
    P --> U([SSO Active])

    style U fill:#d4edda,stroke:#28a745,stroke-width:2px
```
