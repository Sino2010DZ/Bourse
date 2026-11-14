// Sentinelle — moteur de thèmes.
// Chaque thème est un fichier themes/<nom>.json. Ce script copie ses couleurs dans des
// variables CSS (--fond, --texte, --accent…) et ses options dans des attributs du <body>.
// Le reste de l'interface ne lit QUE ces variables : aucune couleur n'est écrite ailleurs.
"use strict";

const Themes = (() => {
  const CLE_MEMOIRE = "sentinelle.theme";        // copie locale du dernier thème (affichage instantané)
  const VARIABLES = {
    fond: "--fond", panneau: "--panneau", surface: "--surface", relief: "--relief",
    texte: "--texte", texte2: "--texte2", texte3: "--texte3", ligne: "--ligne",
    accent: "--accent", surAccent: "--sur-accent", accentTexte: "--accent-texte",
  };
  const etat = { liste: [], donnees: {}, actuel: null, prefs: null, auChangement: [] };
  const sombreSysteme = window.matchMedia("(prefers-color-scheme: dark)");

  function appliquerVariables(cible, couleurs) {
    for (const [cle, variable] of Object.entries(VARIABLES)) {
      if (couleurs[cle]) cible.style.setProperty(variable, couleurs[cle]);
    }
  }

  function poser(id, theme, { fondu = false } = {}) {
    const racine = document.documentElement;
    if (fondu) {
      racine.classList.add("fondu");
      clearTimeout(poser.minuteur);
      poser.minuteur = setTimeout(() => racine.classList.remove("fondu"), 350);
    }
    appliquerVariables(racine, theme.couleurs);
    const options = {
      theme: id,
      police: theme.police,
      messages: theme.messages,
      saisie: theme.saisie,
      droite: theme.droite,
      bandeau: theme.bandeau ? "oui" : "non",
      gauche: theme.gauche,
      sombre: theme.sombre ? "oui" : "non",
    };
    for (const [cle, valeur] of Object.entries(options)) racine.dataset[cle] = valeur;
    etat.actuel = id;
    try { localStorage.setItem(CLE_MEMOIRE, JSON.stringify({ id, theme })); } catch { /* mémoire indisponible */ }
    etat.auChangement.forEach((f) => f(id, theme));
  }

  // Avant tout chargement : remet le dernier thème connu pour éviter un flash de couleurs.
  try {
    const memo = JSON.parse(localStorage.getItem(CLE_MEMOIRE) || "null");
    if (memo && memo.theme) poser(memo.id, memo.theme);
  } catch { /* rien */ }

  async function charger(urlApi) {
    const index = await (await fetch("themes/index.json")).json();
    etat.liste = index.themes;
    await Promise.all(
      etat.liste.map(async (id) => {
        etat.donnees[id] = await (await fetch(`themes/${id}.json`)).json();
      })
    );
    try {
      etat.prefs = await (await fetch(urlApi + "/api/preferences")).json();
    } catch {
      etat.prefs = { theme: index.defaut, auto: false, theme_clair: index.defaut_clair, theme_sombre: index.defaut_sombre, budget_jour_usd: 1 };
    }
    etat.urlApi = urlApi;
    choisirSelonPreferences(false);
    sombreSysteme.addEventListener("change", () => etat.prefs.auto && choisirSelonPreferences(true));
  }

  function themeVoulu() {
    const p = etat.prefs;
    const id = p.auto ? (sombreSysteme.matches ? p.theme_sombre : p.theme_clair) : p.theme;
    return etat.donnees[id] ? id : etat.liste[0];
  }

  function choisirSelonPreferences(fondu = true) {
    const id = themeVoulu();
    if (id !== etat.actuel || !fondu) poser(id, etat.donnees[id], { fondu });
  }

  async function enregistrer(changements) {
    Object.assign(etat.prefs, changements);
    try {
      const r = await fetch(etat.urlApi + "/api/preferences", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(etat.prefs),
      });
      if (r.ok) etat.prefs = await r.json();
    } catch { /* le choix reste appliqué pour cette session */ }
  }

  function choisir(id) {
    if (!etat.donnees[id]) return;
    poser(id, etat.donnees[id], { fondu: true });
    enregistrer({ theme: id, auto: false });
  }

  function suivant() {
    const i = etat.liste.indexOf(etat.actuel);
    choisir(etat.liste[(i + 1) % etat.liste.length]);
  }

  return {
    charger,
    choisir,
    suivant,
    enregistrer,
    choisirSelonPreferences,
    appliquerVariables,
    get liste() { return etat.liste; },
    get donnees() { return etat.donnees; },
    get actuel() { return etat.actuel; },
    get prefs() { return etat.prefs; },
    surChangement(f) { etat.auChangement.push(f); },
  };
})();
