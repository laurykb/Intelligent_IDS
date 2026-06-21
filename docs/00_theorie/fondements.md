# Socle theorique (fondements mobilises dans le projet)

> Reference autonome des notions ML utilisees, expliquees avec l'intuition. Sert de support
> au rapport (chapitre 3) et a la soutenance. Ecrit pour etre lu independamment du code.

## 1. Qu'est-ce que le machine learning

La programmation classique applique des regles ecrites a la main (donnees + regles -> resultats).
Le machine learning inverse la fleche : donnees + resultats -> regles. On montre des exemples
(entrees et bonnes reponses) et l'algorithme apprend une regle qui generalise a des cas nouveaux.

Le risque central est le **sur-apprentissage** (overfitting) : memoriser le bruit du jeu
d'entrainement et echouer sur des donnees nouvelles. Son oppose est le **sous-apprentissage**
(underfitting) : un modele trop simple qui ne capte pas la structure. On controle ce compromis
biais-variance en evaluant **toujours sur des donnees non vues** - ici, des conducteurs non vus.

## 2. Les types d'apprentissage

| Type | Idee | Labels | Notre usage |
|---|---|---|---|
| Supervise | apprendre entree -> etiquette | oui | chemin A (champion) |
| Non supervise | trouver structure / anomalies | non | chemin B, clustering |
| Semi-supervise | peu d'etiquetes + beaucoup sans | partiel | self-training (Vague 2) |
| Deep / sequentiel | apprendre la representation | oui | MLP, GRU |

Le nerf de la guerre est le **label**. Ici la cible `cyberattack_active` est fournie, mais elle
**melange l'injection et la reaction** du conducteur : la qualite du label borne ce qu'on peut
prouver (cf. auto-critique A1).

## 3. Le workflow scikit-learn

Chargement -> split train/test -> preparation (imputation, normalisation) -> choix du modele ->
tuning des hyperparametres -> evaluation sur donnees jamais vues.

- **Normalisation** : les modeles a distance ou a gradient (SVM, regression, reseaux) exigent des
  features a la meme echelle ; les **arbres** (Random Forest, Gradient Boosting) n'en ont pas
  besoin (ils comparent des seuils). Le scaler s'ajuste **sur le train seul** (anti-fuite).
- **Hyperparametres** (fixes avant : profondeur, taux d'apprentissage) vs **parametres** (appris
  pendant). Le tuning cherche les hyperparametres par validation croisee, **jamais sur le test**.

## 4. Les algorithmes utilises (intuition)

- **Regression logistique** : frontiere lineaire + probabilite (sigmoide). Rapide, mais limitee
  aux separations lineaires.
- **SVM** : cherche la frontiere de marge maximale ; avec un noyau RBF, devient non lineaire mais
  couteuse a l'echelle (O(n^2)).
- **Random Forest** : moyenne de nombreux arbres sur des sous-echantillons - reduit la variance.
- **Gradient Boosting** : arbres construits en sequence, chacun corrigeant le precedent. Souvent
  le meilleur sur donnees **tabulaires** - c'est notre champion.
- **MLP / GRU** : reseaux denses / recurrents. Brillent sur la donnee brute haute dimension
  (image, texte, sequence longue) ; sur du tabulaire deja agrege, ils ne battent pas les arbres.
- **Detection d'anomalie** (Isolation Forest, One-Class SVM, PCA) : apprend le **normal**, signale
  l'ecart. Utile pour l'inconnu, mais ici l'attaque n'est pas un outlier global (rare != aberrant).

## 5. Evaluer un classifieur

Matrice de confusion : TN, FP (fausse alerte), FN (intrusion ratee), TP. Pour un IDS, le **FN**
est le cout le plus grave -> on privilegie le **rappel**, sans negliger la precision.

- **Precision** = TP/(TP+FP) : part de vraies parmi les alertes.
- **Rappel** = TP/(TP+FN) : part detectee parmi les attaques.
- **ROC-AUC** : separation tous seuils confondus - **optimiste** quand les positifs sont rares.
- **PR-AUC** (aire precision-rappel) : la metrique **honnete** en contexte desequilibre.

**La base-rate fallacy.** Quand l'attaque est rare (taux b), la precision depend du taux de
fausses alertes (FPR) :

    precision = b * R / (b * R + (1 - b) * FPR)

A 0,1 % d'attaque et 1 % de FPR, un detecteur a rappel 100 % n'a que ~9 % de precision : la
plupart des alertes sont fausses. **Un bon rappel ne suffit pas** ; il faut un FPR tres faible, et
on rapporte la PR-AUC. (Demonstration interactive dans la demo.)

## 6. Validation et fuite de donnees

On apprend sur le train, on juge sur le test. Si des donnees quasi identiques sont des deux cotes,
le test est contamine : c'est la **fuite de donnees** (data leakage), qui gonfle artificiellement
les scores.

- **Fuite par groupe** : ici chaque conducteur ne fait qu'un trajet. Un split aleatoire mettrait
  des fenetres du **meme conducteur** des deux cotes -> le modele reconnait la personne, pas
  l'attaque (PR-AUC 0,985 trompeur). D'ou le **split par conducteur** (GroupKFold) -> 0,632 honnete.
- **Confondeur** : une variable correlee a la fois a la cible et a un facteur parasite. Ici le
  **lieu** (GPS) et le **temps de roulage** sont des confondeurs : un modele qui les utilise
  detecte l'endroit/l'instant de l'attaque, pas l'attaque. On exclut le GPS et on surveille le temps.

Ces deux notions - fuite par groupe et confondeur - sont le **coeur methodologique** du projet :
sans elles, on publierait un faux succes.
