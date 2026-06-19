# Plan de realisation

> La methode appliquee a chaque brique, adaptee au nouveau dataset ORNL.

## La boucle pedagogique (a chaque etape)

```
THEORIE GENERALE -> THEORIE APPLIQUEE -> PRATIQUE (plusieurs chemins) -> EVALUATION -> CONCLUSION
```

Regle d'or : aucune brique n'est « juste du code » ; chacune = un concept
explique + une experience mesuree + un verdict assume.

## Les phases

| Phase | Objectif sur le dataset ORNL | Theorie | Statut |
|---|---|---|---|
| **P0 - Cadrage** | dataset multimodal, attaque, confondeurs, problematique | ML, types, workflow | OK |
| **P1 - EDA** | structure, label, confondeurs lieu/temps, biometrie | stats descriptives, confusion attaque/lieu | OK |
| **P2 - Pretraitement** | NaN, selection hors confondeurs (GPS exclu, time-drift teste) | data prep, fuite de donnees | OK |
| **P3 - Split & validation** | split PAR CONDUCTEUR (0 chevauchement) ; demos confondeurs/fuite | leakage, GroupKFold, leave-one-driver-out | OK |
| **P4 - Modelisation** | 3 chemins : A supervise (fait, GB 0,756), B anomalie, C deep | tous les algos | en cours |
| **P5 - Evaluation** | PR-AUC, precision/recall, tuning, base rate | metriques desequilibre, CV | a faire |
| **P6 - Robustesse & axes** | confondeurs (ablation), biometrie, identification conducteur | rigueur, multimodal | a faire |
| **P7 - Livrables** | demo, rapport, slides | recul critique | a faire |

## Les chemins de modelisation (P4)

| Chemin | Hypothese | Modeles |
|---|---|---|
| **A - Supervise** | avec labels, on classe (hors confondeurs) | LogReg, SVM, Random Forest, Gradient Boosting |
| **B - Anomalie** | apprendre le normal, signaler l'ecart | Isolation Forest, One-Class SVM, PCA |
| **C - Deep** | reseau sur les signaux (et sequences) | MLP, LSTM |

## Les points de vigilance (specifiques a ce dataset)

1. **Confondeur lieu** : exclure les ~320 colonnes GPS/inertie. Faire une
   **ablation** (avec vs sans GPS) pour montrer l'ampleur du piege.
2. **Confondeur temps** : controler la derive des signaux lents.
3. **Fuite conducteur** : split par conducteur, toujours.
4. **Desequilibre** : PR-AUC, precision/recall, jamais l'accuracy seule.
5. **Honnetete** : si la detection « propre » est faible, le documenter et
   l'expliquer plutot que de viser un score spurieux.

-> Details : [contexte.md](contexte.md) - [problematique.md](problematique.md) -
[eda_findings.md](eda_findings.md)
