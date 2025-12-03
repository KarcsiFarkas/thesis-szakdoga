# Böngésző-alapú Export Útmutató (Ajánlott)

A mermaid-cli gyakran problémás WSL/headless környezetben. A legmegbízhatóbb módszer a **böngésző-alapú export**.

## Módszer 1: Automatikus Böngésző Script (Egyszerű)

### 1. Nyisd meg a HTML fájlt

```bash
firefox output/html/phase1_user_onboarding_compact.html
# vagy
google-chrome output/html/phase1_user_onboarding_compact.html
```

### 2. Használd a Böngésző Developer Console-t

Nyomd meg **F12** → Console tab

### 3. SVG Export (Másold be a Console-ba)

```javascript
// SVG mentés
(function() {
  const svg = document.querySelector('.mermaid svg');
  if (!svg) {
    console.error('Nincs SVG elem a lapon');
    return;
  }

  // Clone és tisztítás
  const clone = svg.cloneNode(true);
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');

  // Serialize
  const svgData = new XMLSerializer().serializeToString(clone);
  const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });

  // Download
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = document.title.replace(/[^a-z0-9]/gi, '_').toLowerCase() + '.svg';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);

  console.log('✓ SVG letöltve:', link.download);
})();
```

### 4. PNG Export (Másold be a Console-ba)

```javascript
// PNG mentés (Canvas alapú)
(function() {
  const svg = document.querySelector('.mermaid svg');
  if (!svg) {
    console.error('Nincs SVG elem a lapon');
    return;
  }

  const svgData = new XMLSerializer().serializeToString(svg);
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');

  const img = new Image();
  img.onload = function() {
    canvas.width = img.width * 2;  // 2x méret jobb minőséghez
    canvas.height = img.height * 2;
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(function(blob) {
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = document.title.replace(/[^a-z0-9]/gi, '_').toLowerCase() + '.png';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      console.log('✓ PNG letöltve:', link.download);
    });
  };

  img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgData)));
})();
```

## Módszer 2: Mermaid Live Editor (Online)

### 1. Másold ki a Mermaid kódot

```bash
# A source fájlból (csak a mermaid blokk)
cat source/phase1_user_onboarding_compact.md
```

### 2. Mermaid Live Editor

1. Nyisd meg: https://mermaid.live
2. Töröld a példa kódot
3. Illeszd be a saját Mermaid kódodat
4. Kattints **Actions** → **PNG/SVG/PDF**
5. Letöltés automatikus

### 3. Batch Export

Ha sok diagram van:
1. Nyisd meg minden HTML-t külön tab-ban
2. Futtasd a console script-et mindegyiken
3. Vagy használj Mermaid Live-ot egyenként

## Módszer 3: PDF Export Nyomtatással

### Chrome/Chromium/Edge

```bash
# Parancssorból
google-chrome --headless --print-to-pdf=phase1.pdf output/html/phase1_user_onboarding_compact.html

# Vagy böngészőből
# 1. Nyisd meg a HTML-t
# 2. Ctrl+P (Print)
# 3. Destination: Save as PDF
# 4. Paper size: A4
# 5. Margins: Default
# 6. Save
```

### Firefox

```bash
# Böngészőből:
# 1. Nyisd meg a HTML-t
# 2. Ctrl+P (Print)
# 3. Destination: Save to PDF
# 4. Landscape/Portrait szerint
# 5. Save
```

## Módszer 4: Screenshot (Gyors)

### Linux (GNOME)

```bash
# Teljes ablak screenshot
gnome-screenshot -w

# Terület kijelölés
gnome-screenshot -a
```

### Firefox Screenshot Tool

```bash
# Böngészőben:
# 1. Shift+Ctrl+S (Firefox Screenshot)
# 2. Save full page / Save visible
# 3. Automatikus download
```

## Batch Script (Minden Diagramhoz)

Hozz létre egy bookmarklet-et a böngészőben:

### SVG Bookmarklet

