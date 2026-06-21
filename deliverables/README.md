# Livrables — IDS Intelligent

Trois livrables, tous générés/pilotés en Python :

| Livrable | Fichier | Généré par |
|---|---|---|
| **Démo interactive** | `app.py` (Streamlit) | — |
| **Rapport** | `Rapport_IDS_Intelligent.docx` | `python build_report.py` (racine) |
| **Slides** | `Presentation_IDS_Intelligent.pptx` | `python build_slides.py` (racine) |

## Lancer la démo

```bash
# 1. dépendances (dans le venv du projet)
pip install -r deliverables/requirements.txt

# 2. (re)générer si besoin :
python deliverables/build_demo_data.py   # -> demo_data.json (traces, courbes, métriques réelles)
python artifacts/build_artifacts.py      # -> ids_model.joblib + demo_samples.npz (inférence LIVE)

# 3. lancer
streamlit run deliverables/app.py        # http://localhost:8501
```

## Principe : un banc d'essai, pas un diaporama

La démo n'est **pas** une redite des slides. C'est un **poste de commande** : chaque page laisse
l'utilisateur **agir** et le **vrai modèle / les vraies données** réagissent en direct. Le narratif
(contexte, EDA, comparaison de modèles…) est dans le **rapport et les slides** — la démo, elle, sert
à **manipuler** et **expérimenter**.

## Contenu de la démo (5 postes interactifs, menu de gauche)

1. **Console de détection (live)** — choisissez un conducteur jamais vu, lancez la lecture animée :
   l'attaque se déroule, le détecteur score en direct, le bus CAN0 se tait sous vos yeux. Seuil réglable.
2. **Vous pilotez l'attaquant** — vous êtes l'adversaire : neutralisez des signaux, le **vrai modèle**
   re-score et le rappel s'effondre (jauge live). L'évasion de la Vague 2, en main.
3. **Bac à sable : créez une attaque** — choisissez un type (DoS, fuzzing, masquerade, replay) et une
   intensité ; on l'injecte sur du trafic normal et le vrai modèle juge → vous **découvrez les angles
   morts** (mono-attaque) vous-même.
4. **Le piège du data scientist** — choisissez votre split et vos features ; l'app révèle si vous vous
   êtes **fait piéger** (fuite par conducteur 0,985, confondeur GPS 0,835) ou non (0,632 honnête).
5. **Réglez l'IDS pour le déploiement** — réglez seuil + taux d'attaque réel et lisez le **coût
   opérationnel** (précision réelle, fausses alertes, base-rate fallacy) en direct.

## Notes

- **Vraies données** : `demo_data.json` (prédictions hors-fold du champion via `oof_scores.npz`,
  courbes ROC/PR, traces des 50 conducteurs) ; `artifacts/` (modèle entraîné pour l'inférence live
  de la page « attaquant »). Aucun réentraînement à l'ouverture → démo rapide et portable.
- Lancer avec `python -m streamlit run ...` si le script `streamlit` du PATH est obsolète.
