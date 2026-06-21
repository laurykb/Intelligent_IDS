# Auto-critique — seconde passe (dataset ORNL Driver ID)

> Revue complémentaire (angles nouveaux, hors A1-A6 de
> [autocritique.md](autocritique.md)). Calibrée pour un projet d'école d'ingénieur
> (~3 mois), sur le dataset **final** correspondant au sujet.

## Question directrice : a-t-on exploré le projet de fond en comble ?

Réponse honnête : **on est allé très en profondeur sur UN axe** — l'honnêteté
méthodologique (confondeurs lieu/temps, split par conducteur, gradient d'awareness : ça
touche au niveau recherche) — **mais la LARGEUR a des trous réels**, et on a même laissé
ouvertes **deux demandes littérales du sujet** (courbe ROC, optimisation
d'hyperparamètres). Pour un livrable d'école, certaines explorations fines (P5+) ont été
menées **avant** des bases peu coûteuses et attendues. Le déséquilibre profondeur/largeur
est en soi une critique.

## B. Les angles non couverts (nouveaux)

> **[MAJ 2026-06-19 — état après Vagues 1/2]** : **B1** (injection vs réaction) → isolé via la
> signature CAN0 ([v2_injection_signature.md](../02_experiences/v2_injection_signature.md)) ;
> **B2** → [v2_taxonomy.md](../02_experiences/v2_taxonomy.md) ; **B3** (caractérisation fine) +
> **B4** (latence 2 ms / 695 Ko) → [v2_attack_characterization.md](../02_experiences/v2_attack_characterization.md) ;
> **B6** rigueur stat → Vague 1 ; **B7** papier ORNL → V1-6 ; **B9** clustering/semi-sup →
> [v2_hybrid.md](../02_experiences/v2_hybrid.md) ; **B12** biométrie →
> [v2_biofusion.md](../02_experiences/v2_biofusion.md). **Restent des sections de DISCUSSION
> (non codées, à mettre dans le rapport/la démo)** : B5 poisoning, B7 table SOTA, B8 gestion de
> projet, B11 éthique/dual-use/RGPD, B13 coût opérationnel.

### B1. Cible conflée (injection + réaction) — la limite de validité fondamentale
Toutes nos conclusions reposent sur une cible (`cyberattack_active`) qui **mélange
l'injection CAN et la réaction du conducteur**. On ne peut pas, en l'état, prouver qu'on
détecte l'**intrusion** plutôt que le **comportement de réponse**. C'est l'équivalent ici
de la « donnée unique » du projet précédent : une **faille de base inférentielle**, plus
structurante que l'adversarial.

### B2. Modèle de menace étroit
On ne traite qu'**une** attaque (mise à zéro tachymètre/compteur). L'ELD compromis peut
écrire des messages CAN **arbitraires** (cf. sujet). On n'a pas couvert de **taxonomie** :
DoS / bus-off, fuzzing, replay d'autres PGN, masquerade sans effet visible, suspension de
messages. Notre IDS est de fait un **détecteur mono-attaque**.

### B3. L'attaque jamais caractérisée finement
On sait *que* l'attaque met les compteurs à zéro, mais on n'a pas **dit précisément ce
qu'elle écrit sur le bus** : quels SPN/PGN, à quel instant, sur quel canal (`CAN0` vs
l'autre). On a *entrevu* l'incohérence inter-bus du SPN 190 sans la décoder ni la
confirmer. Un rapport d'ingénieur va au bout de l'investigation.

### B4. Faisabilité embarquée non analysée
Où vit l'IDS (dans l'**ELD** ? une **passerelle** ? le **cloud** ?), budget de **latence**
bout-en-bout, **empreinte mémoire** du modèle ? De plus, l'**agrégation à la seconde**
(mean/sd/min/max) **perd déjà** la signature **sous-seconde** d'une injection rapide :
notre cadrage est confortable pour le ML mais éloigné d'un IDS temps réel sur trames.

### B5. Sécurité de l'IDS lui-même
Aucune analyse des attaques **contre** le détecteur. En particulier le **poisoning** du
profil « normal » : comme l'attaque survient toujours au **même lieu**, un « normal »
appris naïvement est fragile, et un adversaire pourrait empoisonner l'apprentissage.

### B6. Rigueur statistique partielle
Deep **mono-seed**, **hyperparamètres non réglés**, pas d'intervalles de confiance
généralisés ni de tests de significativité systématiques (l'écart MLP 0,532 vs GRU 0,566
est-il significatif ?). Le LODO (50) est solide, mais le reste est plus mince.