```javascript
javascript:(function(){const svg=document.querySelector('.mermaid svg');if(!svg){alert('Nincs SVG');return;}const clone=svg.cloneNode(true);clone.setAttribute('xmlns','http://www.w3.org/2000/svg');const svgData=new XMLSerializer().serializeToString(clone);const blob=new Blob([svgData],{type:'image/svg+xml;charset=utf-8'});const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download=document.title.replace(/[^a-z0-9]/gi,'_').toLowerCase()+'.svg';document.body.appendChild(link);link.click();document.body.removeChild(link);URL.revokeObjectURL(url);})();
```

### PNG Bookmarklet

```javascript
javascript:(function(){const svg=document.querySelector('.mermaid svg');if(!svg){alert('Nincs SVG');return;}const svgData=new XMLSerializer().serializeToString(svg);const canvas=document.createElement('canvas');const ctx=canvas.getContext('2d');const img=new Image();img.onload=function(){canvas.width=img.width*2;canvas.height=img.height*2;ctx.fillStyle='white';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(img,0,0,canvas.width,canvas.height);canvas.toBlob(function(blob){const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download=document.title.replace(/[^a-z0-9]/gi,'_').toLowerCase()+'.png';document.body.appendChild(link);link.click();document.body.removeChild(link);URL.revokeObjectURL(url);});};img.src='data:image/svg+xml;base64,'+btoa(unescape(encodeURIComponent(svgData)));})();
```

### Bookmarklet Használata

1. Hozz létre új bookmarkot a böngésző bookmarks bar-on
2. Név: "Export SVG" vagy "Export PNG"
3. URL: Illeszd be a fenti JavaScript kódot
4. Nyisd meg bármelyik HTML diagramot
5. Kattints a bookmarkra → Automatikus letöltés

## Összehasonlítás

| Módszer | Előny | Hátrány | Ajánlott? |
|---------|-------|---------|----------|
| **Console Script** | Pontos, nagy felbontás | Manuális minden fájlhoz | ✅ Igen |
| **Mermaid Live** | Online, egyszerű | Copy-paste minden kódhoz | ✅ Igen |
| **PDF Print** | Universal, támogatott | Nem szerkeszthető | ⚠️ Backup |
| **Screenshot** | Gyors | Alacsony felbontás | ❌ Nem thesis-hez |
| **mermaid-cli** | Automatikus | WSL-ben nem működik | ❌ Nem |
| **Bookmarklet** | Egy kattintás | Böngésző setup kell | ✅ Batch export-hoz |

## Ajánlás Thesis Integrációhoz

### LaTeX PNG Használathoz

1. **Módszer 1**: Console Script PNG export
   - Nyisd meg: `output/html/phase1_user_onboarding_compact.html`
   - Console: Futtasd a PNG export scriptet
   - Mentés: `output/png/phase1_user_onboarding_compact.png`

2. **Módszer 2**: Mermaid Live
   - Másold a kódot `source/phase1_user_onboarding_compact.md`-ből
   - https://mermaid.live → Paste → Actions → PNG
   - Mentés: `output/png/`

### LaTeX SVG Használathoz

SVG LaTeX-ben:
```latex
\usepackage{svg}
\includesvg{diagrams/output/svg/phase1_user_onboarding_compact}
```

Vagy konvertálás PNG-re:
```bash
inkscape --export-type=png --export-dpi=300 \
  output/svg/phase1.svg \
  -o output/png/phase1.png
```

## Hibakeresés

### SVG üres vagy hibás

**OK:** SVG még nem renderelődött

**Megoldás:**
```javascript
// Várj a Mermaid render-re
setTimeout(function() {
  // Futtasd az export scriptet
}, 2000);  // 2 másodperc várakozás
```

### PNG fehér oldal

**OK:** Canvas CORS policy

**Megoldás:** Használd a Local file:// protokollt, NEM http://

### Betűméret túl kicsi PNG-ben

**Megoldás:** Növeld a canvas méretét
```javascript
canvas.width = img.width * 3;  // 3x helyett 2x
canvas.height = img.height * 3;
```

---

**Összefoglalás:** A böngésző-alapú export a legmegbízhatóbb módszer. Használd a Console scripteket vagy a Mermaid Live Editor-t professzionális minőségű SVG/PNG exporthoz.
