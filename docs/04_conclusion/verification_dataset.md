# Vérification du dataset vs la documentation officielle (audit anti-bêtise)

> Passe de contrôle avant la Vague 1, en confrontant notre pipeline au **README** et
> au **dictionnaire de données** officiels (dossier `ORNL Driver Identification Dataset`).
> But : s'assurer qu'on n'a pas fait de bêtise méthodologique.

## 1. Ce qui est CONFIRMÉ (rien à corriger)

| Notre hypothèse | Documentation officielle | Verdict |
|---|---|---|
| VBOX = GPS/inertie = **confondeur de lieu** à exclure | VBOX 3i = data logger **GPS + inertie** (vitesse, accel, position, heading) | [fait] exact |
| Biométrie = HR/EDA/IBI | **Empatica E4** (cardio + électrodermie) | [fait] exact |
| CAN = signaux **SAE J1939** (préfixe SPN numérique) | CANbus **SAE J1939** via CANLogger3 / TruckCape | [fait] exact |
| Groupes = niveaux d'**awareness** | G1 (17) rien su / G2 (16) prévenu / G3 (17) prévenu+se garer | [fait] **exact** |
| Attaque au **lieu/moment fixe** | attaque au « turn around point », Laporte Ave (survey) ; s'arrête à 1 min OU si on se gare | [fait] cohérent |
| Agrégation **1 s par moyenne** (+ sd/min/max) | downsampling 1 s par moyenne, sd/min/max pour montrer la perte | [fait] exact |

**Audit de la classification des colonnes** (`classify_columns`) :
- Bucket **CAN** (337) : 100 % de SPN J1939 (moteur, carburant, températures, freins,
  couple…). **Aucune** colonne GPS/position/heading ne fuite dedans (vérifié).
- Bucket **VBOX** (312, exclu) : ADC, IMU, Pos_X/Y/Z, PreKF_Latitude/Longitude, accel,
  jerk, pitch… = bien du GPS/inertie. [fait]
- Bucket **BIO** (7) : EDA/HR/IBI. [fait]
- Bucket **META** (exclu) : IDs, temps, `cyberattack_active`, `cumulative_distance_meters`
  (haversine GPS), **et toutes les colonnes Qualtrics** (MMDBQ, GRiPS, démographie).
  -> aucune fuite de survey/lieu dans les features. [fait]

**Confondeurs de progression INTRA-CAN** (déjà gérés) : le bucket CAN contient
légitimement des signaux de mouvement (SPN 84 vitesse roue, 244/245/918 distance,
905-908 vitesses relatives roues). Ils sont corrélés à la position sur le trajet, mais
le test **CAN_STABLE** (P2/P3) avait montré que les exclure ne change rien (0,630 vs
0,632) -> le modèle n'en dépend pas. [fait] Pas de bêtise.

## 2. CE QU'ON A CORRIGÉ

### 2.1. G1S04 : effondrement partiellement dû à la QUALITÉ des données
Le README liste une **erreur de collecte** : *« CANbus Data Collected at Low Frequency:
G1S04 »* (corrélation VBOX/CAN tombée à 0,836 pour ce conducteur, vs ~0,999 ailleurs).
Or **G1S04 = notre pire conducteur en LODO (PR-AUC 0,049)** et membre du Groupe 1.

-> Son effondrement n'est donc **pas seulement** un effet d'awareness : il est en partie
un **artefact de sous-échantillonnage du CAN**. Correction apportée :
[p5b_group_fragility.md](../02_experiences/p5b_group_fragility.md) ajoute le caveat, et on
re-vérifie le gradient **sans G1S04** :

| Groupe | LODO médiane (avec G1S04) | **sans G1S04** |
|---|---|---|
| 1 | 0,740 (moy 0,606 ; 6/17 < 0,5) | **0,750 (moy 0,641 ; 5/16 < 0,5)** |
| 2 | 0,923 | — |
| 3 | 0,960 | — |

**Le gradient d'awareness survit** : le Groupe 1 reste nettement le plus faible même en
retirant le conducteur à données dégradées. Conclusion P5+ **maintenue**, caveat ajouté.

### 2.2. BÊTISE corrigée : le « spoofing du régime moteur » n'existe pas dans les features
En P5 j'avais écrit que le SPN 190 (Engine Speed) était *« une signature plausible de
spoofing CAN (manipulation du régime) »*. **C'est faux.** L'attaque met tachymètre/
compteur à **zéro**, mais dans les signaux agrégés :

| Signal | Attaque (moy / % ~0) | Normal (moy / % ~0) |
|---|---|---|
| `mean.190.Engine.Speed` | 1197 / **0,0 %** | 1214 / 0,0 % |
| `mean.190.Engine.Speed.CAN0` | 1337 / 0,7 % | 1212 / 0,0 % |
| `mean.84.Wheel.Based.Vehicle.Speed` | 44 / 8,2 % | 30 / 18,6 % |

Le régime moteur **n'est jamais mis à zéro** dans nos données (0 % de ~0 ; trace de 0,7 %
seulement sur le bus CAN0). **Le logger a enregistré les vraies diffusions ECU, pas les
messages malveillants injectés vers le tableau de bord.**

**Conséquence (importante)** : l'**injection elle-même est absente** des features
agrégées à la seconde. Le modèle ne détecte donc **que la réaction du conducteur + le
contexte routier** de la fenêtre d'attaque — ce qui **confirme et durcit** la conclusion
P5+ (« on détecte la réaction, pas l'injection »), mais invalide l'idée d'un cœur de
détection « spoofing ». La phrase fautive est corrigée dans
[p5_evaluation.md](../02_experiences/p5_evaluation.md).

> **[Nuance Vague 2 — 2026-06-19] Le constat ci-dessus regardait les VALEURS ; il faut le
> compléter par la DISPONIBILITÉ.** L'analyse inter-bus du SPN 190
> ([v2_injection_signature.md](../02_experiences/v2_injection_signature.md)) montre que
> l'injection **EST présente** dans les features — non comme un régime à 0, mais comme le
> **silence du bus CAN0** : pendant l'attaque, la couverture CAN0 chute de 67 % à 6,7 %
> (~4 s après l'onset, marche d'escalier), tous groupes confondus. Donc l'injection laisse
> bien une trace exploitable (la *missingness* du canal), distincte de la réaction. « Absent
> en valeur » oui, mais « **présent en disponibilité** ». Cela **nuance A1** (une partie de
> l'injection est isolable) sans l'annuler (le Groupe 1, dont CAN0 n'est quasi pas logué,
> reste un angle mort).

## 3. Impact sur les conclusions

- Les **chiffres** (PR-AUC 0,756 ; anomalie ~0,02 ; deep < arbres ; gradient d'awareness)
  **restent valides** : aucune fuite de feature, aucun mauvais split.
- Ce qui change, c'est l'**interprétation de l'importance** : le SPN 190 ne capte pas le
  spoof (absent) mais le **comportement/contexte** -> renforce A1 (cible conflée
  injection+réaction) et B3/B4 (injection sous-seconde perdue par l'agrégation 1 s) de
  l'[auto-critique](autocritique.md).
- Données dégradées à signaler dans tout livrable : **G1S04** (CAN basse fréquence),
  **G1S15/G1S16/G2S13/G3S13** (VBOX manquant, sans impact car GPS exclu), **G1S09** (reset
  VBOX en fin de trajet).

-> Aucune bêtise bloquante. Deux corrections d'honnêteté appliquées. **On peut passer à la
Vague 1.**
