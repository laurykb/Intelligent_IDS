# Vague 2 - Item 3 : fusion biométrie conditionnée par awareness (réponse à A5)

> Code : [`notebooks/09_biometric_fusion.ipynb`](../../notebooks/09_biometric_fusion.ipynb) -
> Résultats : [`docs/03_evaluation/results_biofusion.json`](../03_evaluation/results_biofusion.json) -
> Figure : `docs/assets/v2_biofusion.png`. Répond à **A5** (biométrie + awareness sous-exploitées).

## Question

P4-A avait conclu « biométrie inutile » (BIO seule 0,014 ; CAN+BIO 0,749 ≤ CAN 0,756) — mais
**globalement**. A5 objecte : le vrai signal est la **réaction** (P5+), et la biométrie (HR/EDA)
**est** la réaction physiologique. La biométrie aiderait-elle **là où le CAN échoue**, c.-à-d. sur
le **Groupe 1** (conducteur non averti, qui ne réagit pas au volant mais dont le cœur peut réagir) ?

## Méthode

Pour chaque groupe d'awareness : **GroupKFold par conducteur** (anti-fuite) sur les conducteurs du
groupe ; PR-AUC de **CAN**, **BIO seule**, **CAN+BIO**. Biométrie **normalisée par conducteur**
(z-score sur le normal de chacun), car la fréquence cardiaque de repos varie d'une personne à
l'autre — sans ça, le modèle apprendrait l'individu, pas la réaction.

## Résultats

| Groupe | CAN | BIO seule | CAN+BIO | Δ (fusion − CAN) |
|---|---|---|---|---|
| 1 (non averti) | 0,480 ± 0,14 | 0,021 | **0,457 ± 0,08** | **−0,023** |
| 2 (averti) | 0,665 ± 0,26 | 0,016 | **0,705 ± 0,24** | **+0,040** |
| 3 (averti+protocole) | 0,899 ± 0,04 | 0,013 | 0,904 ± 0,04 | +0,005 |

## Verdict : la biométrie n'aide pas là où il le faudrait (résultat assumé)

1. **BIO seule ≈ hasard** partout (0,013-0,021), même conditionnée par groupe et normalisée par
   conducteur. La réponse HR/EDA est réelle (cf. EDA, +1,7 à +3,1 bpm) mais **trop faible, lente et
   bruitée** à l'échelle 1 s pour discriminer l'attaque.
2. **La fusion ne sauve PAS le Groupe 1** : Δ = **−0,023** (le cas le plus dur, où le CAN échoue).
   Ajouter 7 features biométriques bruitées **dégrade** même légèrement (sur-ajustement, peu de
   positifs). L'hypothèse A5 (« la biométrie comble le trou G1 ») est **infirmée**.
3. Le seul Δ positif est sur le **Groupe 2** (+0,040), cohérent avec l'EDA (réponse HR **maximale**
   pour le groupe averti-mais-non-instruit) — mais l'écart est **dans le bruit** (σ ±0,24) et donc
   non significatif.

**Conclusion** : l'originalité du dataset (biométrie + awareness) reste un **excellent axe
d'analyse** (elle *explique* le gradient de détectabilité, cf. P5+) mais **pas un levier de
modélisation** : elle n'apporte pas de pouvoir de détection, surtout pas sur le Groupe 1. On
**assume** ce négatif plutôt que de survendre la biométrie. La voie pour le Groupe 1 reste la
**signature d'injection** ([item 1](v2_injection_signature.md)) — mais elle est limitée par le
faible logging CAN0 de ce groupe.

> Caveat : peu de conducteurs par groupe (~16-17) → variance inter-fold élevée (jusqu'à ±0,26).
> Les Δ doivent être lus comme des tendances, pas des mesures fines.
