# Rapport de Synthèse de Mi-Parcours (Commun) : Projet SmartMonitoring

**Informations sur la réunion (Mid-Term Meeting) :**
* **Date de la réunion :** [Date, ex: 15 Avril 2026]
* **Lieu :** [Lieu, ex: Salle de réunion / Visioconférence]
* **Superviseur du projet :** [Nom du Superviseur]  
* **Étudiants de l'équipe :** [Nom du Collègue 1], [Nom du Collègue 2], [Nom du Collègue 3], [Votre Nom]
* **Validation / Revue du superviseur :** [ ] Fait le : _______________

---

## ➔ PARTIE 1 : Contribution de [Nom du Collègue 1] - [Son Rôle : ex. Capteurs Hardware / C++]

### 1.1 Contexte et État de l'art
*(Demandez à votre collègue de coller sa partie 1 ici)*

### 1.2 Description des réalisations de l'étudiant durant la première partie
*(Demandez à votre collègue de coller sa partie 2 ici)*

### 1.3 Problèmes rencontrés et solutions mises en œuvre
*(Demandez à votre collègue de coller sa partie 3 ici)*

### 1.4 Description du travail restant (2ème partie) et échéancier
*(Demandez à votre collègue de coller sa partie 4 ici)*

---

<br>

## ➔ PARTIE 2 : Contribution de [Nom du Collègue 2] - [Son Rôle : ex. Application Mobile]

### 2.1 Contexte et État de l'art
*(Demandez à votre collègue de coller sa partie 1 ici)*

### 2.2 Description des réalisations de l'étudiant durant la première partie
*(Demandez à votre collègue de coller sa partie 2 ici)*

### 2.3 Problèmes rencontrés et solutions mises en œuvre
*(Demandez à votre collègue de coller sa partie 3 ici)*

### 2.4 Description du travail restant (2ème partie) et échéancier
*(Demandez à votre collègue de coller sa partie 4 ici)*

---

<br>

## ➔ PARTIE 3 : Contribution de [Nom du Collègue 3] - [Son Rôle : ex. UX/UI Design]

### 3.1 Contexte et État de l'art
*(Demandez à votre collègue de coller sa partie 1 ici)*

### 3.2 Description des réalisations de l'étudiant durant la première partie
*(Demandez à votre collègue de coller sa partie 2 ici)*

### 3.3 Problèmes rencontrés et solutions mises en œuvre
*(Demandez à votre collègue de coller sa partie 3 ici)*

### 3.4 Description du travail restant (2ème partie) et échéancier
*(Demandez à votre collègue de coller sa partie 4 ici)*

---

<br>

## ➔ PARTIE 4 : Contribution de [Votre Nom] - [Backend, MQTT & Base de données]

### 4.1 Contexte et État de l'art du sujet de recherche en cours

Le projet **SmartMonitoring** s'inscrit dans le domaine de l'Internet des Objets (IoT) et de la supervision d'environnements intelligents (comme un FabLab). L'objectif de la recherche est de développer et d'évaluer une architecture logicielle complète capable de collecter, traiter, stocker et afficher en temps réel des données issues de capteurs. 

Actuellement, les solutions de monitoring nécessitent souvent des architectures lourdes. Notre approche se concentre sur une solution légère et modulable basée sur des technologies open-source standards :
- **MQTT :** Un protocole de messagerie léger idéal pour l'IoT (pour la transmission des données des capteurs).
- **Python :** Utilisé comme "pont" (bridge) pour connecter le flux MQTT à une base de données, permettant un traitement rapide des informations.
- **MySQL :** Pour le stockage persistant et sécurisé des données historiques.
- **Interface Web (HTML/JS) :** Pour la visualisation des données en temps réel via un tableau de bord.
- **Docker :** Pour conteneuriser l'application et garantir sa portabilité.

### 4.2 Description des réalisations de l'étudiant durant la première partie du projet

Au cours de cette première moitié du projet de recherche, les fondations techniques de l'architecture ont été construites et validées :

1. **Mise en place de la communication MQTT :** 
   Configuration d'un client capable de s'abonner aux "topics" des capteurs et de recevoir les données en temps réel.
2. **Développement du "Bridge" Python (`main.py`, `api_mqtt.py`) :**
   Création de scripts Python qui interceptent les messages MQTT, formatent les données, et les enregistrent de manière structurée dans la base de données MySQL.
3. **Création de l'Interface Web (`index.html`) :**
   Conception d'un tableau de bord initial permettant de visualiser les données des capteurs.
4. **Conteneurisation (Docker) :**
   Mise en place d'un environnement de déploiement unifié avec `docker-compose.yml` pour faciliter l'installation (incluant la base de données et les services associés).
5. **Documentation :**
   Rédaction d'une documentation professionnelle (`README.md` et `DEMO_CHECKLIST.md`) pour faciliter la prise en main du projet.

### 4.3 Problèmes rencontrés et solutions mises en œuvre

Durant cette première phase, quelques défis techniques ont été rencontrés :

- **Problème de Sécurité (Gestion des mots de passe) :** Lors de la configuration initiale de l'interface web (JavaScript) et des scripts Python, les identifiants d'accès (serveur MQTT, base de données, mot de passe administrateur) étaient codés "en dur" (hardcoded) dans le code source, ce qui représente un risque de sécurité majeur, surtout lors de la publication sur GitHub.
  * **Solution :** Un audit de sécurité a été réalisé. Le travail est en cours pour migrer toutes les données sensibles vers des variables d'environnement (fichier `.env`) afin que les mots de passe ne soient plus jamais enregistrés dans le code source.
- **Synchronisation et affichage en temps réel :** Assurer la communication fluide entre le broker MQTT et l'interface Web a demandé des ajustements de configuration pour éviter les latences (CORS et paramètres de connexion WebSockets).

### 4.4 Description du travail restant (2ème partie) et échéancier (Deadlines)

La deuxième partie du projet de recherche sera consacrée à la sécurisation complète, l'amélioration de l'expérience utilisateur et l'analyse finale de la solution.

* **Semaine 1 (Prochaine étape) :** 
  - Finaliser l'application du patch de sécurité : suppression définitive des mots de passe dans `index.html`, `main.py` et `api_mqtt.py`, et configuration stricte via `.env`.
* **Semaine 2 :** 
  - Amélioration de l'interface graphique (UI/UX) du tableau de bord Web.
  - Ajout de fonctionnalités d'export ou d'historique des données pour l'analyse.
* **Semaine 3 :**
  - Tests d'intégration de bout en bout (End-to-End testing) pour vérifier la stabilité du système sous une charge de données continue simulée.
* **Semaine 4 :**
  - Rédaction de la documentation finale et du rapport de recherche.
  - Préparation de l'environnement de démonstration selon la `DEMO_CHECKLIST.md`.
