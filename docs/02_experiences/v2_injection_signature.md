# Vague 2 - Item 1 : isoler la signature d'injection (réponse à A1)

> Code : [`notebooks/07_injection_signature.py`](../../notebooks/07_injection_signature.py) -
> Résultats : [`docs/03_evaluation/results_injection.json`](../03_evaluation/results_injection.json) -
> Figure : `docs/assets/v2_injection_signature.png`.
> Répond à la faille **A1** ([autocritique.md](../04_conclusion/autocritique.md)) : *« on détecte
> la réaction du conducteur, pas l'injection »*.

## Question

A1 (la faille la plus grave) dit que la cible `cyberattack_active` **mélange** l'injection CAN
et la **réaction comportementale** du conducteur — et que la vérification dataset avait conclu
que le spoof (tachymètre → 0) était **absent des features** (les valeurs de régime ne tombent
pas à 0). Existe-t-il malgré tout une signature de **l'injection elle-même**, indépendante de
la réaction ?

## Matériau : le SPN 190 sur deux bus

Le régime moteur (SPN 190) est le **seul** signal dupliqué sur **deux canaux** :
`*.190.Engine.Speed` (bus principal) et `*.190.Engine.Speed.CAN0`. C'est exactement le
matériau « incohérence inter-bus » évoqué par A1/B3. On compare les deux bus, attaque vs normal.

## Résultat 1 — pendant l'attaque, le bus CAN0 se TAIT (le principal reste)

La signature n'est pas dans les **valeurs** mais dans la **disponibilité** du bus :

| Groupe | CAN0 normal | CAN0 **attaque** | Bus principal (normal → attaque) |
|---|---|---|---|
| 1 (non averti) | 26,3 % | **2,1 %** | 87,7 % → 99,7 % |
| 2 (averti) | 84,2 % | **8,5 %** | 89,8 % → 100 % |
| 3 (averti+protocole) | 91,1 % | **12,2 %** | 91,3 % → 100 % |
| **Global** | 67,0 % | **6,7 %** | 89,6 % → 99,9 % |

Le bus CAN0 (qui diffuse le régime) **disparaît à ~90 %** pendant l'attaque, **dans tous les
groupes**, tandis que le bus principal **monte à ~100 %**. Mécanisme plausible : l'ELD compromis
**sature/brouille CAN0** (écritures arbitraires, cf. sujet), noyant les vraies diffusions ECU.

## Résultat 2 — l'onset est net et aligné sur l'injection (pas un confondeur temps)

Moyenné sur les **51 épisodes** d'attaque, la présence de CAN0 autour de l'onset :

- t = −10 s … +3 s : **~73 %** (niveau de base)
- **t = +4 s : chute à 0 %**, et reste à 0-2 % jusqu'à la fin

C'est une **marche d'escalier** alignée sur l'attaque (~4 s de latence), **pas** une dérive lente.
Le confondeur temps/lieu est donc écarté : c'est l'**événement d'injection** qui coupe le bus.
Figure : `docs/assets/v2_injection_signature.png` (panneau gauche).

## Résultat 3 — détecteur de silence CAN0 (signature d'injection seule)

Comme la couverture CAN0 **varie énormément par conducteur** (G1 26 % vs G3 91 % en normal),
l'absence brute n'est pas spécifique (CAN0 est aussi absent 22 % du temps en normal). On normalise
par la **baseline propre à chaque véhicule** (IDS calibré par vehicule, **sans** labels d'attaque) :
score = chute de présence CAN0 vs baseline du conducteur.

| Groupe | PR-AUC (silence CAN0) | Précision @0,4 | Rappel @0,4 | *(rappel) détection-réaction (champion CAN)* |
|---|---|---|---|---|
| Global | **0,531** | 0,68 | 0,57 | 0,735 |
| 1 | 0,268 | 0,56 | 0,29 | **0,46 (intra-G1)** |
| 2 | **0,741** | 0,76 | 0,78 | — |
| 3 | **0,713** | 0,68 | 0,79 | 0,90 |

**37/50 conducteurs** montrent la chute CAN0 > 20 pts pendant l'attaque (G2 : 15/16, G3 : 17/17).
Avec **un seul signal de missingness**, on atteint PR-AUC 0,53 global (35× le hasard).

## Verdict : A1 partiellement RÉSOLU (et une correction)

1. **On a isolé une signature de l'injection pure**, distincte de la réaction : le silence du bus
   CAN0 est un effet **direct de l'injection** (l'ELD brouille le bus), présent **même quand le
   conducteur ne réagit pas**. Pour les 37/50 véhicules dont CAN0 est loggé, c'est un marqueur
   d'intrusion propre. **Réponse concrète à A1.**
2. **Correction de [verification_dataset.md](../04_conclusion/verification_dataset.md)** : on avait
   écrit que le spoof était « absent des features » — c'était vrai *en valeur* mais **faux en
   disponibilité** : le spoof est présent comme **silence de bus** (missingness), pas comme régime
   à 0. Le logger a perdu les diffusions CAN0 pendant que l'injection saturait le canal.
3. **Limite honnête (Groupe 1)** : le silence CAN0 ne sauve **pas** la détection du Groupe 1
   (PR-AUC 0,27) — mais pour une raison **différente** de la détection-réaction : la baseline CAN0
   du G1 est **médiane 0 %** (le bus n'était quasi jamais logué, cf. « G1 CAN bas débit »). Il n'y
   a donc **rien à faire taire**. Pour le cas le plus dur (conducteur non averti), **ni** la réaction
   **ni** le silence de bus ne sont disponibles — double angle mort, à assumer.

**Apport méthodologique** : ce signal définit un **axe IDS complémentaire** — un détecteur
**par-véhicule** (anomalie de disponibilité de bus) à côté du modèle supervisé **inter-conducteur**.
Les 4 colonnes `190.*.CAN0` étant déjà dans le set CAN (NaN gérés par HistGB), le champion
**exploite probablement déjà en partie** cette missingness — piste : la quantifier (feature
explicite « silence CAN0 » vs ablation). Ouvre aussi l'item *taxonomie/injections synthétiques*.
