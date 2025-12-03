# PaaS Diagram Generation System

Automatikus diagram generálás HTML, SVG és PNG formátumokba A4-es oldal mérethez optimalizálva.

## Könyvtár Struktúra

```
diagrams/
├── source/                          # Forrás Markdown fájlok
│   ├── phase1_user_onboarding_compact.md
│   ├── phase2_configuration_creation_compact.md
│   ├── phase3_vm_provisioning_compact.md
│   ├── phase4a_docker_deployment_compact.md
│   ├── phase4b_nixos_deployment_compact.md
│   ├── phase5_traefik_ssl_compact.md
│   ├── phase6_ldap_sso_compact.md
│   ├── phase7_service_provisioning_compact.md
│   ├── phase8_user_access_sso_compact.md
│   ├── phase9_operational_monitoring_compact.md
│   └── summary_complete_journey_compact.md
│
├── output/                          # Generált kimenetek
│   ├── html/                        # HTML verziók (Mermaid CDN)
│   ├── svg/                         # SVG exportok
│   ├── png/                         # PNG exportok
│   └── index.html                   # Index oldal
│
├── generate-all.sh                  # HTML generálás
├── generate-svg-png.sh              # SVG/PNG npm módszer
├── generate-svg-png-docker.sh       # SVG/PNG Docker módszer
├── generate-index.py                # Index generálás
└── README.md                        # Ez a fájl
```

## Gyors Használat

### 1. HTML Generálás (Ajánlott)

```bash
# Generálj HTML fájlokat (Mermaid CDN-nel)
./generate-all.sh

# Generálj index oldalt
python3 generate-index.py

# Nyisd meg böngészőben
xdg-open output/index.html
```

**💡 Automatikus Verziókezelés:**
- Ha újra futtatod a script-et, nem írja felül a meglévő fájlokat
- Helyette `filename_v1.html`, `filename_v2.html` stb. verziókat hoz létre
- Részletek: [VERSIONING.md](VERSIONING.md)

Ez létrehozza az összes diagramot interaktív HTML formátumban, amely:
- ✓ A4 oldal mérethez optimalizált
- ✓ Böngészőben azonnal megtekinthető
- ✓ Nyomtatható (Ctrl+P)
- ✓ Nincs szükség külső függőségekre

### 2. SVG/PNG Export Módszerek

#### Módszer A: Manuális Export (Ajánlott minőséghez)

1. Nyisd meg a HTML fájlt böngészőben
2. Használd a böngésző Developer Tools-t (F12)
3. Console-ban futtasd:
   ```javascript
   // SVG mentés
   const svg = document.querySelector('.mermaid svg');
   const svgData = new XMLSerializer().serializeToString(svg);
   const blob = new Blob([svgData], { type: 'image/svg+xml' });
   const url = URL.createObjectURL(blob);
   const a = document.createElement('a');
   a.href = url;
   a.download = 'diagram.svg';
   a.click();
   ```

