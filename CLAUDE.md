# brickpi – instrukcje dla agentów

Publiczne repo (MIT): sterownik Raspberry Pi 3/4/5 dla LEGO Mindstorms, klon BrickPi3 (DexterInd, MIT).

## Zasady pracy

- Komunikacja z właścicielem po polsku. Pliki publiczne (README, `docs/`, CHANGELOG) po angielsku.
- Branch zawsze z `develop`, PR do `develop`. Nigdy push na `develop`/`main`. Commity jako `janr-bot`.
- Tytuł PR/commita w [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `docs:`, `ci:`, `chore:`, zakres opcjonalnie: `feat(hardware): …`).
- Każdy PR: wpis w `CHANGELOG.md` (sekcja `[Unreleased]`, Keep a Changelog), wersje wg SemVer.
- Małe pliki, proste rozwiązania, bez zbędnych zależności. Powtarzalne czynności → skrypty w `scripts/`.
- Przed PR uruchom `scripts/check-repo.sh` (zakazane pliki, rozmiar, słowa kluczowe sekretów).

## Bezpieczeństwo i licencje (twarde)

- Repo jest publiczne: żadnych danych logowania, haseł Wi-Fi, kluczy API, danych osobowych.
- Nie dodawaj: tekstu pracy dyplomowej, prezentacji, recenzji (prywatne), materiałów kursów,
  projektów o obcej/niejasnej licencji (np. bricktronics), modeli 3D producentów bez licencji.
- Nowy kod/projekt oparty na DexterInd – zachowaj atrybucję (patrz `NOTICE`).
- Pliki > 10 MB nie trafiają do repo (STL/STEP generujemy z źródeł CAD).

## KiCad (`hardware/`)

- KiCad 8. Commituj tylko `*.kicad_pro`, `*.kicad_sch`, `*.kicad_pcb`, `*.kicad_dru` i biblioteki
  projektu; bez `*.kicad_prl`, `fp-info-cache`, backupów i gerberów (gerbery robi CI).
- Żadnych ścieżek absolutnych (`C:/Users/...`) – używaj `${KIPRJMOD}` albo zmiennych KiCad.
- Zmiany na płytce opisuj w `hardware/README.md` (historia rewizji).

## Mapa

- Protokół SPI: `docs/PROTOCOL.md`; zasilanie: `docs/POWER.md`.
- Plan katalogów: `README.md` w każdym katalogu.
