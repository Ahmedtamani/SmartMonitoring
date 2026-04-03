# Checklist de démo — Étudiant 4 (Données & Serveur)

## 1) Préparation (2 minutes)

- [ ] Docker actif
- [ ] Conteneurs `iot_mysql` et `iot_mosquitto` en état `Up`
- [ ] `main.py` en écoute MQTT
- [ ] `api_mqtt.py` connecté au broker universitaire
- [ ] Dashboard accessible sur `http://localhost:8080`

## 2) Lancement recommandé

```zsh
cd /Users/mac/Desktop/Master1/semestre2/ProjectDs4h/SmartMonitoring
./scripts/start_local_demo.sh
```

Si le script n’est pas exécutable :

```zsh
cd /Users/mac/Desktop/Master1/semestre2/ProjectDs4h/SmartMonitoring
chmod +x ./scripts/start_local_demo.sh
./scripts/start_local_demo.sh
```

## 3) Démonstration attendue

### Terminal `main.py`

- Réception des messages capteurs (`FABLAB_21_22/#`)
- Confirmation d’écriture en base MySQL

### Terminal `api_mqtt.py`

- Réception des requêtes `WEB/REQUETE`
- Publication des réponses `WEB/REPONSE`

### Dashboard web

- Cliquer sur `Sync Data`
- Vérifier le chargement du graphe IAQ
- Vérifier l’affichage des KPI (température, humidité, CO₂/qualité d’air, radar)

## 4) Éléments de preuve (captures)

- [ ] Résultat `docker compose ps`
- [ ] Terminal `main.py` (réception + insertion)
- [ ] Terminal `api_mqtt.py` (requête + réponse)
- [ ] Dashboard avec données visibles

## 5) Validation sur site (université)

- [ ] Raspberry connecté via Tailscale
- [ ] Bridge exécuté sur Raspberry (pas uniquement en local Mac)
- [ ] Vérification des topics réellement publiés par l’équipe
- [ ] Vérification de la cohérence des timestamps et des valeurs en conditions réelles
