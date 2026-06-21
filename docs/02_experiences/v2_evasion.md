# Vague 2 - Item 2 : attaquant adaptatif / évasion (réponse à A3)

> Code : [`notebooks/08_evasion.ipynb`](../../notebooks/08_evasion.ipynb) -
> Résultats : [`docs/03_evaluation/results_evasion.json`](../03_evaluation/results_evasion.json) -
> Figure : `docs/assets/v2_evasion.png`. Répond à **A3** (robustesse / adversarial).

## Question (modèle de menace)

Le sujet précise que l'ELD compromis peut écrire des messages CAN **arbitraires**. Un attaquant
**white-box** (qui connaît le détecteur) peut donc **maquiller** les signaux que le modèle
surveille : faire en sorte que les vraies diffusions ECU **paraissent normales**. Combien de
signaux doit-il contrôler pour évader le champion ?

## Méthode

On classe les 337 features CAN par **permutation importance** sur le champion (HistGB,
GroupKFold conducteur). On simule l'évasion : pendant les fenêtres d'**attaque**, on remplace les
**top-k** signaux par leur **médiane normale** (du train), puis on re-score hors-fold. On trace
PR-AUC(champion) en fonction de **k** = nombre de signaux maquillés.

## Résultat 1 — la détection repose sur très peu de signaux

| Rang | Feature | Importance |
|---|---|---|
| 1 | **`mean.190.Engine.Speed.CAN0`** | **+1,58** |
| 2 | `max.3242 ...DPF Intake Temperature` | +1,02 |
| 3 | `mean.1761 ...DEF Tank Volume` | +0,22 |
| 4 | `min.3242 ...DPF Intake Temperature` | +0,20 |
| … | (longue traîne, chacun < 0,1) | … |

**La feature n°1 est le signal du bus CAN0** — exactement la signature d'injection de
l'[item 1](v2_injection_signature.md) (sa valeur est *manquante* pendant l'attaque, NaN géré par
HistGB). **Le champion exploitait donc déjà, sans qu'on l'ait nommé, le silence du bus CAN0.**

## Résultat 2 — fragilité à un attaquant ciblé

| k signaux maquillés | PR-AUC global | G1 | G2 | G3 |
|---|---|---|---|---|
| 0 (aucun) | **0,738** | 0,499 | 0,846 | 0,927 |
| **1** | **0,221** | 0,128 | 0,335 | 0,466 |
| 2 | 0,065 | 0,045 | 0,111 | 0,092 |
| 5 | 0,036 | — | — | — |
| ≥ 13 | ~0,013 (≈ hasard) | — | — | — |

**Neutraliser un seul signal** (le CAN0) fait s'effondrer la PR-AUC de **0,74 à 0,22** ; **deux
signaux** la mettent quasi au niveau du hasard. Le détecteur est donc **très fragile à un
attaquant adaptatif** : sa performance est concentrée sur une poignée de features.

## Verdict (A3)

1. **Brittleness confirmée** : un attaquant white-box qui maquille **1-2 signaux** évade le
   champion. C'est la rançon d'un modèle dont l'importance est **ultra-concentrée** (Gini très
   inégal). Pour un IDS déployable, c'est une faiblesse de sécurité réelle.
2. **Lien avec l'item 1** : le signal le plus précieux **et** le plus facile à neutraliser est le
   **silence du bus CAN0**. Un attaquant « propre » qui **n'a pas besoin de saturer CAN0** (ou qui
   y réinjecte un régime plausible) défait à la fois l'item 1 et le champion. La signature
   d'injection est forte **mais pas infalsifiable**.
3. **Défense (pistes Vague 2/3)** : (a) **redondance** — forcer le modèle à s'appuyer sur plus de
   signaux (régularisation, ensembles, drop de la feature dominante) pour augmenter le coût
   d'évasion ; (b) **cohérence inter-signaux physique** (un régime moteur doit être cohérent avec
   vitesse/couple/consommation : maquiller *tout* de façon cohérente est bien plus coûteux) ;
   (c) **détection au niveau trame** (sous-seconde), hors de portée de l'agrégation 1 s actuelle.

Cette fragilité **n'invalide pas** les résultats précédents (qui mesurent la détection face à
l'attaque *réelle* du dataset, non adaptative) ; elle **borne** leur portée : bons contre cette
attaque, fragiles contre un adversaire qui connaît le modèle.
