# Problematique et objectifs

## 1. La question centrale

> **Peut-on detecter la cyberattaque a partir du comportement du vehicule (et du
> conducteur), de facon HONNETE - c'est-a-dire sans tricher avec le lieu ni le
> moment de l'attaque ?**

C'est un probleme de detection d'intrusion (classification binaire de
`cyberattack_active`). Mais sa difficulte n'est pas la ou on l'attend.

## 2. Le piege central : les confondeurs

L'EDA (voir [eda_findings.md](eda_findings.md)) revele que l'attaque survient
**toujours au meme endroit** et a un **moment quasi fixe** du trajet. Cela cree
deux confondeurs qui rendraient un modele naif trompeur :

| Confondeur | Mecanisme | Consequence |
|---|---|---|
| **Lieu** | l'attaque est ~7 a 44x plus concentree geographiquement que le reste du trajet | un modele utilisant le GPS detecte **l'endroit**, pas l'attaque |
| **Temps** | l'attaque arrive a ~60 % du trajet | les signaux qui derivent (temperatures d'echappement, fluides) corrigent avec **l'heure**, pas avec l'attaque |

> **Pourquoi c'est grave.** Un modele entraine sur les 816 features atteindrait
> une accuracy quasi parfaite - mais en faisant du **geofencing** (alerter quand
> le camion est a tel endroit) et de l'**horloge** (alerter a la 60e minute). Ce
> ne serait PAS un detecteur d'intrusion : il echouerait des que l'attaque
> changerait de lieu ou d'heure. C'est l'equivalent, en pire, de la fuite de
> label.

### La discipline qu'on s'impose
1. **Exclure les features GPS / inertie / trajectoire** (les ~320 colonnes VBOX).
2. **Se mefier des signaux CAN a derive lente** (temperatures) qui encodent le
   temps de roulage, donc l'instant de l'attaque.
3. Poser la vraie question : **une fois les confondeurs retires, reste-t-il une
   signature CAN/biometrique honnete de l'attaque ?** (L'EDA suggere que non, ou
   peu - ce qui est en soi un resultat important.)

## 3. Le second piege : la fuite par le conducteur

Il y a **50 conducteurs**. Si on melange les lignes au hasard entre train et
test, le **meme conducteur** se retrouve des deux cotes : le modele peut alors
apprendre les habitudes d'un conducteur plutot que l'attaque.

> **Regle imposee : split PAR CONDUCTEUR** (les conducteurs du test ne sont jamais
> vus a l'entrainement) - via une validation croisee groupee (leave-one-driver-
> out ou GroupKFold). C'est la seule facon de mesurer une vraie generalisation.

## 4. Le troisieme enjeu : le desequilibre

L'attaque ne fait que **1,46 %** des fenetres. La base-rate fallacy n'est plus
hypothetique : avec 98,5 % de normal, l'accuracy est inutile. On rapportera la
**PR-AUC** et le couple **precision/recall**.

## 5. Objectifs (alignes sur la consigne)

1. **Explorer** le dataset et caracteriser normal vs attaque ([fait](eda_findings.md)).
2. **Pretraiter** : gestion des NaN (28 % manquants), normalisation, selection de
   features **hors confondeurs**.
3. **Comparer** plusieurs algorithmes (arbres, SVM, reseaux de neurones...).
4. **Decouper** en train/test **par conducteur** (anti-fuite).
5. **Entrainer** sur normal et attaque.
6. **Evaluer** (precision, rappel, PR-AUC, ROC) et **optimiser** les hyperparametres.

### Axe secondaire (le dataset le permet)
- **Identification du conducteur** (classifier `Subject` parmi 50) - tache
  biometrique / d'authentification.
- **Reponse humaine a l'attaque** (la biometrie reagit-elle, selon le groupe
  d'awareness ?).

## 6. Criteres de reussite

- Un detecteur **honnete** (sans confondeurs, split par conducteur) dont on
  mesure lucidement le **recall** et la **PR-AUC** a base rate realiste.
- Une comparaison rigoureuse d'au moins 3 modeles.
- Une conclusion **assumee** : si l'attaque n'est pas detectable proprement, le
  dire et l'expliquer vaut mieux qu'un score spurieux.

-> Suite : [plan.md](plan.md)
