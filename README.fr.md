# AKA.CRISTI Skills — Présentation en français

🌐 **Language / Langue :** [English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Français](README.fr.md)

**FROM EXPERIENCE TO CAPABILITY｜Transformer l'expérience de collaboration en capacité réutilisable**

## À propos du projet

AKA.CRISTI Skills est un ensemble public, vérifiable et installable localement de **Skills de flux de travail pour agents IA**, accompagné d'un installateur sécurisé et de la configuration de collaboration CHEF pour Codex. L'objectif est que l'IA, face à une tâche complexe, ne se contente pas de proposer des suggestions, mais suive une méthode de travail : « objectif clair → vérification de l'environnement → exécution répartie → vérification des résultats → reprise sur erreur → consignation de l'expérience réutilisable ».

**À distinguer :** une Skill est une description et une procédure qui guident la façon de travailler d'un Agent, **ce n'est pas un cerveau IA autonome**. Elle n'obtient pas non plus automatiquement les identifiants de GitHub, Codex, Hermes, Claude ou d'autres services. La possibilité réelle d'appeler un Agent dépend de la version de l'hôte, des connexions d'outils et des autorisations sur votre machine.

Ce dépôt est une version de distribution publique, séparée du dépôt de développement privé d'AKA.CRISTI. Aucune règle de travail privée, information de compte, donnée client ou historique privé n'y est publiée.

## Version publique actuelle : Beta Codex disponible

