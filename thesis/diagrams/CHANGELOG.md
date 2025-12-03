# Changelog

## 2025-12-03 - Version 2.0

### ✅ Automatikus Verziókezelés Hozzáadva

**Új Funkció:** Minden script automatikusan verziókezeli a fájlokat

#### Változások

- **generate-all.sh**: HTML fájlok automatikus verziókezelése
  - Első generálás: `filename.html`
  - Második generálás: `filename_v1.html`
  - Harmadik generálás: `filename_v2.html`
  - És így tovább...

- **generate-svg-png.sh**: SVG/PNG verziókezelés npm módszerrel
  - Ugyanaz a verziókezelési logika mint HTML-nél
  - Külön verziókezelés SVG és PNG fájloknak

- **generate-svg-png-docker.sh**: SVG/PNG verziókezelés Docker módszerrel
  - Docker-alapú generálás verziókezeléssel
  - Független verzió számok SVG és PNG-hez

#### Dokumentáció

- **VERSIONING.md**: Részletes verziókezelési útmutató
  - Működési elv
  - Példák
  - Tisztítási módszerek
  - Git integráció

- **README.md**: Frissítve verziókezelési megjegyzéssel
  - Link a VERSIONING.md-re
  - Gyors összefoglaló

#### Előnyök

✅ Biztonságos - Soha nem írja felül a meglévő fájlokat
✅ Verzió történet - Minden generálás megmarad
✅ Összehasonlítás - Könnyű diff megtekintés
✅ Visszaállás - Bármikor visszatérhetsz korábbi verzióhoz
✅ Automatikus - Nincs kézi fájlnév menedzsment

#### Tesztelés

```bash
# Első futtatás
./generate-all.sh
# Kimenet: phase1_user_onboarding_compact.html

# Második futtatás
./generate-all.sh
# Kimenet: phase1_user_onboarding_compact_v1.html
# Eredeti: phase1_user_onboarding_compact.html (változatlan)

# Harmadik futtatás
./generate-all.sh
# Kimenet: phase1_user_onboarding_compact_v2.html
# Korábbiak: VÁLTOZATLANOK
```

---

## 2025-12-03 - Version 1.0

### ✅ Kezdeti Kiadás

#### Kompakt A4-re Optimalizált Diagramok

- 11 diagram újratervezve több oszlopos layouttal
- Subgraph-ok logikai csoportosításhoz
- 13-14px betűméret (olvasható nyomtatva)
- Vízszintes (LR) és függőleges (TB) orientáció

#### Diagramok

1. **phase1_user_onboarding_compact.md**
2. **phase2_configuration_creation_compact.md**
3. **phase3_vm_provisioning_compact.md**
4. **phase4a_docker_deployment_compact.md**
5. **phase4b_nixos_deployment_compact.md**
6. **phase5_traefik_ssl_compact.md**
7. **phase6_ldap_sso_compact.md**
8. **phase7_service_provisioning_compact.md**
9. **phase8_user_access_sso_compact.md**
10. **phase9_operational_monitoring_compact.md**
11. **summary_complete_journey_compact.md**

#### Generálási Rendszer

- **generate-all.sh**: HTML generálás Mermaid CDN-nel
- **generate-svg-png.sh**: SVG/PNG npm módszer
- **generate-svg-png-docker.sh**: SVG/PNG Docker módszer
- **generate-index.py**: Index oldal automatikus generálás

#### Dokumentáció

- **README.md**: Részletes használati útmutató
- **SUMMARY.md**: Projekt összefoglaló

#### Jellemzők

- A4 oldal méret optimalizálás
- Interaktív HTML Mermaid renderinggel
- Böngésző-alapú PDF export
- Magyar nyelvű feliratokkal
- Git verziókezelésbe integrálható

---

## Jövőbeli Tervek

### Version 2.1 (Tervezett)

- [ ] PDF közvetlen export puppeteer-rel
- [ ] Automatikus LaTeX integráció
- [ ] Diagram diff tool (verzió összehasonlítás)
- [ ] CI/CD GitHub Actions integráció

### Version 3.0 (Ötletek)

- [ ] Interaktív diagram szerkesztő
- [ ] Real-time preview WebSocket-tel
- [ ] Theme váltás (light/dark mode)
- [ ] Export több formátumba (PPTX, DOCX)

---

**Karbantartó:** BME-VIK Diplomaterv
**Licensz:** Belső használat
**Frissítve:** 2025-12-03
