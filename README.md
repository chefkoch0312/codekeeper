# CodeKeeper
> 🧠 Lokales Backup- & Deployment-Tool für Entwicklerprojekte

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey)

---

Ein schlankes, lokal ausführbares Backup- und Deployment-Tool für Entwicklungsprojekte – entwickelt mit **Python**, **Tkinter** und einer **SQLite-Datenbank** zur Verwaltung projektbezogener Informationen. Ziel ist eine einfache, transparente Sicherung und Übertragung von Quellcode in definierte Backup- oder Runtime-Verzeichnisse.

## ✨ Funktionen

- 🗂️ Projektverwaltung mit Quell-, Backup- und optionalem Runtime-Pfad
- 🕓 Versionierte Backups mit Zeitstempel (nach Datum/Uhrzeit)
- 🚀 Manuelles Deployment in Laufzeitumgebungen (z. B. XAMPP)
- 🧹 Ausschlussmuster für `.git`, `__pycache__` etc.
- 🛡️ Pfadvalidierung gegen riskante Systemverzeichnisse
- 📊 Fortschrittsanzeige und Statusprotokoll im Hauptfenster

## 📁 Projektstruktur (vereinfacht)

```
codekeeper/
  main.py              # GUI, Engine und Projektsteuerung
  codekeeper.db        # SQLite-Datenbank für Projekte
  config/
    templates/         # ggf. Vorlagen für zukünftige Erweiterungen
```

## 🔧 Setup

1. Repository klonen:

   ```bash
   git clone https://github.com/chefkoch0312/codekeeper.git
   ```

2. Abhängigkeiten sicherstellen (nur Standardbibliotheken benötigt):

   ```bash
   python main.py
   ```

## 🖋️ Projektpflege

Über die grafische Oberfläche lassen sich Projekte hinzufügen, bearbeiten oder löschen. Jedes Projekt speichert:

- ✅ Quellpfad (z. B. `C:/Users/user/dev/projektX`)
- ✅ Backup-Ziel (z. B. `Z:/backup/projektX`)
- ✅ Optional: Laufzeitumgebung (z. B. `C:/xampp/htdocs/projektX`)

Ein Klick auf **„Backup erstellen“** erzeugt eine vollständige, versionierte Kopie. Der Button **„In Runtime kopieren“** überträgt den aktuellen Stand (nach Rückfrage) in das Laufzeitverzeichnis.

## 🧠 Funktionsweise

Das Herzstück bildet die Klasse `BackupEngine`. Sie durchläuft rekursiv den Quellordner, ignoriert per Muster definierte Ausschlüsse und kopiert die restlichen Dateien an den Zielort. Pfade wie `C:/Windows` oder Root-Verzeichnisse werden geblockt.

Die Klasse `ProjectManager` verwaltet alle Projekte in der SQLite-Datenbank. Die GUI-Komponente `CodeKeeperGUI` verbindet alle Logikbestandteile zu einer übersichtlichen Bedienoberfläche.

## ⚠️ Hinweis

CodeKeeper ist ein lokales Werkzeug – es läuft vollständig ohne Internetverbindung. Die Datenbank befindet sich im Projektverzeichnis und speichert ausschließlich Pfadinformationen und Metaangaben. Es erfolgt **keine automatische Synchronisierung oder Cloud-Nutzung**.

---

## 🛠️ Erweiterungsideen

- 🔄 Automatische Backup-Intervalle (per Task-Scheduler)
- ☁️ Unterstützung für Netzlaufwerke & Cloud-Ziele
- 🧪 Unit Tests für BackupEngine und PathValidator
- 🗃️ Export/Import von Projektprofilen (z. B. als JSON)

Entwickelt & gepflegt von [Kai Dombrowski](https://kado-ber.de/)
