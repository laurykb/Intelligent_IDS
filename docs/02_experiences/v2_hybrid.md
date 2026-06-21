# Vague 2 - Item 4 : clustering, SVM-RBF, semi-supervisé, IDS hybride (réponse à A4)

> Code : [`notebooks/10_clustering_hybrid.py`](../../notebooks/10_clustering_hybrid.py) -
> Résultats : [`docs/03_evaluation/results_hybrid.json`](../03_evaluation/results_hybrid.json) -
> Figure : `docs/assets/v2_hybrid.png`. Répond à **A4** (angles non explorés).
> Split : driver_holdout (12 conducteurs test, anti-fuite) ; PR-AUC sur le test.

## 1. SVM à noyau RBF (jamais testé — seul le linéaire l'était)

Sur sous-échantillon (15 000 lignes, le RBF est en O(n²)) : **PR-AUC 0,212**. Le noyau RBF
**ne rattrape pas** les arbres (champion 0,695 sur ce même split). Confirme P4-A : sur ce
tabulaire déséquilibré, **les arbres boostés dominent** ; ni le SVM linéaire ni le RBF n'approchent.

## 2. Clustering non supervisé — l'attaque n'est pas isolable sans labels

| Méthode | PR-AUC (via taux d'attaque par cluster) | ARI vs attaque | ARI vs conducteur |
|---|---|---|---|
| K-means (20) | 0,038 | **0,001** | 0,055 |
| GMM (10, diag) | 0,029 | — | — |

Les clusters **ne s'alignent pas du tout** sur l'attaque (ARI ≈ 0) ni vraiment sur le conducteur
(0,055) : la structure non supervisée du CAN capte des **régimes de conduite**, pas l'attaque.
Cohérent avec l'échec de la détection d'anomalie (P4-B, ~0,02) : **rare ≠ aberrant**, il faut les
labels.

## 3. Semi-supervisé (self-training) — l'unlabeled n'aide pas, mais haute efficacité-label

| % de labels | Supervisé | Self-training |
|---|---|---|
| 5 % | 0,548 | 0,543 |
| 10 % | 0,627 | 0,634 |
| 25 % | **0,695** | 0,677 |
| 100 % | 0,695 | 0,695 |

Deux enseignements : (a) le **self-training n'apporte rien** (≤ supervisé, dans le bruit) — les
données non étiquetées n'ajoutent pas de signal exploitable ; (b) **forte efficacité-label** :
**25 % des labels suffisent** à atteindre la performance pleine (0,695). Utile en pratique
(annotation coûteuse).

## 4. IDS hybride : champion (réaction) ∪ signature d'injection (silence CAN0)

| Détecteur | PR-AUC | Précision @1 % alertes | Rappel @1 % |
|---|---|---|---|
| Champion (supervisé) | **0,695** | **0,78** | 0,58 |
| Injection (silence CAN0, item 1) | 0,490 | 0,61 | 0,50 |
| **Hybride (union max)** | 0,645 | 0,66 | **0,62** |

**Résultat honnête** : l'union **n'améliore pas** la PR-AUC (0,645 < 0,695). Raison déjà établie
en [item 2](v2_evasion.md) : **le champion exploite déjà** la signature d'injection (le signal CAN0
est sa feature n°1), donc le détecteur d'injection explicite est **largement redondant** — la fusion
ajoute surtout ses fausses alertes. Elle **augmente toutefois le rappel** au point d'opération
(0,62 vs 0,58), au prix de la précision (0,66 vs 0,78) : un arbitrage, pas un gain net.

## Verdict (A4)

Les quatre angles « manquants » sont désormais couverts — et tous **confirment le champion** :
le RBF ne bat pas les arbres, le non-supervisé n'isole pas l'attaque, le semi-supervisé n'ajoute
rien (mais 25 % des labels suffisent), et l'**hybride n'apporte pas de gain** car le supervisé
**absorbe déjà** la signature d'injection. Conclusion : pas de free lunch méthodologique au-delà du
Gradient Boosting ; le levier restant est ailleurs (modèle de menace élargi, item 5 ; trame
sous-seconde).
