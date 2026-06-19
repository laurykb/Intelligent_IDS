# Références & positionnement scientifique

## Le papier source du dataset (à citer en priorité)

> **Lanigan, T. F., Biggs, T., Gallegos, E. E., Daily, J., Reid, E. J., Powers, S.**
> *« Impact of Cyber Threat Awareness on Driver Response to an Unexpected Vehicle
> Cyberattack »*, **Journal of Transportation Security**, 2025.
> DOI : [10.1007/s12198-025-00303-0](https://link.springer.com/article/10.1007/s12198-025-00303-0)
> · PDF libre : [OSTI 3002667](https://www.osti.gov/servlets/purl/3002667)
> · Dataset : [OSTI 2513388](https://www.osti.gov/biblio/2513388) (ORNL, 2025).

Équipe **ORNL + Colorado State University (groupe de Jeremy Daily**, cybersécurité poids
lourds — le même lignage que l'attaque ELD du projet précédent, avis CISA).

### Ce que le papier établit (et qui VALIDE notre travail)

| Constat du papier | Notre résultat indépendant (ML) |
|---|---|
| Groupes = **Control** (non averti) / **Aware** / **Aware + Protocol** | = nos Groupes **1 / 2 / 3** (mapping exact) |
| **Temps de réaction moyen : 30,3 s / 16,1 s / 7,5 s** (Control / Aware / Protocol) | **Gradient de détectabilité** LODO médiane **0,74 / 0,92 / 0,96** (même ordre monotone) |
| *« Unaware group more likely to continue driving and not pull over »* | Groupe 1 sans signature de réaction -> détection intra-groupe **0,46** |
| **Aware + Protocol : 100 % de taux d'arrêt** (se garent tous) | Groupe 3 réaction uniforme (régime chute d=-0,48) -> détection **0,90**, transfert **0,93** |
| Attaque = **instrument cluster** : aiguilles tach/compteur **mises à zéro** (l'afficheur) | Vérifié : le spoof **n'est pas** dans les diffusions ECU loggées -> on détecte la réaction, pas l'injection |
| *« response may have been influenced by not even noticing the attack »* (Control) | Conducteur non averti = indétectable : la limite fondamentale qu'on a posée (A1) |
| **Même lieu** d'attaque pour tous les participants | Notre **confondeur de lieu** (GPS exclu) — confirmé par les auteurs |

### Lecture : notre contribution vs la leur

- Le papier source traite la **réponse comportementale** du conducteur (temps de
  réaction, taux d'arrêt). Il **ne construit pas de détecteur d'intrusion**.
- Notre apport est **orthogonal et complémentaire** : on montre, par le ML, que la
  détectabilité de l'attaque **suit le même gradient d'awareness** — preuve quantitative,
  côté signal CAN, que *ce que détecte un IDS ici est la réaction, pas l'injection*.
- **Point notable** : notre **latence de détection** (~4 s médiane) est plus courte que
  les temps de réaction humains (7,5 à 30 s). Le modèle « flague » la fenêtre d'attaque
  avant la manœuvre d'arrêt -> il s'appuie aussi sur le **contexte** (lieu fixe, régime au
  segment d'attaque), pas seulement sur l'arrêt. À garder à l'esprit (confondeur de lieu).
- Aucune PR-AUC de **détection** publiée sur ce dataset (le cadrage IDS semble inédit) ->
  pas de SOTA direct à comparer ; on se compare donc au **hasard (0,015)** et entre nos
  chemins.

## Littérature CAN IDS à mobiliser (Vagues 2/3)

- **Cho & Shin, CIDS (USENIX Security 2016)** — *clock-skew* par ECU : détecterait
  l'**ELD usurpateur** indépendamment du payload **et du conducteur** -> réponse directe à
  notre A1 (détecter l'injection, pas la réaction).
- **Hanselmann et al., CANet (IEEE Access 2020)** — auto-encodeur par signal.
- **Taylor et al. (DSAA 2016)** — LSTM sur séquences CAN (notre chemin C).
- **Verma et al., ROAD (ORNL 2022/2024)** — attaques masquerade furtives : banc d'essai
  pour l'attaquant adaptatif et la généralisation.
- **Murvay & Groza** — failles de SAE J1939 (notre protocole).
