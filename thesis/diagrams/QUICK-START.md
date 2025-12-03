# Diagram System - Quick Start

5 perces gyors útmutató a diagram rendszer használatához.

## 📋 Előfeltételek

```bash
cd /home/kari/thesis-szakdoga/thesis/diagrams
```

Nincs szükség telepítésre - minden működik out-of-the-box!

## 🚀 Használat 3 Lépésben

### 1️⃣ HTML Generálás

```bash
./generate-all.sh
```

**Kimenet:** `output/html/` - 11 HTML fájl

### 2️⃣ Index Generálás

```bash
python3 generate-index.py
```

**Kimenet:** `output/index.html`

### 3️⃣ Megnyitás Böngészőben

```bash
xdg-open output/index.html
# vagy
firefox output/index.html
```

✅ **Kész!** Minden diagram elérhető böngészőben.

## 📥 SVG/PNG Export

### Módszer A: Böngésző Console (Ajánlott)

1. Nyisd meg a HTML-t böngészőben
2. **F12** → Console
3. Illeszd be:

**SVG Export:**
```javascript
const svg=document.querySelector('.mermaid svg');const svgData=new XMLSerializer().serializeToString(svg);const blob=new Blob([svgData],{type:'image/svg+xml'});const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download=document.title.replace(/[^a-z0-9]/gi,'_')+'.svg';link.click();
```

**PNG Export:**
```javascript
const svg=document.querySelector('.mermaid svg');const svgData=new XMLSerializer().serializeToString(svg);const canvas=document.createElement('canvas');const ctx=canvas.getContext('2d');const img=new Image();img.onload=function(){canvas.width=img.width*2;canvas.height=img.height*2;ctx.fillStyle='white';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(img,0,0,canvas.width,canvas.height);canvas.toBlob(blob=>{const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download=document.title.replace(/[^a-z0-9]/gi,'_')+'.png';link.click();})};img.src='data:image/svg+xml;base64,'+btoa(unescape(encodeURIComponent(svgData)));
```

### Módszer B: Mermaid Live

1. Másold ki a kódot: `cat source/phase1_user_onboarding_compact.md`
2. https://mermaid.live → Paste
3. Actions → PNG/SVG

### Módszer C: PDF Print

```bash
# Chrome
google-chrome --headless --print-to-pdf=output.pdf output/html/phase1.html

# Vagy böngészőből: Ctrl+P → Save as PDF
```

## 📝 Diagram Szerkesztés

### 1. Szerkeszd a Source Fájlt

```bash
# Pl.
nano source/phase1_user_onboarding_compact.md
```

### 2. Generálás Újra

```bash
./generate-all.sh
python3 generate-index.py
```

### 3. Frissítés Böngészőben

```bash
# Ctrl+R vagy F5 a böngészőben
```

## 🔄 Verziókezelés

**Automatikus!** Újra futtatásnál nem írja felül:

```bash
./generate-all.sh  # Első futtatás
# Kimenet: phase1.html

./generate-all.sh  # Második futtatás
# Kimenet: phase1_v1.html (eredeti változatlan)

./generate-all.sh  # Harmadik futtatás
# Kimenet: phase1_v2.html
```

Részletek: [VERSIONING.md](VERSIONING.md)

## 📚 Fájl Struktúra

```
diagrams/
├── source/              # Szerkeszd ezeket!
│   ├── phase1_user_onboarding_compact.md
│   ├── phase2_configuration_creation_compact.md
│   └── ...
│
├── output/
│   ├── html/            # Generált HTML-ek
│   ├── svg/             # Manuális export ide
│   ├── png/             # Manuális export ide
│   └── index.html       # Főoldal
│
└── generate-*.sh        # Script-ek
```

## 🎨 Diagram Típusok

| Fájl | Leírás | Diagram Típus |
|------|--------|---------------|
| phase1 | User onboarding | Flowchart LR |
| phase2 | Configuration | Flowchart TB |
| phase3 | VM provisioning | Flowchart TB (subgraphs) |
| phase4a | Docker deploy | Flowchart TB |
| phase4b | NixOS deploy | Flowchart TB |
| phase5 | Traefik SSL | Flowchart TB |
| phase6 | LDAP SSO | Flowchart TB |
| phase7 | Service provision | Flowchart LR |
| phase8 | User access | Flowchart TB |
| phase9 | Monitoring | Flowchart TB |
| summary | Complete journey | Flowchart TB (subgraphs) |

## 🔧 Troubleshooting

### HTML nem látszik

```bash
# Ellenőrizd a generálást
ls -lh output/html/
# Nyisd meg közvetlenül
firefox output/html/phase1_user_onboarding_compact.html
```

### SVG/PNG script nem működik

**Normális!** A mermaid-cli gyakran problémás WSL-ben.

**Megoldás:** Használd a böngésző console scriptet (lásd fent)

### Diagram szintaxis hiba

```bash
# Teszteld online
# 1. Másold ki a Mermaid kódot
cat source/phase1_user_onboarding_compact.md

# 2. https://mermaid.live
# 3. Paste → Javítsd a hibákat
# 4. Másold vissza a fájlba
```

## 📖 Teljes Dokumentáció

- **README.md** - Részletes használati útmutató
- **VERSIONING.md** - Verziókezelés magyarázat
- **export-from-browser.md** - SVG/PNG export részletesen
- **SUMMARY.md** - Projekt összefoglaló
- **CHANGELOG.md** - Változások története

## 🎯 Leggyakoribb Munkafolyamatok

### Új Diagram Hozzáadása

```bash
# 1. Hozz létre új MD fájlt
cp source/phase1_user_onboarding_compact.md source/phase11_new_feature_compact.md

# 2. Szerkeszd
nano source/phase11_new_feature_compact.md

# 3. Generálás
./generate-all.sh
python3 generate-index.py
```

### Batch Export Minden Diagramhoz

```bash
# 1. Nyisd meg az index.html-t
firefox output/index.html

# 2. Készíts bookmarklet-et a console scriptekből
# (lásd export-from-browser.md)

# 3. Kattints minden diagram linken
# 4. Kattints a bookmarklet-re minden oldalon
```

### LaTeX Integrálás

```latex
\begin{figure}[h]
    \centering
    \includegraphics[width=0.9\textwidth]{diagrams/output/png/phase1_user_onboarding_compact.png}
    \caption{Felhasználói regisztráció és bejelentkezés}
    \label{fig:phase1}
\end{figure}
```

## 💡 Tippek

1. **Mindig a `*_compact.md` fájlokat szerkeszd** - Ezek A4-re optimalizáltak
2. **Használd a subgraph-okat** - Több oszlopos layouthoz
3. **Teszteld mermaid.live-on** - Gyorsabb debug
4. **Bookmarklet** - Gyors export minden diagramhoz
5. **Git commit** - Verziózd a source fájlokat

## ⚡ Egyetlen Parancs Workflow

```bash
# Mindent egyben
./generate-all.sh && python3 generate-index.py && xdg-open output/index.html
```

---

**Gyors Referencia Kész!** Részletekhez lásd a teljes dokumentációt.
