# Setup — så får du upp repot på GitHub

Det här repot ligger som en mapp på din dator (`worktime-tracker-repo/`). För att HACS ska kunna installera det måste det ligga på GitHub. Allt är redan konfigurerat för användarnamnet `ottoherdy`.

## 1. Skapa ett tomt repo på GitHub

1. Gå till [github.com/new](https://github.com/new)
2. **Repository name:** `worktime-tracker`
3. Lämna allt annat tomt (ingen README, ingen .gitignore, ingen LICENSE — vi har redan)
4. Klicka **Create repository**

## 2. Initiera git lokalt och pusha

Öppna terminalen, gå till mappen där detta repo ligger:

```bash
cd /sökväg/till/worktime-tracker-repo

git init -b main
git add .
git commit -m "Initial commit: Worktime Tracker integration"
git remote add origin https://github.com/ottoherdy/worktime-tracker.git
git push -u origin main
```

## 3. Tagga första releasen (krävs av HACS)

```bash
git tag v1.0.0
git push --tags
```

HACS plockar automatiskt upp den senaste tag:en som "version" i manifestet.

## 4. Lägg till repot i HACS

I Home Assistant:

1. **HACS → Integrations → ⋮ → Custom repositories**
2. URL: `https://github.com/ottoherdy/worktime-tracker`
3. Kategori: **Integration**
4. **Add**

Sök upp **Worktime Tracker** i listan, **Download**, starta om HA.

## (Valfritt) Lägg till i HACS officiella default-listan

Om du vill att andra ska kunna hitta det utan "Custom repositories"-steget måste du skicka in en PR till [hacs/default](https://github.com/hacs/default). Inte nödvändigt för personligt bruk.
