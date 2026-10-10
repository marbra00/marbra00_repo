# Kodi Repository: marbra00_repo

## Deutsch

Unabhängig gepflegtes Repository von **marbra00** für Kodi-Addons und Updates. Die Sammlung kann mehrere Addons aus verschiedenen Quellcode-Projekten anbieten.

- Name in Kodi: `marbra00_repo`
- Repository-Kennung: `repository.marbra00_repo`
- Repository-Version: `1.0.0`
- [Downloadseite](https://marbra00.github.io/marbra00_repo/)
- [Installationsanleitung](repository.marbra00_repo/README.md)

Dieses Repository ist inoffiziell und nicht mit Team Kodi verbunden. Der Repository-Code steht unter [GPL-3.0-or-later](LICENSE). Aufgenommene Addons behalten ihre jeweiligen Lizenzen und Autorenangaben.

### Verfügbare Addons

| Addon | Version | Quellcode |
| --- | --- | --- |
| Dailymotion – Unofficial | 1.0.0 | [Dailymotion-Unofficial](https://github.com/marbra00/Dailymotion-Unofficial/tree/v1.0.0) |

### Pflege des Repositorys

Die Quelldateien des Repository-Addons liegen in `repository.marbra00_repo/`. Die Dateien für GitHub Pages liegen in `docs/`.

Nach einer freigegebenen Änderung die Paketliste und Prüfsummen mit Python 3.9 oder neuer neu erstellen:

```sh
python tools/build_repository.py
```

Zusätzliche Addons werden ausdrücklich über `packages.json` aufgenommen. Jeder Eintrag nennt den Pfad einer vorhandenen ZIP-Datei innerhalb von `docs/`, ihre SHA-256-Prüfsumme und den Link zum zugehörigen Quellcode. Das Werkzeug prüft und veröffentlicht ausschließlich diese ausgewählten Pakete in der Paketliste; es lädt nichts aus dem Internet und verändert keine anderen Projekte.

Eine bereits gepackte Version wird nicht mit verändertem Inhalt überschrieben. Bei Änderungen am Repository-Addon zuerst dessen Versionsnummer und Änderungsprotokoll aktualisieren. Auch bei aufgenommenen Addons benötigt geänderter Inhalt eine neue Versionsnummer.

GitHub Pages wird aus dem Ordner `/docs` des Hauptbranches veröffentlicht. Das Hochladen und Aktivieren von GitHub Pages sind separate Schritte.

Die Prüfungen für Paketstruktur, Prüfsummen, wiederholbare Erstellung und ungültige Pakete lassen sich mit `python -m unittest discover -s tests` ausführen.

## English

*The following text was automatically translated from the German original.*

An independently maintained repository by **marbra00** for Kodi addons and updates. The collection can provide multiple addons from different source code projects.

- Name in Kodi: `marbra00_repo`
- Repository ID: `repository.marbra00_repo`
- Repository version: `1.0.0`
- [Download page](https://marbra00.github.io/marbra00_repo/)
- [Installation guide](repository.marbra00_repo/README.md)

This repository is unofficial and is not affiliated with Team Kodi. The repository code is licensed under [GPL-3.0-or-later](LICENSE). Included addons retain their own licences and author credits.

### Available addons

| Addon | Version | Source code |
| --- | --- | --- |
| Dailymotion – Unofficial | 1.0.0 | [Dailymotion-Unofficial](https://github.com/marbra00/Dailymotion-Unofficial/tree/v1.0.0) |

### Maintaining the repository

The repository addon's source files are in `repository.marbra00_repo/`. GitHub Pages files are in `docs/`.

After an approved change, rebuild the package list and checksums with Python 3.9 or newer:

```sh
python tools/build_repository.py
```

Additional addons are explicitly included through `packages.json`. Each entry specifies the path of an existing ZIP file inside `docs/`, its SHA-256 checksum and the corresponding source code link. The tool validates and lists only these selected packages; it does not download anything or modify other projects.

An existing packaged version is never overwritten with different contents. Before changing the repository addon, update its version and changelog. Changes to included addons also require a new version number.

GitHub Pages is published from `/docs` on the main branch. Uploading the project and enabling GitHub Pages are separate steps.

Run `python -m unittest discover -s tests` to check package structure, checksums, reproducible builds and invalid packages.