4. Vagy használd a [Mermaid Live Editor](https://mermaid.live):
   - Másold ki a Mermaid kódot a `.md` fájlból
   - Illeszd be a mermaid.live-ba
   - Kattints "Actions" → "PNG/SVG/PDF"

#### Módszer B: Docker (Automatikus, de lehet instabil)

```bash
# Docker képfájl letöltése
docker pull minlag/mermaid-cli

# SVG és PNG generálás
./generate-svg-png-docker.sh
```

**Figyelmeztetés:** A mermaid-cli Docker image nem mindig működik tökéletesen minden Mermaid szintaxissal. Ha üres fájlokat kapsz, használd a manuális módszert.

#### Módszer C: NPM (Ha telepítve van Node.js)

```bash
# Mermaid CLI telepítés
npm install -g @mermaid-js/mermaid-cli

# SVG és PNG generálás
./generate-svg-png.sh
```

## Diagram Jellemzők

### A4 Optimalizálás

- **Szélesség:** 1200px (optimális A4 nyomtatáshoz)
- **Layout:** Több oszlopos, kompakt elrendezés
- **Betűméret:** 13-14px (olvasható nyomtatva)
- **Margók:** 2cm minden oldalon (A4 standard)

### Diagram Típusok

1. **Flowchart TB/LR** - Folyamatábrák (felülről le, balról jobbra)
2. **Subgraph** - Logikai csoportosítás több oszlopban
3. **Direction:** TB/LR/RL - Irány kontroll kompakt layouthoz

### Színkódok

- 🔵 **Kék (#e3f2fd):** Felhasználói műveletek
- 🟠 **Narancs (#fff3e0):** Konfiguráció
- 🟣 **Lila (#e1bee7):** Infrastruktúra
- 🟢 **Zöld (#c8e6c9):** Sikeres állapot
- 🔴 **Piros (#f8d7da):** Hiba/rollback

## Diagram Módosítás

### Új Diagram Hozzáadása

1. Hozz létre új `.md` fájlt a `source/` mappában:
   ```markdown
   # Diagram Címe

   ```mermaid
   %%{init: {'theme':'base', 'themeVariables': { 'fontSize':'14px'}}}%%
   flowchart TB
       A[Start] --> B[End]
   ```
   ```

2. Futtasd a generálást:
   ```bash
   ./generate-all.sh
   python3 generate-index.py
   ```

### Meglévő Diagram Módosítása

1. Szerkeszd a megfelelő `.md` fájlt a `source/` mappában
2. Futtasd újra a generálást
3. Frissítsd a böngészőt (Ctrl+R)

## Mermaid Szintaxis Tippek

### Kompakt Layout Trükkök

```mermaid
# Több oszlopos layout subgraph-okkal
flowchart TB
    subgraph COL1[Első Oszlop]
        direction TB
        A --> B
    end

    subgraph COL2[Második Oszlop]
        direction TB
        C --> D
    end

    COL1 --> COL2
```

### A4-re Optimalizálás

1. **Használj subgraph-okat** - Logikai csoportosítás
2. **Állítsd be a direction-t** - `direction LR` vagy `direction TB`
3. **Limit node szöveg** - Max 3-4 sor per node
4. **Kerüld a hosszú label-eket** - Használj `<br/>` sortörést

### Stílus Vezérlés

```mermaid
style NodeID fill:#color,stroke:#color,stroke-width:2px
```

## Troubleshooting

### HTML nem jelenik meg

```bash
# Ellenőrizd a fájl létezését
ls -lh output/html/

# Nézd meg a Mermaid kódot
cat source/phase1_user_onboarding_compact.md

# Böngésző Console hibák ellenőrzése (F12)
```

### SVG/PNG generálás sikertelen

**Tünet:** Üres vagy hiányzó fájlok

**Megoldás:**
1. Használd a manuális export módszert (lásd fent)
2. Vagy használj online eszközt: https://mermaid.live
3. Vagy használd a Mermaid VSCode extension-t

### Docker jogosultsági hiba

```bash
# Add hozzá magad a docker csoporthoz
sudo usermod -aG docker $USER
newgrp docker

# Vagy futtasd sudo-val
sudo ./generate-svg-png-docker.sh
```

## LaTeX Integráció

### Includálás Thesis-be

```latex
\begin{figure}[h]
    \centering
    \includegraphics[width=0.9\textwidth]{diagrams/output/png/phase1_user_onboarding_compact.png}
    \caption{Felhasználói regisztráció és bejelentkezés folyamata}
    \label{fig:phase1}
\end{figure}
```

### PDF Export

HTML-ből nyomtatással:
```bash
# Chrome/Chromium headless
google-chrome --headless --print-to-pdf=output.pdf output/html/phase1.html

# Vagy böngészőből: File → Print → Save as PDF
```

## Hasznos Linkek

- **Mermaid Dokumentáció:** https://mermaid.js.org/
- **Mermaid Live Editor:** https://mermaid.live
- **Mermaid Syntax:** https://mermaid.js.org/syntax/flowchart.html
- **VSCode Extension:** https://marketplace.visualstudio.com/items?itemName=bierner.markdown-mermaid

## Licensz

BME-VIK Diplomaterv - Belső használatra
