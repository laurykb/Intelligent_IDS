"""
IDS Intelligent - Demo INTERACTIVE (Streamlit) : un poste de commande, pas un diaporama.
Chaque page = l'utilisateur agit, le vrai modele / les vraies donnees reagissent en direct.

Lancer :  streamlit run deliverables/app.py
Donnees  :  deliverables/demo_data.json (traces held-out) + artifacts/ (modele + echantillons).
"""
import os, json, time
import numpy as np
import joblib
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.metrics import average_precision_score

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLUE, RED, GREEN, GRAY, PURPLE, AMBER = "#2980b9", "#c0392b", "#16a085", "#7f8c8d", "#8e44ad", "#e67e22"

st.set_page_config(page_title="IDS Intelligent - console", layout="wide")


@st.cache_data
def load_data():
    return json.load(open(os.path.join(ROOT, "deliverables", "demo_data.json"), encoding="utf-8"))


@st.cache_resource
def load_model():
    return joblib.load(os.path.join(ROOT, "artifacts", "ids_model.joblib"))


@st.cache_data
def load_samples():
    z = np.load(os.path.join(ROOT, "artifacts", "demo_samples.npz"))
    return {k: z[k] for k in z.files}


def show(fig):
    st.plotly_chart(fig, width="stretch")


def gauge(value, label, good_high=True):
    col = (GREEN if value >= 50 else RED) if good_high else (RED if value >= 50 else GREEN)
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value, number={"suffix": " %"}, title={"text": label},
        gauge={"axis": {"range": [0, 100]}, "bar": {"color": col},
               "steps": [{"range": [0, 50], "color": "#fbecec"}, {"range": [50, 100], "color": "#eafaf1"}]}))
    fig.update_layout(height=260, margin=dict(t=50, b=10))
    return fig


D = load_data()
ATTACK_RATE = D["meta"]["attack_rate"]
AWARE = {1: "non averti", 2: "averti", 3: "averti + consigne de se garer"}


def driver_label(d):
    g, s = d.split("_S")
    return f"Groupe {g} ({AWARE[int(g)]}) · conducteur {s}"

st.sidebar.title("IDS Intelligent — console")
st.sidebar.caption("Démo **interactive** : ici on **manipule** le détecteur et on voit le vrai "
                   "modèle réagir en direct. Ce n'est pas le diaporama — c'est le banc d'essai.")
PAGES = [
    "1 · Voir l'IDS détecter (live)",
    "2 · L'IDS est-il robuste ? (attaquant)",
    "3 · Détecte-t-il l'inconnu ? (bac à sable)",
    "4 · Mon score est-il honnête ? (le piège)",
    "5 · Combien de fausses alertes ? (déploiement)",
]
page = st.sidebar.radio("Postes", PAGES, label_visibility="collapsed", key="nav")
st.sidebar.markdown("---")
st.sidebar.caption("Modèle réel : Gradient Boosting / CAN (PR-AUC 0,798). Données : prédictions "
                   "hors-fold + échantillons de test. Projet intégrateur 2026 — R. Khatoun.")


