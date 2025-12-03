# Automatikus Verziókezelés

Az összes generálási script automatikus verziókezelést használ, hogy megelőzze a létező fájlok felülírását.

## Hogyan Működik

### Első Generálás

```bash
./generate-all.sh
```

**Létrehozott fájlok:**
```
output/html/phase1_user_onboarding_compact.html
output/html/phase2_configuration_creation_compact.html
...
```

### Második Generálás (verziókezelés)

```bash
./generate-all.sh  # Újra futtatás
```

**Létrehozott fájlok:**
```
output/html/phase1_user_onboarding_compact_v1.html
output/html/phase2_configuration_creation_compact_v1.html
...
```

**Meglévő fájlok VÁLTOZATLANOK:**
```
output/html/phase1_user_onboarding_compact.html  ← NEM módosult
output/html/phase2_configuration_creation_compact.html  ← NEM módosult
```

### Harmadik Generálás

```bash
./generate-all.sh  # Még egyszer
```

**Új verzió:**
```
output/html/phase1_user_onboarding_compact_v2.html
output/html/phase2_configuration_creation_compact_v2.html
...
```

## Verzió Számozás Logika

```bash
# Ha fájl NEM létezik
filename.html  # Eredeti név

# Ha filename.html LÉTEZIK
filename_v1.html  # Első verzió

# Ha filename.html ÉS filename_v1.html LÉTEZIK
filename_v2.html  # Második verzió

# És így tovább...
filename_v3.html
filename_v4.html
filename_v10.html
```

## Minden Formátumra Érvényes

### HTML Generálás
```bash
./generate-all.sh
# Kimenet: phase1_user_onboarding_compact.html
# Második futtatás: phase1_user_onboarding_compact_v1.html
```

### SVG Generálás
```bash
./generate-svg-png.sh  # vagy generate-svg-png-docker.sh
# Kimenet: phase1_user_onboarding_compact.svg
# Második futtatás: phase1_user_onboarding_compact_v1.svg
```

### PNG Generálás
```bash
./generate-svg-png.sh  # vagy generate-svg-png-docker.sh
# Kimenet: phase1_user_onboarding_compact.png
# Második futtatás: phase1_user_onboarding_compact_v1.png
```

## Példa Kimenet

```
output/
├── html/
│   ├── phase1_user_onboarding_compact.html       # Eredeti
│   ├── phase1_user_onboarding_compact_v1.html    # 1. verzió
│   ├── phase1_user_onboarding_compact_v2.html    # 2. verzió
│   └── ...
├── svg/
│   ├── phase1_user_onboarding_compact.svg
│   ├── phase1_user_onboarding_compact_v1.svg
│   └── ...
└── png/
    ├── phase1_user_onboarding_compact.png
    ├── phase1_user_onboarding_compact_v1.png
    └── ...
```

## Előnyök

✅ **Biztonságos** - Soha nem írja felül a meglévő fájlokat
✅ **Verzió történet** - Minden generálás megmarad
✅ **Összehasonlítás** - Könnyű a verziók közötti különbségek megtekintése
✅ **Visszaállás** - Bármikor visszatérhetsz korábbi verzióhoz
✅ **Automatikus** - Nincs szükség kézi fájlnév menedzsmentre

## Megjegyzés: Index.html Generálás

Az `index.html` **NEM** használ verziókezelést, mert mindig újragenerálódik az aktuális fájlok alapján:

```bash
python3 generate-index.py
# Mindig újraírja: output/index.html
```

Az index automatikusan detektálja és listázza az ÖSSZES verzióját minden diagramnak.

## Tisztítás (Opcionális)

Ha törölni szeretnéd a régi verziókat:

```bash
# Csak a verziókezelt fájlok törlése
rm output/html/*_v*.html
rm output/svg/*_v*.svg
rm output/png/*_v*.png

# Vagy minden HTML törlése és újragenerálás
rm -rf output/html/*
./generate-all.sh
python3 generate-index.py
```

## Git Integráció

### Verziókezelt Fájlok Commitolása

```bash
# Csak az eredeti fájlok commitolása
git add output/html/phase*.html
git add '!output/html/*_v*.html'  # Verziókat kihagyja

# Vagy minden verzió commitolása
git add output/html/
```

### .gitignore Beállítás

Ha NEM akarod commitolni a verziókat:

```gitignore
# .gitignore
output/html/*_v*.html
output/svg/*_v*.svg
output/png/*_v*.png
```

Csak az eredeti fájlokat commitolja:

```gitignore
# .gitignore - CSAK verziók kizárása
output/**/*_v*.*
```

## Tesztelés

Próbáld ki a verziókezelést:

```bash
# 1. Első generálás
./generate-all.sh
ls -1 output/html/phase1*

# 2. Második generálás
./generate-all.sh
ls -1 output/html/phase1*

# Kimenet:
# phase1_user_onboarding_compact.html
# phase1_user_onboarding_compact_v1.html

# 3. Harmadik generálás
./generate-all.sh
ls -1 output/html/phase1*

# Kimenet:
# phase1_user_onboarding_compact.html
# phase1_user_onboarding_compact_v1.html
# phase1_user_onboarding_compact_v2.html
```

## Troubleshooting

### Verzió számok nem inkrementálódnak

**Ellenőrzés:**
```bash
ls -la output/html/phase1*
# Győződj meg róla, hogy a fájlok léteznek
```

**Megoldás:**
```bash
# Futtasd újra
./generate-all.sh
```

### Túl sok verzió

```bash
# Régi verziók törlése (v10 felett)
find output/html -name '*_v[1-9].html' -delete
find output/html -name '*_v1[0-9].html' -delete
```

### Verziókezelés letiltása

Ha SZERETNÉD felülírni a fájlokat:

```bash
# Töröld a verziókezelési logikát a scriptből
# Vagy egyszerűen töröld a célkönyvtárat futtatás előtt
rm -rf output/html/
./generate-all.sh
```

---

**Összefoglaló:** A verziókezelés automatikusan védi a meglévő fájlokat, és minden új generálás egy új verziószámot kap (_v1, _v2, stb.).
