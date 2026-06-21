# Evaluation du projet (perspective encadrant / jury)

> Exercice : se mettre dans la peau de l'encadrant (R. Khatoun, securite des reseaux) qui
> evalue le projet integrateur. Note indicative, commentaires, axes d'amelioration. Ton
> volontairement exigeant et critique, comme en soutenance.

## Note globale indicative : 17 / 20

Detail par critere (ponderation indicative) :

| Critere | Note | Justification |
|---|---|---|
| Conformite au sujet (7 etapes + ROC + tuning) | 19/20 | toutes les etapes demandees sont faites, y compris les deux longtemps oubliees (courbe ROC, optimisation d'hyperparametres) |
| Rigueur methodologique | 19/20 | discipline anti-confondeurs et split par conducteur de niveau recherche ; reproductibilite (tests, versions, multi-graine, cross-plateforme) |
| Originalite / valeur ajoutee | 17/20 | la signature d'injection (silence CAN0) et le gradient d'awareness sont de vraies trouvailles |
| Honnetete et esprit critique | 19/20 | resultats negatifs assumes (anomalie, deep, biometrie, mono-attaque, evasion) ; aucune survente |
| Livrables (demo, rapport, slides) | 17/20 | demo interactive vivante (detection animee, attaquant pilote en direct, base-rate fallacy) ; rapport et slides complets |
| Portee et generalisation | 13/20 | un seul dataset, une seule attaque, detecteur evadable : la limite assumee mais reelle |

## Ce que je dirais en soutenance (points forts)

1. **Le reflexe methodologique est excellent.** Splitter par conducteur, exclure le GPS, choisir
   la PR-AUC : ces decisions sont prises **des l'exploration**, pas apres coup. Beaucoup d'etudiants
   se seraient arretes au 0,985 trompeur et auraient affiche un faux succes. Refuser ce score et
   descendre a 0,632 honnete, c'est exactement le reflexe d'un ingenieur securite.
2. **La decouverte du silence CAN0 est remarquable.** Aller chercher l'incoherence inter-bus du
   SPN 190, trouver que le bus se tait ~4 s apres l'onset, et separer ainsi l'injection de la
   reaction du conducteur : c'est une investigation qui distingue un vrai travail d'une simple
   application de recettes.
3. **L'honnetete est exemplaire.** Le projet nomme ses limites (cible conflee, mono-attaque,
   evasion en 1-2 signaux, biometrie inutile) au lieu de les cacher. C'est ce qui rend les
   resultats positifs credibles.
4. **Les livrables tiennent la soutenance.** La demo ou l'on **pilote l'attaquant en direct** et
   ou l'on voit le rappel s'effondrer est pedagogiquement forte ; la base-rate fallacy interactive
   montre une maturite metrologique rare a ce niveau.

## Ce que je critiquerais (points faibles / a ameliorer)

1. **La generalisation n'est pas prouvee.** Un seul dataset, un seul vehicule, une seule attaque.
   Rien ne dit que le detecteur tient sur un autre camion ou une autre injection. C'est la limite
   la plus serieuse pour une pretention operationnelle. -> *Tester sur ROAD / Car-Hacking.*
2. **Le detecteur est fragile.** Evadable en neutralisant 1 a 2 signaux : honnete de le montrer,
   mais cela borne fortement la valeur en conditions adverses. La defense en profondeur reste a
   construire (l'IDS hybride teste n'apporte rien car le champion absorbe deja la signature - il
   faudrait une couche reellement **orthogonale**, p. ex. coherence physique inter-signaux ou
   detection au niveau trame). -> *Vraie seconde couche de detection.*
3. **La cible reste partiellement conflee.** On detecte l'injection ET la reaction ; la separation
   est entamee (silence CAN0) mais le label ne distingue pas les deux, et le Groupe 1 reste un
   angle mort. -> *Donnees haute-resolution (signature sous-seconde) pour isoler l'injection pure.*
4. **Pas de comparaison chiffree a l'etat de l'art.** Le papier source ORNL est cite, mais aucune
   mise en regard quantitative avec les IDS CAN de reference (CIDS, CANet). -> *Positionnement SOTA.*
5. **Le projet foisonne.** La profondeur est reelle mais la narration se disperse (vagues, sous-
   analyses). Un socle theorique autonome et un fil unique resserre aideraient la lecture. -> *Fil
   conducteur plus lineaire ; section theorie dediee.*

## Questions que je poserais au candidat

- Que devient le detecteur sur un autre vehicule ? Avez-vous une preuve, ou une intuition chiffree ?
- Une injection **furtive** qui ne sature pas le bus CAN0 : comment la detecteriez-vous ?
- Le seuil haute-precision laisse passer la moitie des secondes d'attaque : est-ce acceptable pour
  un IDS, et pourquoi (argument episode) ?
- La biometrie ne sert a rien ici : est-ce une propriete du dataset, de l'echelle 1 s, ou de la
  methode ? Comment le trancher ?

## Verdict

Travail **solide, rigoureux et honnete**, au-dessus des attentes sur la methodologie et l'esprit
critique, avec une vraie trouvaille (signature d'injection). Il est **bride par la nature du jeu de
donnees** (un echantillon, une attaque) plus que par la competence : c'est ce qui separe le 17 d'un
19. Les axes d'amelioration sont clairs et tous hors du perimetre strict du sujet (generalisation,
defense en profondeur, donnees haute-resolution).
