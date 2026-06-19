# Contexte du projet

> Projet integrateur 2026 - Detecteur d'intrusion intelligent (IDS)
> Encadrant : Rida Khatoun - Dataset : ORNL Driver Identification (downsampled)

## 1. Le but en une phrase

Construire un systeme, base sur du machine learning, capable de **detecter une
cyberattaque** dans le comportement d'un camion, a partir d'un jeu de donnees
multimodal collecte sur 50 conducteurs.

## 2. Le terrain : un dataset multimodal sur 50 conducteurs

Le **ORNL Driver Identification Dataset** a ete construit pour etudier le
comportement de conduite (et, accessoirement, identifier le conducteur). 50
conducteurs ont conduit un **Kenworth T270 Class 6** autour de Fort Collins
(Colorado), pendant qu'on enregistrait plusieurs sources de donnees.

| Modalite | Source | Contenu |
|---|---|---|
| **CANbus (J1939)** | CANLogger3 / TruckCape | ~340 signaux moteur/vehicule **deja decodes** (regime, pedale, couples, temperatures...) |
| **GPS + inertie** | VBOX 3i | position, vitesse, altitude, acceleration, tangage/roulis |
| **Biometrie** | moniteur cardiaque | rythme cardiaque (HR), electrodermie (EDA), inter-battement (IBI) |

> Meme ecosysteme de recherche que l'attaque ELD (equipe de Jeremy Daily,
> Colorado State University).

## 3. L'attaque

Une **cyberattaque est executee pendant CHAQUE trajet**. Elle allume plusieurs
temoins d'erreur au tableau de bord et **met le tachymetre et le compteur de
vitesse a zero**, quelle que soit la vitesse reelle. Elle survient **toujours au
meme endroit** (peu apres North Overland Trail sur Laporte Avenue) et s'arrete
**apres 1 minute ou si le conducteur s'arrete sur le bas-cote**.

### Trois groupes d'awareness
Les conducteurs sont repartis selon leur connaissance prealable de l'attaque :

| Groupe | N | Connaissance | Consigne |
|---|---|---|---|
| 1 | 17 | aucune (attaque totalement inattendue) | - |
| 2 | 16 | prevenu qu'une attaque peut survenir | - |
| 3 | 17 | prevenu + invite a s'arreter si elle survient | s'arreter |

> Ce design permet d'etudier aussi la **reponse humaine** a l'attaque (stress),
> via la biometrie - un axe que notre EDA exploite.

## 4. La structure des donnees

Le fichier est une **version downsamplee** : chaque variable est agregee a la
**seconde** (moyenne, ecart-type, min, max sur la seconde). On obtient donc une
**fenetre de 1 s par ligne** - le feature engineering temporel est, en partie,
deja fait.

| Element | Valeur |
|---|---|
| Lignes (fenetres de 1 s) | **155 902** |
| Colonnes | **816** (4 stats x ~200 variables) |
| Conducteurs | **50** (Group x Subject) |
| **Labels fournis** | `cyberattack_active` (IDS) et `Subject`/`Group` (conducteur) |
| Signaux CAN exploitables | ~337 |
| Biometrie | HR, EDA, IBI |

## 5. En quoi ce dataset change tout (vs un log CAN brut)

- **Donnees pre-decodees et pre-agregees** : pas de parsing de trames brutes, pas
  de decodage J1939 a faire - les signaux sont des grandeurs physiques nommees.
- **Labels fournis** : `cyberattack_active` existe. Plus besoin de fabriquer la
  verite terrain.
- **Population reelle** : 50 conducteurs = vraie base pour generaliser (vs un seul
  log).
- **Desequilibre realiste** : l'attaque ne represente que **1,46 %** du temps.
- **Multimodal** : CAN + GPS + biometrie ouvre des questions nouvelles.

> Mais ces atouts s'accompagnent d'un **piege methodologique majeur** (l'attaque a
> lieu a un endroit et un moment fixes) que la problematique detaille.

-> Suite : [problematique.md](problematique.md) - [eda_findings.md](eda_findings.md)