### B7. Pas de positionnement vs la littérature
On a des chiffres honnêtes mais on ne les a **jamais comparés** à ceux du **papier source
ORNL** ni au **SOTA CAN IDS** (CIDS, CANet, ROAD). Un travail académique se situe.

### B8. Gestion de projet absente des livrables
Pas de planning/jalons, ni spécification d'exigences, ni analyse de risques, ni critères
de succès tracés. Le `journal.md` est un carnet, pas un plan projet.

### B9. Curriculum couvert en théorie, pas en pratique
Plusieurs items du programme ML restent **documentés mais non appliqués** : clustering
(K-means/DBSCAN/GMM), semi-/self-supervisé, régression (Lasso/Ridge/ElasticNet),
auto-encodeur neuronal, reinforcement learning. La pratique s'est concentrée sur la
détection supervisée.

### B10. Génie logiciel perfectible
Pas de packaging (`pyproject.toml`), pas de lint / type-check / CI, pas de tests, scripts
en `.py` plutôt qu'en notebooks interactifs `.ipynb`.

### B11. Éthique, divulgation, cadre légal
Projet sur une **vulnérabilité réelle** (compromission ELD, avis **CISA**) : aucune section
sur l'usage responsable, le caractère **dual-use**, le cadre légal, la divulgation
coordonnée. De plus, ce dataset comporte de la **biométrie humaine** -> enjeux **RGPD /
consentement / vie privée** à traiter explicitement.

### B12. L'originalité du dataset (biométrie + awareness) sous-exploitée
Ce jeu de données se distingue d'un dataset CAN générique **précisément** par la biométrie
et les **niveaux d'awareness**. On en a fait l'angle le plus *intéressant* en analyse
(P5+), mais pas un **axe de modélisation** (fusion, détection assistée par l'état du
conducteur). C'est l'apport différenciant qu'on a le plus de marge à valoriser.

### B13. Dimension opérationnelle et économique
Coût des **fausses alertes** en exploitation de flotte, **fatigue d'alerte**, intégration
dans un **SOC/télématique** : non traités. Or c'est ce qui décide de l'adoption — et notre
courbe PR montre justement un compromis dur à haut rappel (precision 0,22 à rappel 0,9).

## C. Addendum au plan d'amélioration (priorisé pour ~3 mois)

| Priorité | Action | Effort | Pourquoi |
|---|---|---|---|
| **Haute** | **Courbe ROC + optimisation d'hyperparamètres** (demandes littérales du sujet) | faible | conformité au sujet, peu coûteux |
| **Haute** | **Caractériser l'attaque** (SPN/PGN écrits, onset, canal) + incohérence inter-bus | moyen | clôt B3, ouvre la détection d'injection pure (A1) |
| **Haute** | Section **déploiement** (où vit l'IDS, latence, mémoire) + **éthique/RGPD/légal** | faible | attendu d'un livrable ingénieur |
| **Haute** | Artefacts de **gestion de projet** (jalons, exigences, risques) | faible | format école d'ingénieur |
| **Haute** | **Latence + métriques par épisode** (a-t-on détecté les 50 attaques ?) | faible | *la* métrique IDS qui manque |
| Moyenne | **Exploiter biométrie + awareness** comme axe (fusion conditionnée, cas Groupe 1) | moyen | valorise l'originalité du dataset (B12) |
| Moyenne | **Taxonomie de menaces** + 1-2 attaques synthétiques | moyen | sort du mono-attaque (B2) |
| Moyenne | **Généralisation ROAD/Car-Hacking** + comparaison littérature | élevé | seule vraie preuve de généralisation (B1, B7) |
| Moyenne | Appliquer 1-2 items curriculum (clustering, semi-supervisé) | moyen | complétude pédagogique (B9) |
| Basse | Packaging + lint + CI + tests | moyen | qualité logicielle (B10) |

## D. Le verdict

Le projet a une **profondeur rare** sur l'honnêteté méthodologique et la découverte du
**gradient d'awareness** (c'est sa force et son originalité). Mais en tant que **livrable
d'école d'ingénieur**, il lui manque surtout :

1. les **demandes littérales du sujet** non coûteuses (**ROC**, **hyperparamètres**, latence) ;
2. la **largeur d'ingénierie** (modèle de menace, déploiement, gestion de projet, éthique/RGPD) ;
3. l'**exploitation de l'originalité du dataset** (biométrie + awareness) au-delà de l'analyse.

La priorité raisonnable avant la soutenance n'est **pas plus de profondeur**, mais
**combler ces bases** — la plupart sont peu coûteuses et augmentent fortement la
crédibilité devant un jury.
