# Diagram System Documentation Index

Complete documentation for the PaaS Infrastructure Diagram Generation System.

## 📚 Documentation Files

### Getting Started
- **[QUICK-START.md](QUICK-START.md)** - 5 perces gyors útmutató (START HERE!)
- **[README.md](README.md)** - Részletes használati útmutató és technikai referencia

### Core Features
- **[VERSIONING.md](VERSIONING.md)** - Automatikus verziókezelés működése
- **[export-from-browser.md](export-from-browser.md)** - SVG/PNG export böngészőből (ajánlott módszer)

### Project Info
- **[SUMMARY.md](SUMMARY.md)** - Projekt összefoglaló és státusz
- **[CHANGELOG.md](CHANGELOG.md)** - Verzió történet és változások

## 🚀 Gyors Linkek

### Kezdőknek
1. [QUICK-START.md](QUICK-START.md#-használat-3-lépésben) - 3 lépéses gyors használat
2. [README.md](README.md#gyors-használat) - Részletes első lépések

### Fejlett Használat
1. [VERSIONING.md](VERSIONING.md#hogyan-működik) - Verziókezelés részletesen
2. [export-from-browser.md](export-from-browser.md#módszer-1-automatikus-böngésző-script-egyszerű) - Export módszerek

### Troubleshooting
1. [QUICK-START.md](QUICK-START.md#-troubleshooting) - Gyakori problémák
2. [README.md](README.md#troubleshooting) - Részletes hibaelhárítás
3. [export-from-browser.md](export-from-browser.md#hibakeresés) - Export problémák

## 📖 Olvasási Sorrend

### Első Használat (5 perc)
1. [QUICK-START.md](QUICK-START.md) - Olvass végig
2. Futtasd a 3 parancsot
3. Nyisd meg böngészőben

### Mélyebb Megértés (15 perc)
1. [README.md](README.md) - Teljes áttekintés
2. [VERSIONING.md](VERSIONING.md) - Verziókezelés
3. [SUMMARY.md](SUMMARY.md) - Projekt kontextus

### Export Készítés (10 perc)
1. [export-from-browser.md](export-from-browser.md) - Összes módszer
2. Válaszd ki a számodra megfelelőt
3. Exportálj!

## 🎯 Use Cases

### "Gyorsan szeretnék HTML-eket látni"
→ [QUICK-START.md](QUICK-START.md#-használat-3-lépésben)

### "Kell PNG a thesis-hez"
→ [export-from-browser.md](export-from-browser.md#módszer-1-automatikus-böngésző-script-egyszerű)

### "Új diagramot szeretnék létrehozni"
→ [README.md](README.md#új-diagram-hozzáadása)

### "Módosítani szeretnék egy diagramot"
→ [QUICK-START.md](QUICK-START.md#-diagram-szerkesztés)

### "Nem értem a verziókezelést"
→ [VERSIONING.md](VERSIONING.md#hogyan-működik)

### "A mermaid-cli nem működik"
→ [export-from-browser.md](export-from-browser.md) - Alternatív módszerek

## 📂 Fájl Rendszer Áttekintés

```
diagrams/
├── 📄 INDEX.md                    # Ez a fájl - Dokumentáció index
├── 📘 QUICK-START.md              # Gyors útmutató (5 perc)
├── 📗 README.md                   # Teljes dokumentáció
├── 📙 VERSIONING.md               # Verziókezelés
├── 📕 export-from-browser.md      # Export módszerek
├── 📔 SUMMARY.md                  # Projekt összefoglaló
├── 📓 CHANGELOG.md                # Változások
│
├── 📁 source/                     # Diagram forrás fájlok
│   ├── phase1_user_onboarding_compact.md
│   ├── phase2_configuration_creation_compact.md
│   └── ... (11 db kompakt diagram)
│
├── 📁 output/                     # Generált kimenetek
│   ├── 📁 html/                   # HTML fájlok
│   ├── 📁 svg/                    # SVG exportok
│   ├── 📁 png/                    # PNG exportok
│   └── index.html                 # Főoldal
│
└── 🔧 Scripts                     # Generálási eszközök
    ├── generate-all.sh            # HTML generálás
    ├── generate-index.py          # Index generálás
    ├── generate-svg-png.sh        # SVG/PNG (npm)
    └── generate-svg-png-docker.sh # SVG/PNG (docker)
```

## 🔍 Keresés a Dokumentációban

### Script használat
→ [QUICK-START.md](QUICK-START.md#-használat-3-lépésben)
→ [README.md](README.md#gyors-használat)

### Verziókezelés
→ [VERSIONING.md](VERSIONING.md)
→ [CHANGELOG.md](CHANGELOG.md)

### Export módszerek
→ [export-from-browser.md](export-from-browser.md)
→ [README.md](README.md#svgpng-export-módszerek)

### Diagram szerkesztés
→ [README.md](README.md#diagram-módosítás)
→ [QUICK-START.md](QUICK-START.md#-diagram-szerkesztés)

### Mermaid szintaxis
→ [README.md](README.md#mermaid-szintaxis-tippek)

### LaTeX integráció
→ [README.md](README.md#latex-integráció)
→ [QUICK-START.md](QUICK-START.md#latex-integrálás)

## 💡 Gyakori Kérdések

**Q: Melyik dokumentumot olvassam először?**
A: [QUICK-START.md](QUICK-START.md) - 5 perc alatt működésre bírod

**Q: Hogyan exportálok PNG-t thesis-hez?**
A: [export-from-browser.md](export-from-browser.md#módszer-1-automatikus-böngésző-script-egyszerű)

**Q: Mi a verziókezelés?**
A: [VERSIONING.md](VERSIONING.md#hogyan-működik)

**Q: A mermaid-cli nem működik**
A: Normális WSL-ben. Lásd: [export-from-browser.md](export-from-browser.md)

**Q: Új diagramot szeretnék**
A: [README.md](README.md#új-diagram-hozzáadása)

**Q: Diagram szintaxis hiba**
A: Teszteld: https://mermaid.live

## 📞 Segítség

Ha elakadtál:
1. Nézd meg a [QUICK-START.md](QUICK-START.md#-troubleshooting) troubleshooting részt
2. Olvasd el a [README.md](README.md#troubleshooting) részletes hibaelhárítást
3. Ellenőrizd a [CHANGELOG.md](CHANGELOG.md)-t legfrissebb változásokért

---

**Start Here:** [QUICK-START.md](QUICK-START.md)
