# IDS Intelligent - Detection de cyberattaque sur le dataset ORNL Driver ID

> Projet integrateur 2026 - Encadrant : Rida Khatoun
> Detection, par machine learning, d'une cyberattaque dans le comportement d'un
> camion (Kenworth T270), a partir d'un dataset multimodal sur 50 conducteurs
> (CANbus J1939 + GPS/inertie + biometrie).

## Le projet en bref

Le dataset enregistre 50 conducteurs subissant une cyberattaque (mise a zero du
tachymetre/compteur de vitesse) a un moment de leur trajet. La cible est
`cyberattack_active` (1,46 % du temps). Ce depot construit, etape par etape, un
detecteur d'intrusion **honnete**.

## Le defi central (ce qui rend le projet rigoureux)

L'attaque a toujours lieu **au meme endroit** et a un **moment fixe** du trajet.
Un modele naif atteindrait une accuracy quasi parfaite en detectant le **lieu**
(via le GPS) et l'**heure** - sans rien comprendre a l'attaque. Tout l'enjeu est
de construire un detecteur **sans ces confondeurs**, avec un **split par
conducteur** (anti-fuite) et des metriques adaptees au desequilibre (PR-AUC).

## Structure du depot

```
data/      jeu de donnees ORNL + dictionnaire (cache parquet)
src/       data.py (chargement + classification des colonnes en CAN / GPS / bio)
notebooks/ experiences reproductibles (01_exploration, ...)
docs/      theorie, projet, experiences, evaluation, conclusion
app/       demonstrateur (a venir)
deliverables/ rapport et slides (a venir)
tests/     tests unitaires
```

## Demarrage rapide

```bash
pip install -r requirements.txt
python src/data.py               # apercu : colonnes classees, % attaque
python notebooks/01_exploration.py   # EDA + figures
```

## Avancement

- [x] **P0** - Cadrage (contexte, problematique, plan)
- [x] **P1** - Exploration : confondeurs lieu/temps, 1,46 % d'attaque, reponse biometrique
- [x] **P2/P3** - Pretraitement, selection hors confondeurs, split par conducteur
  - Honnete = PR-AUC **0,632** (CAN, split conducteur) ; GPS spurieux 0,834 ; fuite aleatoire 0,985
- [~] **P4** - Modelisation : [x] A supervise - [ ] B anomalie - [ ] C deep
  - Chemin A : Gradient Boosting **PR-AUC 0,756** (CAN, val. par conducteur) ; biometrie inutile ; GPS spurieux 0,835
- [ ] **P5** - Evaluation (PR-AUC, validation croisee groupee), tuning
- [ ] Robustesse, couche intelligente, demo, livrables

## Donnees

ORNL Driver Identification Dataset (downsampled), 155 902 fenetres de 1 s, 50
conducteurs, Kenworth T270. Meme ecosysteme de recherche que l'avis CISA
ICSA-24-093-01 (equipe J. Daily, Colorado State).