# ============================================================= 1. CONSOLE LIVE
if page == PAGES[0]:
    st.title("Console de détection en temps réel")
    st.caption("Choisissez un conducteur **jamais vu** par le modèle et lancez la lecture : "
               "l'attaque se déroule, le détecteur score en direct, et le **bus CAN0 se tait** "
               "(la signature d'injection) sous vos yeux.")
    st.caption("Les **50 conducteurs** se répartissent en 3 niveaux d'*awareness* (étude ORNL) : "
               "**Groupe 1** = non averti, **Groupe 2** = averti, **Groupe 3** = averti + consigne "
               "de se garer. Plus le conducteur est averti, plus il réagit — et plus on le détecte.")
    epis = D["episodes_all"]; hl = D["highlights"]
    drivers = sorted(epis.keys(), key=lambda d: (int(d.split("_S")[0]), int(d.split("_S")[1])))
    ctl = st.columns([2, 1, 1, 1, 1])
    default = drivers.index(hl["reactif"]) if hl["reactif"] in drivers else 0
    dsel = ctl[0].selectbox("Conducteur", drivers, index=default, key="anim_drv",
                            format_func=driver_label)
    thr = ctl[1].slider("Seuil d'alerte", 0.0, 1.0, 0.5, 0.05, key="anim_thr")
    play = ctl[2].toggle("Lecture", key="anim_play")
    speed = ctl[3].slider("Vitesse", 1, 8, 3, key="anim_speed")
    if ctl[4].button("Rejouer"):
        st.session_state.apos = 0

    ep = epis[dsel]; n = len(ep["t"])
    st.session_state.setdefault("apos", n)
    if st.session_state.get("apos_drv") != dsel:
        st.session_state.apos = n; st.session_state.apos_drv = dsel
    pos = min(st.session_state.apos, n)

    t = ep["t"][:pos]; es = ep["engine_speed"][:pos]; sc = ep["score"][:pos]
    att = ep["attack"][:pos]; can0 = ep["can0_present"][:pos]; fullt = ep["t"]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    in_att = [i for i, a in enumerate(ep["attack"]) if a == 1]
    if in_att:
        fig.add_vrect(x0=ep["t"][in_att[0]], x1=ep["t"][in_att[-1]], fillcolor=RED, opacity=0.10,
                      line_width=0, annotation_text="attaque réelle", annotation_position="top left")
    fig.add_scatter(x=t, y=es, name="régime moteur (rpm)", line_color=GRAY, secondary_y=False)
    fig.add_scatter(x=t, y=sc, name="score du détecteur", line_color=BLUE, secondary_y=True)
    fig.add_hline(y=thr, line_dash="dash", line_color=RED, secondary_y=True)
    al = [(t[i], sc[i]) for i in range(len(t)) if sc[i] is not None and sc[i] >= thr]
    if al:
        fig.add_scatter(x=[a[0] for a in al], y=[a[1] for a in al], mode="markers", name="ALERTE",
                        marker=dict(color=RED, size=9, symbol="x"), secondary_y=True)
    sil = [t[i] for i in range(len(t)) if can0[i] == 0]
    if sil:
        fig.add_scatter(x=sil, y=[0.02] * len(sil), mode="markers", name="bus CAN0 muet (injection)",
                        marker=dict(color=AMBER, size=6, symbol="line-ns-open"), secondary_y=True)
    fig.update_xaxes(range=[fullt[0], fullt[-1]])
    fig.update_yaxes(title_text="régime moteur (rpm)", secondary_y=False)
    fig.update_yaxes(title_text="score", range=[0, 1], secondary_y=True)
    fig.update_layout(height=440, xaxis_title="temps (s)", legend=dict(orientation="h", y=1.12))
    show(fig)
    st.progress(pos / n, text=f"{pos}/{n} s")

    att_idx = [i for i in range(pos) if att[i] == 1]
    fired = [i for i in att_idx if sc[i] is not None and sc[i] >= thr]
    detected = len(fired) > 0
    all_att = [i for i in range(len(ep["attack"])) if ep["attack"][i] == 1]
    lat = (ep["t"][fired[0]] - ep["t"][all_att[0]]) if detected else None
    fp = sum(1 for i in range(pos) if att[i] == 0 and sc[i] is not None and sc[i] >= thr)
    can0_off = sum(1 for i in range(pos) if att[i] == 1 and can0[i] == 0)
    c = st.columns(4)
    c[0].metric("Groupe d'awareness", ep["group"])
    c[1].metric("État", "INTRUSION" if (detected and not play) else ("lecture…" if play else "nominal"))
    c[2].metric("Latence de détection", f"{lat} s" if detected else "—")
    c[3].metric("Bus CAN0 coupé", f"{can0_off} s" if can0_off else "0 s")
    if ep["group"] == 1 and not detected:
        st.warning("Conducteur **non averti** (Groupe 1) : il ne réagit pas, et son bus CAN0 est "
                   "peu logué → angle mort assumé du détecteur. Essayez un conducteur du Groupe 3.")
    elif detected:
        st.success(f"Alerte levée **{lat} s** après le début de l'attaque. Le régime moteur chute "
                   "(réaction) **et** le bus CAN0 se tait (injection) — les deux empreintes.")
    if play and st.session_state.apos < n:
        st.session_state.apos = min(st.session_state.apos + speed, n)
        time.sleep(0.2); st.rerun()


