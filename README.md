# SmartMonitoring

Projet M1 — plateforme de monitoring FabLab (IoT + visualisation temps réel).

## Objectif

Ce dépôt implémente une chaîne complète de collecte et d'affichage des données capteurs :

`Capteurs MQTT` → `bridge/main.py` → `MySQL` → `bridge/api_mqtt.py` → `WEB/REPONSE` → `Dashboard web`

## Composants principaux

- `bridge/main.py` : ingestion MQTT multi-topics et persistance MySQL.
- `bridge/api_mqtt.py` : API MQTT de requête/réponse (`WEB/REQUETE` → `WEB/REPONSE`).
- `web_interface/public/index.html` : interface de monitoring (KPI + graphe qualité d’air).
- `scripts/start_local_demo.sh` : démarrage local rapide de la démo.

## Prérequis

- macOS (ou Linux) avec Docker/Colima opérationnel
- Python 3
- Accès au broker MQTT universitaire (`mqtt.univ-cotedazur.fr`)

## Démarrage rapide

```zsh
cd /Users/mac/Desktop/Master1/semestre2/ProjectDs4h/SmartMonitoring
chmod +x ./scripts/start_local_demo.sh
./scripts/start_local_demo.sh
```

Le script lance les services Python nécessaires et le dashboard local sur `http://localhost:8080`.

## Démarrage manuel

### 1) Infrastructure Docker

```zsh
cd /Users/mac/Desktop/Master1/semestre2/ProjectDs4h/SmartMonitoring
docker compose up -d
docker compose ps
```

### 2) Ingestion MQTT vers MySQL

```zsh
cd /Users/mac/Desktop/Master1/semestre2/ProjectDs4h/SmartMonitoring/bridge
python3 -m pip install -r requirements.txt
python3 main.py
```

### 3) API MQTT pour l’interface web

```zsh
cd /Users/mac/Desktop/Master1/semestre2/ProjectDs4h/SmartMonitoring/bridge
python3 api_mqtt.py
```

### 4) Interface web

```zsh
cd /Users/mac/Desktop/Master1/semestre2/ProjectDs4h/SmartMonitoring/web_interface/public
python3 -m http.server 8080
```

Ouvrir ensuite `http://localhost:8080`.

## Vérification fonctionnelle

- `main.py` reçoit des messages sur `FABLAB_21_22/#` et écrit en base.
- `api_mqtt.py` traite les requêtes `WEB/REQUETE` et publie sur `WEB/REPONSE`.
- Le dashboard affiche les KPI et le graphe IAQ après synchronisation (`Sync Data`).

## Démo

La checklist de passage en revue est disponible dans [`DEMO_CHECKLIST.md`](./DEMO_CHECKLIST.md).