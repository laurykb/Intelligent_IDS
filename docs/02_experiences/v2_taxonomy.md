# Vague 2 - Item 5 : taxonomie de menaces + injections synthétiques (réponse à A3/B2)

> Code : [`notebooks/11_threat_taxonomy.py`](../../notebooks/11_threat_taxonomy.py) -
> Résultats : [`docs/03_evaluation/results_taxonomy.json`](../03_evaluation/results_taxonomy.json) -
> Figure : `docs/assets/v2_taxonomy.png`. Répond à **B2** (modèle de menace étroit) / **A3**.

## Question

Le dataset ne contient **qu'une seule** attaque (mise à zéro tachymètre / *instrument cluster*).
Notre IDS est donc, de fait, un **détecteur mono-attaque**. Généralise-t-il à d'**autres** types
d'attaques CAN J1939 ? On le teste avec des attaques **synthétiques** appliquées à des fenêtres
**normales held-out** (conducteurs non vus), et on mesure le taux de détection au **seuil
haute-précision** du champion (calibré à ~1 % de fausses alertes sur le normal réel).

## Taxonomie testée et résultats

| Type d'attaque (synthétique sauf ref.) | Description | Détection @1 % |
|---|---|---|
| **Attaque RÉELLE (référence)** | la vraie attaque du dataset | **65,1 %** |
| DoS / silence de bus | on coupe le bus CAN0 (NaN) — mime l'item 1 | **15,3 %** |
| Fuzzing (20 % des signaux) | valeurs aléatoires hors-plage | 0,7 % |
| Masquerade furtif | on ne décale QUE le régime moteur (−200 rpm) | 0,9 % |
| Replay (autre fenêtre) | on rejoue le CAN d'une autre fenêtre normale | 1,1 % |

(Taux de fausses alertes du seuil : 1,0 % — donc 0,7-1,1 % ≈ **non détecté**.)

## Verdict : détecteur mono-attaque (limite assumée, B2)

1. **Le détecteur ne généralise PAS** aux attaques qu'il n'a jamais vues : fuzzing, masquerade
   furtif et replay passent **sous le radar** (détection ≈ taux de fausses alertes). Il n'a appris
   que la **signature spécifique** de l'attaque du dataset (réaction + silence CAN0).
2. **Seul le DoS/silence de bus** est partiellement attrapé (15 %), et c'est **cohérent** : il
   ressemble à la signature d'injection réelle (item 1, silence CAN0) que le modèle exploite déjà.
3. **Le masquerade furtif (0,9 %)** rejoint l'item 2 (évasion) : une perturbation discrète et
   ciblée du seul régime moteur **échappe** au détecteur.

**Conséquence (B2)** : pour un IDS réellement déployable, il faut **élargir le modèle de menace** —
soit un jeu d'attaques (DoS/bus-off, fuzzing, replay, masquerade) à l'entraînement, soit un
**second étage par anomalie/cohérence** pour l'inconnu. En l'état, le périmètre validé est
**l'attaque ELD du dataset**, pas « les intrusions CAN » en général. On l'**assume** explicitement
dans les conclusions et le rapport plutôt que de survendre la portée.
