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

### macOS ancien (alternative validée)

Si Docker Desktop est incompatible avec votre version macOS, utiliser `Rancher Desktop`:

```zsh
brew install --cask rancher
open '/Applications/Rancher Desktop.app'
```

Puis utiliser le socket Docker Rancher:

```zsh
export DOCKER_HOST=unix:///Users/$USER/.rd/docker.sock
docker info
```

## Démarrage rapide

### Sécurité: configurer les secrets en local (recommandé)

Copier les exemples de configuration, puis renseigner vos identifiants **en local uniquement**:

```zsh
cd /Users/mac/Desktop/Master1/semestre2/ProjectDs4h/SmartMonitoring
cp .env.example .env
cp web_interface/public/config.example.js web_interface/public/config.local.js
```

- `.env` : secrets backend / Docker / Python (`MYSQL_*`, `DB_*`, `MQTT_*`)
- `config.local.js` : identifiants MQTT du dashboard navigateur + clé optionnelle `adminAccessKey`

Ces deux fichiers ne doivent pas être versionnés.

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

### Smoke test E2E (recommandé)

Ce test valide la chaîne complète **MQTT → MySQL → API MQTT** avec un topic temporaire.

```zsh
cd /Users/mac/Desktop/Master1/semestre2/ProjectDs4h/SmartMonitoring/bridge
python3 e2e_smoke_test.py
```

Résultat attendu: `🎉 E2E OK: MQTT -> MySQL -> API MQTT validé`

## Démo

La checklist de passage en revue est disponible dans [`DEMO_CHECKLIST.md`](./DEMO_CHECKLIST.md).

## Raspberry Pi + Tailscale (Étudiant 4)

Pour couvrir l'exigence de configuration Raspberry sous Tailscale, un script dédié est fourni:

```zsh
cd /Users/mac/Desktop/Master1/semestre2/ProjectDs4h/SmartMonitoring
chmod +x ./scripts/setup_raspberry_tailscale.sh
TS_AUTHKEY="tskey-xxxx" TS_HOSTNAME="fablab-rpi" ./scripts/setup_raspberry_tailscale.sh
```

Variables optionnelles:
- `TS_ACCEPT_ROUTES` (défaut: `true`)
- `TS_ADVERTISE_TAGS` (ex: `tag:fablab`)

Après exécution, vérifier que le Raspberry apparaît bien dans votre tailnet avec une IP Tailscale.

### Démarrage automatique au boot Raspberry (systemd)

Pour lancer automatiquement `main.py` et `api_mqtt.py` au démarrage du Raspberry:

```zsh
cd /Users/mac/Desktop/Master1/semestre2/ProjectDs4h/SmartMonitoring
chmod +x ./scripts/install_raspberry_services.sh
./scripts/install_raspberry_services.sh
```

Le script:
- installe les dépendances Python (si nécessaire),
- crée `/etc/smartmonitoring.env` (à compléter),
- installe et active deux services `systemd`:
	- `smartmonitoring-main.service`
	- `smartmonitoring-api.service`

Vérification:

```zsh
sudo systemctl status smartmonitoring-main.service --no-pager
sudo systemctl status smartmonitoring-api.service --no-pager
```

### Healthcheck Raspberry (1 commande)

Pour vérifier rapidement l'état global (Tailscale + services + MQTT + MySQL):

```zsh
cd /Users/mac/Desktop/Master1/semestre2/ProjectDs4h/SmartMonitoring
chmod +x ./scripts/healthcheck_raspberry.sh
./scripts/healthcheck_raspberry.sh
```

Le script retourne un code d'erreur (`exit 1`) si un check échoue.