# ============================================================= 2. ATTAQUANT LIVE
elif page == PAGES[1]:
    st.title("Vous pilotez l'attaquant — l'IDS est-il robuste ?")
    st.info("**La question :** un attaquant qui connaît le détecteur peut-il devenir **invisible** ? "
            "Et si oui, à quel prix ?\n\n"
            "**Ce que vous faites :** l'IDS surveille des signaux du bus CAN. En *maquiller* un, c'est "
            "y réinjecter une valeur d'apparence normale pour tromper le modèle. Montez le curseur et "
            "regardez **combien de signaux il faut maquiller pour que l'IDS ne détecte plus rien**.")
    try:
        model = load_model(); S = load_samples()
    except Exception as e:
        st.error(f"Artefacts absents ({e}). Lancez : python artifacts/build_artifacts.py"); st.stop()
    Xa, Xn, med, rank, names = S["X_att"], S["X_norm"], S["med_norm"], S["rank"], S["feat_names"]
    c = st.columns([2, 1])
    k = c[0].slider("Nombre de signaux que vous maquillez (du plus surveillé au moins surveillé)", 0, 30, 0)
    thr = c[1].slider("Seuil de détection", 0.1, 0.9, 0.5, 0.05)
    Xa_mod = Xa.copy()
    for idx in rank[:k]:
        Xa_mod[:, idx] = med[idx]
    sa = model.predict_proba(Xa_mod)[:, 1]
    recall = float((sa >= thr).mean()) * 100
    recall0 = float((model.predict_proba(Xa)[:, 1] >= thr).mean()) * 100
    g, info = st.columns([1, 1])
    g.plotly_chart(gauge(recall, "Rappel du détecteur", good_high=True), width="stretch")
    info.metric("Rappel sans évasion", f"{recall0:.0f} %")
    info.metric("Rappel sous votre évasion", f"{recall:.0f} %", f"{recall-recall0:+.0f} pts")
    info.metric("Signaux neutralisés", k)
    if k == 0:
        info.info("Attaque brute : le détecteur la voit. Montez le curseur.")
    elif recall < 50:
        info.error(f"**ÉVADÉ** en {k} signal(aux). Le 1er est le bus CAN0 — la signature "
                   "d'injection. Le détecteur est fragile : tout repose sur une poignée de signaux.")
    else:
        info.warning("Il tient encore. Continuez à neutraliser.")
    with st.expander("Quels signaux maquillez-vous ?"):
        st.write([str(names[i]) for i in rank[:max(k, 1)]])
    st.caption("**La leçon :** un seul signal maquillé (le bus CAN0) suffit à faire chuter le rappel. "
               "Le détecteur est **fragile** car sa puissance est concentrée sur une poignée de "
               "signaux — un IDS sérieux a besoin de redondance et d'une couche de secours.")


