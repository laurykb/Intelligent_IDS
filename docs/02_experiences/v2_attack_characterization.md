# Auto-critique v2 — B3 (caractérisation fine de l'attaque) + B4 (faisabilité)

> Code : [`notebooks/12_attack_characterization.py`](../../notebooks/12_attack_characterization.py) -
> Résultats : [`docs/03_evaluation/results_characterization.json`](../03_evaluation/results_characterization.json) -
> Figure : `docs/assets/v2_attack_fingerprint.png`. Reste **in-scope** de
> [autocritique_v2.md](../04_conclusion/autocritique_v2.md) (B3, B4).

## B3 — l'empreinte de l'attaque dans le CAN (onset, 51 épisodes)

Pour chaque signal CAN, on aligne sur le début d'attaque et on mesure le **step** =
moyenne[t∈+4..+10 s] − moyenne[t∈−10..−1 s]. La fenêtre ±10 s **filtre les confondeurs à
dérive lente** (qui ne font pas de marche à +4 s). On sépare deux signatures :

**Signature 1 — DISPONIBILITÉ (= l'injection)**

| Signal | Step de disponibilité |
|---|---|
| `*.190.Engine.Speed.CAN0` (mean/sd/min/max) | **−0,72** |
| (signal suivant) | −0,03 |

→ Seul le **bus CAN0 du régime moteur** disparaît. Tout le reste est plat. La signature de
**l'injection** est isolée et unique : le **silence de CAN0** (cf. [item 1](v2_injection_signature.md)).

**Signature 2 — VALEUR (= la réaction du conducteur / du véhicule)**

À +4 s, une grappe de signaux **moteur** chute brutalement (z ≈ −1,5) :

| Signal | Step (z-score) |
|---|---|
| EGR Mass Flow Rate (2659) | −1,58 |
| Estimated Brake Power (1242) | −1,50 |
| Engine Fuel Rate (183) | −1,48 |
| Engine Demand % Torque (2432) | −1,48 |
| Actual Engine % Torque (513) | −1,45 |
| EGR Valve Position (27) | −1,43 |

→ Débit EGR, carburant, couple demandé, puissance de freinage : **la charge moteur s'effondre**
~4 s après l'onset = le **véhicule décélère** (le conducteur lève le pied / se gare). C'est la
**réaction**, distincte de l'injection.

**Conclusion B3** : l'attaque laisse **deux empreintes simultanées à +4 s** — (1) *injection* :
silence du bus CAN0 ; (2) *réaction* : effondrement de la charge moteur. Cela **confirme
concrètement, signal par signal, la dichotomie A1** (le détecteur voit les deux). On ne peut pas
voir *ce que l'injection écrit* (le logger n'a capté que les vraies diffusions ECU, cf.
[verification_dataset.md](../04_conclusion/verification_dataset.md)), mais on a **caractérisé
précisément son EFFET** (canal CAN0, onset +4 s) — ce que B3 demandait.

## B4 — faisabilité embarquée (mesurée)

| Mesure | Valeur |
|---|---|
| Taille du modèle sérialisé (champion HistGB) | **695 Ko** |
| Latence d'inférence, 1 fenêtre | **2,25 ms** |
| Débit en lot | **562 000 fenêtres/s** |

**Conclusion B4** : le détecteur est **trivial à déployer** (< 1 Mo, 2 ms/fenêtre) — il tiendrait
dans une **passerelle embarquée** ou l'ELD lui-même, bien en deçà du budget temps réel à l'échelle
1 s. **Le goulot n'est pas le calcul mais la donnée** : l'agrégation **1 s** (mean/sd/min/max)
**perd la signature sous-seconde** d'une injection rapide. Un IDS temps réel sur trames brutes
exigerait la donnée haute-résolution (piste hors-scope, citée en perspectives).

## Reste de l'auto-critique v2 → sections de discussion (rapport/démo)

B5 (poisoning), B7 (table SOTA), B8 (gestion de projet), B11 (éthique/dual-use/RGPD), B13 (coût
opérationnel / fatigue d'alerte) ne sont **pas des expériences** mais des **sections écrites** :
elles seront intégrées au **rapport** et à la **démo interactive** (onglets dédiés), pas codées.
