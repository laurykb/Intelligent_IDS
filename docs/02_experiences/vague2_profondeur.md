# Vague 2 - Profondeur méthodologique (au-delà du sujet, sur la tâche du sujet)

> Deuxième vague d'auto-amélioration (cf. [autocritique.md](../04_conclusion/autocritique.md) §C).
> **Cadrage de scope** : les 7 étapes littérales du sujet sont remplies dès la
> [Vague 1](vague1_credibilite.md). La Vague 2 est de la **profondeur** sur la **même tâche**
> (détecter l'attaque dans les données CAN) : elle répond aux failles A1-A5 et **borne
> honnêtement** la portée du détecteur. État : **5/5 faits** (2026-06-19, PC GPU).

| # | Item | Répond à | Rapport au sujet | Résultat clé |
|---|---|---|---|---|
| 1 | Isoler la signature d'injection | A1 (la + grave) | [fait] cœur (données CAN) | **silence du bus CAN0** ~4 s après l'onset = injection, indép. de la réaction |
| 2 | Attaquant adaptatif / évasion | A3 | [partiel] évaluation+ | **fragile** : neutraliser 1-2 signaux → PR-AUC 0,74 → 0,07 |
| 3 | Fusion biométrie / awareness | A5 | [hors-cible] (pas du CAN) | biométrie **inutile** même par groupe ; ne sauve pas le G1 |
| 4 | Clustering/SVM-RBF/semi-sup/hybride | A4 | [partiel] « comparer algos »+ | rien ne bat les arbres ; **hybride sans gain** (champion absorbe déjà l'injection) |
| 5 | Taxonomie + injections synthétiques | A3/B2 | [hors-cible] au-delà du dataset | **mono-attaque** : fuzzing/masquerade/replay non détectés |

## Item 1 — la signature d'injection (avancée majeure, A1)

Le SPN 190 (régime moteur) existe sur **deux bus**. Pendant l'attaque, le bus **CAN0 se tait**
(~4 s après l'onset, marche d'escalier, couverture 67 % → 6,7 %), **tous groupes confondus**,
pendant que le bus principal reste à ~100 %. C'est une signature de **l'injection elle-même**
(l'ELD compromis sature/brouille CAN0), **distincte de la réaction du conducteur** — exactement
ce que A1 réclamait. Détecteur dédié (par véhicule) : PR-AUC 0,53 / 0,74 (G2) / 0,71 (G3).
**Corrige** [verification_dataset.md](../04_conclusion/verification_dataset.md) : l'injection
n'était pas « absente » mais présente comme **missingness** de canal. Détail :
[v2_injection_signature.md](v2_injection_signature.md).
**Limite** : ne sauve pas le Groupe 1 (CAN0 quasi jamais logué pour ce groupe → angle mort).

## Item 2 — fragilité adverse (A3)

Permutation importance : la feature n°1 est **le signal CAN0** (= la signature d'injection). Un
attaquant white-box qui **maquille 1 seul signal** fait chuter PR-AUC de **0,74 à 0,22** ; **2
signaux → 0,07**. Détecteur **brittle** : sa force est concentrée sur une poignée de signaux.
Pistes défense : redondance, cohérence physique inter-signaux, détection sous-seconde.
[v2_evasion.md](v2_evasion.md).

## Item 3 — biométrie : négatif assumé (A5)

BIO seule ≈ hasard (0,013-0,021) ; fusion CAN+BIO : **−0,02 sur le G1** (le cas dur), +0,04 sur
le G2 (dans le bruit). La biométrie reste un **axe d'analyse** (elle explique le gradient
d'awareness) mais **pas de modélisation**. [v2_biofusion.md](v2_biofusion.md).

## Item 4 — pas de free lunch méthodologique (A4)

SVM-RBF 0,212 (< arbres) ; clustering ARI 0,001 (n'isole pas l'attaque) ; self-training sans
gain (mais 25 % des labels suffisent) ; **hybride 0,645 < champion 0,695** (le supervisé absorbe
déjà l'injection). [v2_hybrid.md](v2_hybrid.md).

## Item 5 — détecteur mono-attaque (A3/B2)

Au seuil 1 % d'alertes : attaque réelle détectée à 65 %, mais **fuzzing 0,7 % / masquerade 0,9 % /
replay 1,1 %** (≈ non détectés ; seul le DoS/silence généralise à 15 %). Périmètre validé =
**l'attaque ELD du dataset**, pas « les intrusions CAN » en général. [v2_taxonomy.md](v2_taxonomy.md).

## Bilan de la Vague 2

**Ce qu'on a gagné** : (1) une **réponse concrète à A1** — on sait désormais montrer une signature
d'injection (silence CAN0) distincte de la réaction ; (2) une **carte honnête des limites** :
détecteur fragile à l'adversaire, mono-attaque, biométrie inutile, pas de gain hybride. Ces
négatifs **renforcent la crédibilité** (on ne survend pas) et **cadrent la portée** du livrable.

**Discipline de scope** : la Vague 2 approfondit la tâche du sujet sans en sortir (sauf items 3/5,
au-delà mais bornants). La **Vague 3** (autres datasets, RAG, déploiement) sort du scope et est en
partie infaisable hors-ligne → reléguée à une section **« Limites & perspectives »** du rapport,
non implémentée. **Prochaine étape : LIVRABLES** (démo, rapport .docx, slides .pptx).