# ============================================================= 3. BAC A SABLE D'ATTAQUE
elif page == PAGES[2]:
    st.title("Bac à sable — l'IDS détecte-t-il l'inconnu ?")
    st.info("**La question :** notre IDS n'a appris qu'**une seule** attaque (la mise à zéro de "
            "l'afficheur). Tiendra-t-il face à une attaque qu'il n'a **jamais vue** ?\n\n"
            "**Ce que vous faites :** choisissez un **type d'attaque** et son intensité ; on l'injecte "
            "sur du trafic normal et le **vrai modèle** rend son verdict. Comparez à l'attaque qu'il "
            "connaît (la référence).")
    try:
        model = load_model(); S = load_samples()
    except Exception as e:
        st.error(f"Artefacts absents ({e})."); st.stop()
    Xn, Xa, names = S["X_norm"], S["X_att"], S["feat_names"]
    names = [str(x) for x in names]
    can0 = [i for i, nm in enumerate(names) if nm.endswith(".CAN0")]
    spn190 = [i for i, nm in enumerate(names) if ".190.Engine.Speed" in nm and not nm.endswith(".CAN0")]
    lo = np.nanpercentile(Xn, 1, axis=0); hi = np.nanpercentile(Xn, 99, axis=0)
    thr = float(np.quantile(model.predict_proba(Xn)[:, 1], 0.99))   # seuil ~1% de fausses alertes
    rng = np.random.RandomState(0)

    c = st.columns([1.4, 1])
    atype = c[0].radio("Type d'attaque à injecter", [
        "DoS — couper le bus CAN0 (comme l'attaque réelle)",
        "Fuzzing — randomiser des signaux",
        "Masquerade furtif — décaler discrètement le régime moteur",
        "Replay — rejouer le trafic d'un autre instant"], index=0)
    intensity = c[1].slider("Intensité", 1, 100, 50,
                            help="Fuzzing: % de signaux touchés. Masquerade: ampleur du décalage.")
    Xm = Xn.copy()
    if atype.startswith("DoS"):
        Xm[:, can0] = np.nan
    elif atype.startswith("Fuzzing"):
        kf = max(1, int(len(names) * intensity / 100))
        for j in rng.choice(len(names), kf, replace=False):
            Xm[:, j] = rng.uniform(lo[j], hi[j], size=len(Xm)) * rng.choice([1, 3], size=len(Xm))
    elif atype.startswith("Masquerade"):
        Xm[:, spn190] = Xm[:, spn190] - (intensity * 6)     # decalage rpm
    else:
        Xm = Xn[rng.permutation(len(Xn))].copy()
    detec = float((model.predict_proba(Xm)[:, 1] >= thr).mean()) * 100
    real = float((model.predict_proba(Xa)[:, 1] >= thr).mean()) * 100

    g, info = st.columns([1, 1])
    g.plotly_chart(gauge(detec, "Taux de détection de VOTRE attaque", good_high=True), width="stretch")
    info.metric("Détection de votre attaque", f"{detec:.0f} %")
    info.metric("Référence : l'attaque réelle apprise", f"{real:.0f} %")
    info.caption(f"Seuil calibré à ~1 % de fausses alertes sur le trafic normal.")
    if detec < 10 and not atype.startswith("DoS"):
        info.error("**ANGLE MORT.** Le modèle supervisé n'a appris qu'une signature : il ne voit "
                   "pas cette attaque inédite. C'est la limite *mono-attaque* — qu'une couche "
                   "anomalie ou une détection au niveau trame comblerait.")
    elif atype.startswith("DoS"):
        info.success("Détecté : cette attaque **ressemble** à la signature apprise (silence CAN0). "
                     "Le modèle généralise quand l'attaque partage la même empreinte.")
    else:
        info.warning("Détection partielle — l'attaque empiète sur la signature connue.")
    st.caption("**La leçon :** un détecteur **supervisé** n'apprend que les attaques qu'on lui montre. "
               "Essayez le fuzzing ou le masquerade : il est aveugle. C'est la limite *mono-attaque* — "
               "en vrai, il faudrait l'entraîner sur une taxonomie d'attaques ou ajouter une couche d'anomalie.")


# ============================================================= 4. LE PIEGE
elif page == PAGES[3]:
    st.title("Le piège du data scientist — votre score est-il honnête ?")
    st.info("**La question :** un PR-AUC de 0,98, est-ce un bon détecteur… ou un **mirage** ? Tout "
            "dépend de choix faits **avant** d'entraîner le modèle.\n\n"
            "**Ce que vous faites :** vous endossez le rôle du data scientist. Choisissez votre "
            "**découpage train/test** et vos **features**, puis découvrez le score que vous obtiendriez "
            "— et si vous vous êtes **fait piéger**.")
    c = st.columns(2)
    split = c[0].radio("Comment séparer train / test ?",
                       ["Au hasard (mélanger les fenêtres)", "Par conducteur (jamais vu)"])
    feats = c[1].radio("Quelles features ?", ["CAN seul", "CAN + GPS"])
    by_driver = split.startswith("Par")
    with_gps = feats.endswith("GPS")
    if not by_driver and not with_gps:
        score, verdict, msg = 0.985, "error", ("**FUITE par conducteur.** Chaque conducteur ne "
            "fait qu'un trajet : en mélangeant, le modèle reconnaît la *personne*, pas l'attaque. "
            "Score brillant… et faux.")
    elif by_driver and not with_gps:
        score, verdict, msg = 0.632, "success", ("**Honnête.** Split par conducteur + CAN seul : "
            "c'est la vraie difficulté, sans triche. C'est notre point de départ.")
    elif by_driver and with_gps:
        score, verdict, msg = 0.835, "error", ("**CONFONDEUR de lieu.** L'attaque est toujours au "
            "même endroit : avec le GPS, le modèle fait du *géofencing* — il détecte l'endroit, "
            "pas l'attaque.")
    else:
        score, verdict, msg = 0.99, "error", ("**Les DEUX pièges cumulés** (fuite conducteur + "
            "confondeur GPS). Le score frôle la perfection et ne prouve rien.")
    st.metric("PR-AUC que vous obtiendriez", f"{score:.3f}",
              "trompeur" if verdict == "error" else "honnête",
              delta_color="inverse" if verdict == "error" else "normal")
    (st.error if verdict == "error" else st.success)(msg)
    st.caption("Le hasard est à 0,015. Tout l'enjeu d'un projet sécurité crédible est de **refuser "
               "le score flatteur** et de garder le 0,632 honnête. C'est le cœur méthodologique du projet.")