**[v1.0.0-beta.2](https://github.com/2ndforcecrew/aka-cristi-skills/releases/tag/v1.0.0-beta.2)** est une version de test publique. Elle inclut les règles CHEF, quatre Skills, quatre configurations de rôles Codex, un installateur graphique Windows et une commande unifiée Windows/macOS/Ubuntu. **Les CI des trois systèmes, la compilation de l'EXE et la provenance GitHub sont validées.** Les essais d'installation indépendants et l'exécution réelle des quatre agents restent à vérifier.

Prérequis : Git et Python 3.11+. Les modifications sont prévisualisées ; saisir `INSTALL` autorise leur application.

Windows PowerShell :

```powershell
git clone https://github.com/2ndforcecrew/aka-cristi-skills.git; if ($LASTEXITCODE -ne 0) { throw 'Clone failed' }; cd aka-cristi-skills; git checkout v1.0.0-beta.2; if ($LASTEXITCODE -ne 0) { throw 'Tag checkout failed' }; py -3 -m tools.quick_install --interactive
```

macOS / Ubuntu / Linux :

```bash
git clone https://github.com/2ndforcecrew/aka-cristi-skills.git && cd aka-cristi-skills && git checkout v1.0.0-beta.2 && python3 -m tools.quick_install --interactive
```

`FILES_VERIFIED` prouve seulement l'intégrité des fichiers, pas l'activation réelle des agents. L'EXE ne porte pas de signature Authenticode. Vérifier sa provenance et utiliser un environnement isolé.

**À propos des anciens scans :** l'ancienne mention `DO_NOT_INSTALL` et les constats SkillSpector concernent un ancien instantané du code, non une évaluation actuelle de la Beta. SkillSpector n'est pas obligatoire pour installer ni publier. Les [résultats historiques](docs/SECURITY_REVIEW_2026-11-15.md) sont conservés sans affirmer que tous les constats sont des vulnérabilités ou des faux positifs.

## 1. Fonctionnalités principales

### 1. CHEF Orchestrator : chef d'orchestre des tâches IA

Fichier : [chef-orchestrator/SKILL.md](skills/chef-orchestrator/SKILL.md)

- **Objectif et acceptation :** transformer la demande de l'utilisateur en conditions d'achèvement observables, limites d'autorisation et conditions d'arrêt.
- **Inspect :** lire d'abord les règles du projet, la configuration existante, l'état Git et les outils disponibles, afin d'éviter d'écraser le travail existant.
- **Répartition des tâches :** planifier selon les besoins les responsabilités Research, Creative, Coding, QA, Automation, Knowledge.
- **Transfert traçable :** préciser l'ID de la tâche, les outils réellement utilisés, la portée des fichiers, les entrées et sorties, les délais, le nombre de tentatives et les critères d'acceptation.
- **Exécution réelle :** n'appeler un autre Agent que lorsqu'une vraie connexion existe. Dans le cas contraire, consigner clairement `BLOCKED` ou `NOT_RUN`, sans inventer de résultat de délégation.
- **Vérification indépendante :** examiner le code, les tests, les journaux et le parcours utilisateur réel, et distinguer « terminé » de « vérifié ».
- **Méthode de reprise automatique :** face à un échec, diagnostiquer dans des limites définies, appliquer une correction minimale et retester. Les opérations irréversibles exigent toujours une autorisation.
- **Capitalisation de l'expérience :** seuls les processus répétés réellement vérifiés sont extraits en Skills à examiner, sans publication ni installation automatique.

### 2. Verified Change Loop : boucle de diagnostic et de correction

Fichier : [verified-change-loop/SKILL.md](skills/verified-change-loop/SKILL.md)

Reproduire le problème → examiner les preuves → correction minimale et réversible → réexécuter le même scénario → comparer les résultats → tests de régression → livraison avec acceptation. Convient aux bugs de code, aux pannes CI, aux anomalies de fonctionnalités web et aux corrections complexes.

### 3. Feature Journey Map : parcours utilisateur réel

Fichier : [feature-journey-map/SKILL.md](skills/feature-journey-map/SKILL.md)

Consigner le parcours complet de l'utilisateur, de l'entrée et de l'initialisation jusqu'au résultat visible, en couvrant les états vides, les permissions insuffisantes, les entrées erronées et les réseaux lents. Éviter de déclarer un produit utilisable sur la seule foi des tests unitaires.

### 4. Skill Evaluation Gate : contrôle qualité des Skills

Fichier : [skill-evaluation-gate/SKILL.md](skills/skill-evaluation-gate/SKILL.md)

Déterminer, à partir de scénarios réels, de preuves de tests, d'une relecture indépendante et d'une autorisation de publication, si une Skill peut passer à l'étape suivante. Distinguer Candidate, Tested, Reviewed, Approved / Released, sans assimiler le succès de l'installation à celui de l'exécution.

### 5. CHEF Global Rules : règles de travail multi-projets

- Écrire les règles CHEF **rendues publiques après désensibilisation** dans `~/.codex/AGENTS.md` ou `$CODEX_HOME/AGENTS.md`.
- La commande `preview` est disponible avant l'installation ; l'écriture réelle exige `--apply`.
- Les règles sont ajoutées sous forme de bloc balisé géré, en préservant autant que possible le contenu existant ; les fichiers existants sont sauvegardés.
- La vérification et la désinstallation du bloc géré sont prises en charge ; cela n'équivaut pas à une synchronisation automatique des règles privées sur tous les ordinateurs.

Explication technique : [CHEF Global Rules + Multi-Agent Starter](docs/CHEF_GLOBAL_AND_MULTIAGENT.md).

### 6. Codex Native Subagents : quatre rôles

| Rôle | Nom | Responsabilité principale |
| --- | --- | --- |
| Research | `aka_research` | Rechercher des faits, organiser sources et preuves |
| Coding | `aka_coding` | Programmer, corriger et tester dans le périmètre autorisé |
| QA | `aka_qa` | Examen et vérification indépendants de la version finale |
| Automation | `aka_automation` | Concevoir des flux d'automatisation sûrs et bornés |

Le dépôt fournit les configurations TOML des quatre Agents Codex natifs personnalisés ainsi que les scripts d'installation et de vérification. **Installer la configuration ne signifie pas que les quatre Agents ont réellement démarré**, et encore moins qu'ils peuvent appeler les comptes d'autres fournisseurs. Une décision formelle exige de vrais sous-threads Codex et des journaux d'exécution.

Détails : [Codex Native Subagents V0.2](docs/CODEX_NATIVE_SUBAGENTS_V02.md).

### 7. Installateur local et sûr de Skills

- Prise en charge de l'aperçu local, de l'installation, de la vérification d'intégrité des fichiers, de la mise à niveau, du retour en arrière et de la désinstallation.
- Refuse d'écraser une Skill non gérée par l'installateur ou modifiée de l'extérieur.
- Ne télécharge pas de code depuis le réseau, n'exécute pas de script interne aux Skills, ne téléverse pas de secrets.
- La désinstallation conserve une archive ; le retour en arrière exige une sauvegarde antérieure réellement existante.
- Ce n'est ni un antivirus ni une vérification de signature numérique ; la CLI actuelle n'équivaut pas à une interface graphique en un clic. L'interface graphique candidate exige encore une acceptation en environnement réel.

## 2. Installation pour un ami (Windows 11 / macOS / Linux)

Prérequis : installer [Git](https://git-scm.com/downloads) et Python 3.11 ou plus, et utiliser un terminal local disposant des droits nécessaires. Lisez d'abord le contenu du dépôt par vous-même ; l'installation modifie les fichiers Codex locaux de l'utilisateur courant.

### Étape 1 : télécharger le dépôt public

```powershell
git clone https://github.com/2ndforcecrew/aka-cristi-skills.git
cd aka-cristi-skills
```

### Étape 2 : prévisualiser les règles globales CHEF et la Skill principale

```powershell
python -m tools.chef_global_rules preview
python -m tools.skill_installer preview skills/chef-orchestrator --target codex
```

### Étape 3 : autoriser explicitement l'installation locale

```powershell
python -m tools.chef_global_rules install --apply
python -m tools.skill_installer install skills/chef-orchestrator --target codex --apply
python -m tools.skill_installer install skills/verified-change-loop --target codex --apply
python -m tools.skill_installer install skills/feature-journey-map --target codex --apply
python -m tools.skill_installer install skills/skill-evaluation-gate --target codex --apply
```

### Étape 4 : installer les quatre rôles Codex natifs (facultatif)

```powershell
python -m tools.codex_subagents preview
python -m tools.codex_subagents install --apply
python -m tools.codex_subagents verify
```

### Étape 5 : vérifier les fichiers installés

```powershell
python -m tools.chef_global_rules verify
python -m tools.skill_installer verify chef-orchestrator --target codex
python -m tools.skill_installer verify verified-change-loop --target codex
```

Ces commandes vérifient la **configuration et les fichiers**, sans prouver que Codex a appelé une Skill ou démarré les quatre Agents. Rouvrez une session Codex, testez une vraie délégation et conservez la preuve d'exécution réelle.

Si Codex CLI est installé et connecté sur votre machine, vous pouvez exécuter l'acceptation stricte d'exécution des quatre rôles (cela peut consommer du quota Codex) :

```powershell
codex login status
python -m tools.verify_four_agents --timeout 600 --out four-agent-report.json
```

Les résultats d'acceptation doivent être distingués en `PASS`, `FAIL`, `INCONCLUSIVE`, `NOT_RUN`. Sans preuve de thread réel, il est impossible de prétendre à une réussite. Voir : [acceptation d'exécution réelle des quatre Agents](docs/FOUR_AGENT_RUNTIME_ACCEPTANCE.md).

## 3. Capacités réelles et limites

| Élément | Limite actuelle |
| --- | --- |
| Fichiers Skill publics et installateur CLI | Déjà fournis dans le dépôt ; lisibles, téléchargeables et exécutables localement |
| Installation des règles globales CHEF | Aperçu sûr, installation par bloc géré et vérification fournis |
| Configuration des quatre rôles Codex natifs | TOML et outils d'installation / vérification fournis |
| Détection et correction automatiques de toutes les erreurs réelles de projet | **Non garanti** ; dépend des outils, des droits, du projet et des tests réels |
| Connexion automatique à Hermes, Claude ou d'autres Agents de marque | **Connexion générique non implémentée** ; une adaptation API / MCP / CLI distincte est nécessaire |
| Réussite d'exécution des quatre Agents dans l'environnement Codex réel de l'utilisateur | **À vérifier séparément sur un appareil Codex réel et connecté** |
| Publication automatique de l'expérience réussie en Skill | Un processus d'évaluation existe, mais **ce n'est pas un système de publication automatique sans examen** |
| Synchronisation automatique multi-appareils et installation graphique en un clic | Pas encore une fonctionnalité vérifiée de cette version de distribution publique |

## 4. Principes de sécurité

- Ne pas écraser les règles privées existantes ni les Skills non gérées ; d'abord prévisualiser, puis exécuter explicitement.
- Ne pas téléverser de mots de passe, de clés API, de conversations privées ni de données clients.
- Ne pas confondre les tests locaux, les sorties simulées ou les déclarations d'un Agent avec des résultats d'exécution réels.
- Ne pas effectuer automatiquement d'opérations à haut risque : paiements, changements de droits, publication de production, suppression de données.
- Toute connexion d'Agent multi-plateforme exige une autorisation indépendante et une acceptation réelle.

## 5. Direction du projet

Avec **DESIGN × CODE × AI × AUTOMATION × BUSINESS** comme cap, améliorer progressivement une expérience d'installation plus conviviale, l'adaptation multi-Agents, des journaux de tâches auditables, l'évaluation des Skills et la maintenance continue. Les capacités inachevées sont listées comme planifiées uniquement, jamais déclarées livrées.

---

**AKA.CRISTI · CREATE BEAUTIFULLY. BUILD INTELLIGENTLY. AUTOMATE EVERYTHING REASONABLE.**