# ============================================================= 5. DEPLOIEMENT
elif page == PAGES[4]:
    st.title("Réglez l'IDS pour le déploiement — combien de fausses alertes ?")
    st.info("**La question :** vous déployez l'IDS dans une flotte. Avec quelle **sensibilité** "
            "d'alarme ? Et surtout : en vrai, l'attaque est **rare** — combien de vos alertes seront "
            "**fausses** ?\n\n"
            "**Ce que vous faites :** réglez le **seuil** (sévérité de l'alarme) et le **taux d'attaque "
            "réel** attendu en exploitation, puis lisez la **précision réelle** et le coût en fausses alertes.")
    T = D["thresholds"]
    c = st.columns(2)
    q = c[0].slider("Sévérité du seuil (quantile du score)", 0.50, 0.99, 0.90, 0.01)
    base = c[1].selectbox("Taux d'attaque réel en exploitation",
                          [0.45, 0.10, 0.0146, 0.001, 0.0001], index=2,
                          format_func=lambda x: f"{x*100:.2f} %  ({'dataset' if abs(x-0.0146)<1e-4 else 'réaliste flotte' if x<0.05 else 'irréaliste'})")
    row = min(T, key=lambda r: abs(r["q"] - q))
    R = row["recall"]; fpr = row["alert_rate"]          # approx FPR ~ taux d'alerte (negatifs dominants)
    prec_real = base * R / (base * R + (1 - base) * fpr) if (base * R + (1 - base) * fpr) > 0 else 0
    m = st.columns(4)
    m[0].metric("Rappel (attaque captée)", f"{R*100:.0f} %")
    m[1].metric("Précision sur le dataset", f"{row['precision']*100:.0f} %")
    m[2].metric("Précision en exploitation", f"{prec_real*100:.0f} %",
                "s'effondre" if prec_real < 0.5 else None,
                delta_color="inverse")
    m[3].metric("Fenêtres alertées", f"{fpr*100:.2f} %")
    bs = np.logspace(-4, -0.3, 80)
    fig = go.Figure(go.Scatter(x=bs, y=bs * R / (bs * R + (1 - bs) * fpr), line_color=RED))
    fig.add_vline(x=base, line_dash="dash", line_color=AMBER, annotation_text="votre contexte")
    fig.update_xaxes(type="log", title="taux d'attaque réel (log)")
    fig.update_yaxes(title="précision opérationnelle", range=[0, 1.02])
    fig.update_layout(height=320, title="La base-rate fallacy : précision vs rareté de l'attaque")
    show(fig)
    if prec_real < 0.5:
        st.error(f"À **{base*100:.2f} %** d'attaque, votre précision réelle tombe à "
                 f"**{prec_real*100:.0f} %** : la plupart des alertes seraient fausses (fatigue "
                 "d'alerte). **Un bon rappel ne suffit pas** — durcissez le seuil.")
    else:
        st.success("Compromis tenable. Le seuil haute-précision (< 1 % d'alertes) est recommandé en "
                   "flotte : l'attaque étant un bloc continu, capter la moitié des secondes suffit.")
