// Sentinelle — interface. Parle au serveur local Python (127.0.0.1:8765).
"use strict";

const PORT = 8765;
const SERVI_PAR_LE_SERVEUR = location.protocol.startsWith("http") && location.port === String(PORT);
const API = SERVI_PAR_LE_SERVEUR ? "" : `http://127.0.0.1:${PORT}`;
const SUGGESTIONS = [
  "Comment vont mes actions ?",
  "Où en sont mes prix Galaxus ?",
  "Quelle est la tendance d'Aston Martin ?",
  "Qu'est-ce qui bouge fort aujourd'hui ?",
];

const $ = (id) => document.getElementById(id);
const fil = $("fil");
const champ = $("message");
const bouton = $("envoyer");

const etat = {
  discussionId: null,
  sections: [],
  pret: false,
  occupe: false,
  graphique: { ticker: null, periode: "1M" },
  positions: [],
  produits: [],
  produitOuvert: null,
};

// ------------------------------------------------------------ outils

async function api(chemin, options = {}) {
  const r = await fetch(API + chemin, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (!r.ok) {
    let detail = `Erreur ${r.status}`;
    try { detail = (await r.json()).detail || detail; } catch { /* rien */ }
    throw new Error(detail);
  }
  return r.json();
}

function el(tag, classe, texte) {
  const e = document.createElement(tag);
  if (classe) e.className = classe;
  if (texte !== undefined) e.textContent = texte;
  return e;
}

function icone(chemin) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  const p = document.createElementNS(ns, "path");
  p.setAttribute("d", chemin);
  svg.append(p);
  return svg;
}
const ICONES = {
  copier: "M8 8h11v13H8zM5 16H4V3h11v1",
  regenerer: "M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7",
  ok: "M5 12l5 5 9-10",
};

const fmt = (n, dec = 2) => n.toLocaleString("fr-CH", { minimumFractionDigits: dec, maximumFractionDigits: dec });
const signe = (n) => (n > 0 ? "+" : n < 0 ? "−" : "") + fmt(Math.abs(n));
const devise = (d) => (d === "GBp" ? "p" : d);
const fleche = (v) => (v > 0 ? "▲ " : v < 0 ? "▼ " : "");

// Texte des réponses : **gras** → <strong>, sans jamais interpréter de HTML.
function remplirTexte(cible, texte) {
  cible.replaceChildren();
  texte.split(/\*\*(.+?)\*\*/gs).forEach((morceau, i) => {
    if (i % 2) cible.append(el("strong", "", morceau));
    else if (morceau) cible.append(document.createTextNode(morceau));
  });
}

// ------------------------------------------------------------ discussion

function accueil() {
  const h = new Date().getHours();
  const salut = h < 5 || h >= 18 ? "Bonsoir" : "Bonjour";
  const bloc = el("div", "accueil");
  bloc.append(el("h1", "", `${salut}, Monsieur.`), el("p", "", "Que puis-je faire pour vous ?"));
  fil.replaceChildren(bloc);
}

function messageMoi(texte) {
  const m = el("div", "message moi");
  m.append(el("div", "texte", texte));
  fil.querySelector(".accueil")?.remove();
  fil.append(m);
  fil.scrollTop = fil.scrollHeight;
  return m;
}

function messageChef(texte, { agents = [], meta = null, erreur = false, attente = false, dernier = false } = {}) {
  const m = el("div", "message chef" + (erreur ? " erreur" : "") + (attente ? " attente" : ""));
  const signature = el("div", "signature");
  const pastille = el("span", "pastille-chef");
  pastille.append(el("span"));
  signature.append(pastille, document.createTextNode("Grand Chef"));
  const corps = el("div", "texte");
  remplirTexte(corps, texte);
  m.append(signature, corps);

  if (!attente) {
    const pied = el("div", "pied-message");
    agents.forEach((a) => pied.append(el("span", "pastille", a)));
    if (meta && !erreur) {
      pied.append(el("span", "meta", `${(meta.duree_ms / 1000).toFixed(1)} s · ${fmt(meta.cout_usd, 3)} $`));
    }
    pied.append(el("span", "espace"));
    const copier = el("button", "action-message");
    copier.type = "button";
    copier.append(icone(ICONES.copier), document.createTextNode("Copier"));
    copier.addEventListener("click", () => copierTexte(texte, copier));
    pied.append(copier);
    if (dernier) {
      const regen = el("button", "action-message regenerer");
      regen.type = "button";
      regen.append(icone(ICONES.regenerer), document.createTextNode("Régénérer"));
      regen.addEventListener("click", () => regenerer(m));
      pied.append(regen);
    }
    m.append(pied);
  }
  fil.querySelector(".accueil")?.remove();
  fil.append(m);
  fil.scrollTop = fil.scrollHeight;
  return m;
}

async function copierTexte(texte, boutonCopier) {
  try {
    await navigator.clipboard.writeText(texte);
  } catch {
    const zone = el("textarea");
    zone.value = texte;
    document.body.append(zone);
    zone.select();
    document.execCommand("copy");
    zone.remove();
  }
  boutonCopier.replaceChildren(icone(ICONES.ok), document.createTextNode("Copié"));
  setTimeout(() => boutonCopier.replaceChildren(icone(ICONES.copier), document.createTextNode("Copier")), 1500);
}

function retirerBoutonsRegenerer() {
  fil.querySelectorAll(".regenerer").forEach((b) => b.remove());
}

// Messages d'erreur du navigateur (« Load failed », « Failed to fetch »…) traduits en français.
function traduireErreur(e) {
  const m = (e && e.message) || "";
  if (/load failed|failed to fetch|networkerror|network connection/i.test(m)) {
    return "je n'arrive plus à joindre mon serveur interne. Quittez Sentinelle (⌘ + Q) puis rouvrez-la";
  }
  return m || "une erreur inconnue est survenue";
}

// Lance la question en « tâche » puis demande chaque seconde si la réponse est prête :
// le Mac coupe les requêtes de plus de 60 secondes, et une question aux agents peut durer plus.
async function attendreReponse(corps, attente) {
  const { tache, discussion_id } = await api("/api/chat/tache", { method: "POST", body: JSON.stringify(corps) });
  etat.discussionId = discussion_id;
  const debut = Date.now();
  let echecs = 0;
  for (;;) {
    await new Promise((r) => setTimeout(r, 1000));
    let suivi;
    try {
      suivi = await api(`/api/chat/tache/${tache}`);
      echecs = 0;
    } catch (e) {
      if (++echecs >= 5) throw e;      // 5 échecs d'affilée : le serveur ne répond vraiment plus
      continue;
    }
    if (suivi.statut === "fini") return suivi.resultat;
    if (suivi.statut === "erreur") throw new Error(suivi.detail);
    const secondes = Math.round((Date.now() - debut) / 1000);
    const corpsAttente = attente.querySelector(".texte");
    if (corpsAttente && secondes >= 8) {
      corpsAttente.textContent = secondes < 25 ? "Mes agents travaillent, Monsieur" : `Encore un instant, Monsieur (${secondes} s)`;
    }
  }
}

async function demander(corps, attente) {
  etat.occupe = true;
  bouton.disabled = true;
  try {
    const r = await attendreReponse(corps, attente);
    attente.remove();
    etat.discussionId = r.discussion_id;
    retirerBoutonsRegenerer();
    messageChef(r.reponse, {
      agents: r.agents,
      meta: { duree_ms: r.duree_ms, cout_usd: r.cout_usd },
      erreur: r.erreur,
      dernier: true,
    });
    afficherQuota(r.consommation);
    chargerHistorique();
  } catch (e) {
    attente.remove();
    messageChef(`Toutes mes excuses, Monsieur : ${traduireErreur(e)}.`, { erreur: true });
  } finally {
    etat.occupe = false;
    bouton.disabled = !etat.pret;
    champ.focus();
  }
}

async function envoyer(texte) {
  texte = (texte ?? champ.value).trim();
  if (!texte || etat.occupe || !etat.pret) return;
  champ.value = "";
  ajusterHauteur();
  retirerBoutonsRegenerer();
  if (!etat.discussionId) $("titre-discussion").textContent = texte;
  messageMoi(texte);
  const attente = messageChef("Je m'en occupe, Monsieur", { attente: true });
  await demander({ message: texte, discussion_id: etat.discussionId, section: $("section").value || null }, attente);
}

async function regenerer(ancien) {
  if (etat.occupe || !etat.discussionId) return;
  ancien.remove();
  const attente = messageChef("Je reformule, Monsieur", { attente: true });
  await demander({ discussion_id: etat.discussionId, regenerer: true }, attente);
}

function nouvelleDiscussion() {
  etat.discussionId = null;
  $("titre-discussion").textContent = "Nouvelle discussion";
  accueil();
  marquerHistorique();
  champ.focus();
}

async function ouvrirDiscussion(id) {
  try {
    const d = await api(`/api/discussions/${id}`);
    etat.discussionId = d.id;
    $("titre-discussion").textContent = d.titre;
    fil.replaceChildren();
    const derniere = d.messages.map((m) => m.role).lastIndexOf("chef");
    d.messages.forEach((m, i) => {
      if (m.role === "moi") messageMoi(m.texte);
      else messageChef(m.texte, { agents: m.agents, meta: m.meta, erreur: m.meta.erreur, dernier: i === derniere });
    });
    if (!d.messages.length) accueil();
    marquerHistorique();
  } catch {
    /* discussion introuvable : on ne change rien */
  }
}

// ------------------------------------------------------------ historique (gauche)

async function chargerHistorique() {
  const q = $("recherche").value.trim();
  let liste = [];
  try { liste = await api("/api/discussions" + (q ? `?q=${encodeURIComponent(q)}` : "")); } catch { /* hors ligne */ }
  const nav = $("historique");
  nav.replaceChildren();
  if (!liste.length) {
    nav.append(el("div", "rien", q ? "Aucun résultat." : "Aucune discussion pour l'instant."));
    return;
  }
  const minuit = new Date(); minuit.setHours(0, 0, 0, 0);
  const semaine = new Date(minuit); semaine.setDate(semaine.getDate() - 6);
  const groupes = { "Aujourd'hui": [], "Cette semaine": [], "Plus ancien": [] };
  liste.forEach((d) => {
    const date = new Date(d.modifiee);
    const g = date >= minuit ? "Aujourd'hui" : date >= semaine ? "Cette semaine" : "Plus ancien";
    groupes[g].push(d);
  });
  for (const [nom, discussions] of Object.entries(groupes)) {
    if (!discussions.length) continue;
    nav.append(el("div", "groupe", nom));
    discussions.forEach((d) => {
      const b = el("button", "", d.titre);
      b.type = "button";
      b.title = d.titre;
      b.dataset.id = d.id;
      b.addEventListener("click", () => ouvrirDiscussion(d.id));
      nav.append(b);
    });
  }
  marquerHistorique();
}

function marquerHistorique() {
  $("historique").querySelectorAll("button").forEach((b) => b.classList.toggle("actif", Number(b.dataset.id) === etat.discussionId));
}

// ------------------------------------------------------------ sections et quota

function afficherSections(sections) {
  etat.sections = sections;
  const libelles = { active: "en service", en_preparation: "en préparation", a_construire: "à construire" };
  $("liste-sections").replaceChildren(
    ...sections.map((s) => {
      const li = el("li", s.statut, s.icone);
      li.title = `${s.nom} — ${s.commandant} (${libelles[s.statut]})`;
      li.append(el("i", `point ${s.statut}`));
      return li;
    })
  );
  const choix = $("section");
  choix.replaceChildren(el("option", "", "Toutes les sections"));
  choix.firstChild.value = "";
  sections.forEach((s) => {
    const o = el("option", "", `${s.icone} ${s.nom}` + (s.statut === "active" ? "" : " (à construire)"));
    o.value = s.id;
    o.disabled = s.statut !== "active";
    choix.append(o);
  });
}

function afficherQuota(c) {
  if (!c) return;
  const budget = c.budget_jour_usd || 1;
  const part = Math.min(100, (c.cout_usd / budget) * 100);
  $("quota-jauge").style.width = `${part}%`;
  $("quota-texte").textContent = `${fmt(c.cout_usd)} / ${fmt(budget)} $`;
  $("quota").title = `Dépense du jour : ${fmt(c.cout_usd, 3)} $ sur un budget de ${fmt(budget)} $ (${c.echanges} appels)`;
}

// ------------------------------------------------------------ bourse (droite + bandeau)

async function chargerActions() {
  try {
    const res = await api("/api/bourse/mes-actions");
    etat.positions = res.positions;
    if (!etat.graphique.ticker && res.positions.length) etat.graphique.ticker = res.positions[0].ticker;
    const zone = $("actions");
    zone.replaceChildren(
      ...res.positions.map((p) => {
        const ligne = el("button", "action" + (p.ticker === etat.graphique.ticker ? " choisie" : ""));
        ligne.type = "button";
        ligne.title = p.date_cours ? `Cours du ${p.date_cours} — cliquez pour le graphique` : "";
        ligne.append(el("span", "nom-action", p.nom));
        ligne.append(el("span", "prix", p.prix == null ? "—" : `${fmt(p.prix)} ${devise(p.devise)}`));
        const detail = p.valeur_chf != null
          ? `${fmt(p.quantite, 0)} pièces · ${fmt(p.valeur_chf)} CHF` + (p.gain_pct != null ? ` · ${signe(p.gain_pct)} %` : "")
          : p.ticker;
        ligne.append(el("span", "detail", detail));
        const v = p.variation_jour_pct;
        ligne.append(el("span", "var" + (v > 0 ? " hausse" : ""), v == null ? "" : `${fleche(v)}${signe(v)} %`));
        ligne.addEventListener("click", () => { etat.graphique.ticker = p.ticker; chargerActions(); });
        return ligne;
      })
    );
    if (res.positions.some((p) => p.valeur_chf != null)) {
      const total = el("div", "total-actions");
      total.append(el("span", "", "Total"), el("span", "", `${fmt(res.valeur_totale_chf)} CHF`));
      zone.append(total);
    }
    afficherBandeau(res.positions);
    chargerGraphique();
  } catch {
    $("actions").replaceChildren(el("div", "vide", "Cours indisponibles pour le moment."));
  }
}

async function chargerGraphique() {
  const { ticker, periode } = etat.graphique;
  if (!ticker) return;
  document.querySelectorAll("#periodes button").forEach((b) => b.classList.toggle("actif", b.dataset.periode === periode));
  const position = etat.positions.find((p) => p.ticker === ticker);
  $("graphique-nom").textContent = position ? position.nom : ticker;
  const svg = $("graphique");
  try {
    const g = await api(`/api/bourse/graphique?ticker=${encodeURIComponent(ticker)}&periode=${periode}`);
    if (etat.graphique.ticker !== ticker || etat.graphique.periode !== periode) return; // clic plus récent
    const v = g.variation_pct;
    $("graphique-var").textContent = v == null ? "" : `${fleche(v)}${signe(v)} % sur ${periode}`;
    dessinerCourbe(svg, g.points.map((p) => p.p));
  } catch {
    $("graphique-var").textContent = "indisponible";
    svg.replaceChildren();
  }
}

function dessinerCourbe(svg, valeurs, largeur = 300, hauteur = 90, avecAire = true) {
  const ns = "http://www.w3.org/2000/svg";
  svg.replaceChildren();
  if (valeurs.length === 1) valeurs = [valeurs[0], valeurs[0]];
  if (valeurs.length < 2) return;
  const min = Math.min(...valeurs), max = Math.max(...valeurs);
  const ecart = max - min || 1;
  const pts = valeurs.map((v, i) => [
    (i / (valeurs.length - 1)) * largeur,
    hauteur - 4 - ((v - min) / ecart) * (hauteur - 8),
  ]);
  const d = pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  const aire = document.createElementNS(ns, "path");
  aire.setAttribute("d", `${d} L${largeur} ${hauteur} L0 ${hauteur} Z`);
  aire.setAttribute("class", "aire");
  const ligne = document.createElementNS(ns, "path");
  ligne.setAttribute("d", d);
  ligne.setAttribute("class", "ligne-cours");
  if (avecAire) svg.append(aire);
  svg.append(ligne);
}

function afficherBandeau(positions) {
  const elements = positions.map((p) => {
    const e = el("span", "element");
    e.append(el("strong", "", p.nom.replace(" (ETF)", "")));
    const v = p.variation_jour_pct;
    e.append(document.createTextNode(p.prix == null ? "—" : `${fmt(p.prix)} ${devise(p.devise)} `));
    if (v != null) e.append(el("span", v > 0 ? "hausse" : "", `${fleche(v)}${signe(v)} %`));
    return e;
  });
  const produit = etat.produits.find((p) => p.prix != null);
  const galaxus = el("span", "element");
  galaxus.append(el("strong", "", "Galaxus"));
  if (produit) {
    galaxus.append(document.createTextNode(`${produit.nom.slice(0, 28)} ${fmt(produit.prix)} CHF `));
    if (produit.variation) galaxus.append(el("span", produit.variation < 0 ? "hausse" : "", `${fleche(produit.variation)}${signe(produit.variation)}`));
  } else {
    galaxus.append(document.createTextNode("aucun produit suivi"));
  }
  elements.push(galaxus);
  for (const [titre, texte] of [["F1", "à construire"], ["Genève", "météo à construire"]]) {
    const e = el("span", "element");
    e.append(el("strong", "", titre), document.createTextNode(texte));
    elements.push(e);
  }
  $("bandeau").replaceChildren(...elements);
}

// Modifier quantités et prix d'achat
async function ouvrirFormulaire() {
  const pf = await api("/api/portefeuille");
  $("actions-champs").replaceChildren(
    ...pf.positions.map((p, i) => {
      const fs = el("fieldset");
      fs.append(el("legend", "", `${p.nom} (${p.ticker})`));
      for (const [cle, libelle] of [["quantite", "Quantité"], ["prix_achat", `Prix d'achat (${devise(p.devise)})`]]) {
        const label = el("label", "", libelle);
        const input = el("input");
        input.type = "number"; input.min = "0"; input.step = "any";
        input.dataset.index = i; input.dataset.cle = cle;
        input.value = p[cle] ?? "";
        label.append(input);
        fs.append(label);
      }
      return fs;
    })
  );
  $("actions-formulaire").dataset.portefeuille = JSON.stringify(pf);
  $("actions-erreur").textContent = "";
  $("actions").hidden = true;
  $("actions-formulaire").hidden = false;
}

function fermerFormulaire() {
  $("actions-formulaire").hidden = true;
  $("actions").hidden = false;
}

$("actions-formulaire").addEventListener("submit", async (e) => {
  e.preventDefault();
  const formulaire = e.currentTarget;
  const pf = JSON.parse(formulaire.dataset.portefeuille);
  formulaire.querySelectorAll("input").forEach((input) => {
    pf.positions[input.dataset.index][input.dataset.cle] = input.value === "" ? null : Number(input.value);
  });
  try {
    await api("/api/portefeuille", { method: "PUT", body: JSON.stringify(pf) });
    fermerFormulaire();
    chargerActions();
  } catch (err) {
    $("actions-erreur").textContent = err.message;
  }
});

// ------------------------------------------------------------ prix suivis (Galaxus)

const date = (iso) => new Date(iso).toLocaleDateString("fr-CH", { day: "2-digit", month: "2-digit", year: "2-digit" });
const dateHeure = (iso) => `${date(iso)} ${new Date(iso).toLocaleTimeString("fr-CH", { hour: "2-digit", minute: "2-digit" })}`;

async function chargerProduits() {
  try {
    etat.produits = await api("/api/produits");
  } catch {
    return;
  }
  const zone = $("produits");
  if (!etat.produits.length) {
    zone.replaceChildren(el("div", "vide", "Aucun produit suivi. Cliquez sur « + Ajouter » et collez un lien Galaxus."));
  } else {
    zone.replaceChildren(
      ...etat.produits.map((p) => {
        const b = el("button", "produit");
        b.type = "button";
        b.title = `${p.nom} — cliquez pour la courbe`;
        b.append(el("span", "nom-produit", p.nom));
        const manuel = p.historique.length && p.historique[p.historique.length - 1].source === "manuel";
        const etatTexte = p.statut !== "ok" && p.prix == null ? "prix à saisir (lecture refusée)" :
          p.dernier_releve ? `${manuel ? "saisi" : "relevé"} le ${date(p.dernier_releve)}` : "en attente du premier relevé";
        b.append(el("span", "etat-produit", etatTexte));
        const mini = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        mini.setAttribute("class", "mini");
        mini.setAttribute("viewBox", "0 0 64 22");
        mini.setAttribute("preserveAspectRatio", "none");
        dessinerCourbe(mini, p.historique.map((h) => h.prix), 64, 22, false);
        b.append(mini);
        b.append(el("span", "prix-produit", p.prix == null ? "—" : `${fmt(p.prix)} CHF`));
        const v = p.variation;
        b.append(el("span", "var-produit" + (v < 0 ? " baisse" : ""), v ? `${fleche(v)}${signe(v)}` : p.prix_min != null && p.prix === p.prix_min && p.nb_releves > 1 ? "plus bas" : ""));
        b.addEventListener("click", () => ouvrirProduit(p.id));
        return b;
      })
    );
  }
  afficherBandeau(etat.positions);
  if (etat.produitOuvert) remplirFiche();
}

function basculerFormulaireProduit(ouvert) {
  $("produit-formulaire").hidden = !ouvert;
  $("produit-erreur").textContent = "";
  if (ouvert) { $("produit-lien").value = ""; $("produit-prix").value = ""; $("produit-lien").focus(); }
}

$("ajouter-produit").addEventListener("click", () => basculerFormulaireProduit($("produit-formulaire").hidden));
$("annuler-produit").addEventListener("click", () => basculerFormulaireProduit(false));
$("produit-formulaire").addEventListener("submit", async (e) => {
  e.preventDefault();
  const bouton = e.currentTarget.querySelector("button[type=submit]");
  bouton.disabled = true;
  $("produit-erreur").textContent = "Lecture du prix sur Galaxus…";
  try {
    const prix = $("produit-prix").value;
    const p = await api("/api/produits", {
      method: "POST",
      body: JSON.stringify({ url: $("produit-lien").value.trim(), prix: prix ? Number(prix) : null }),
    });
    basculerFormulaireProduit(false);
    await chargerProduits();
    if (p.statut !== "ok" && p.prix == null) ouvrirProduit(p.id);   // Galaxus refuse : saisir le prix
  } catch (err) {
    $("produit-erreur").textContent = err.message;
  } finally {
    bouton.disabled = false;
  }
});

function ouvrirProduit(id) {
  etat.produitOuvert = id;
  $("fp-confirmation").hidden = true;
  $("fp-supprimer").hidden = false;
  $("fp-erreur").textContent = "";
  $("fp-prix").value = "";
  remplirFiche();
  if (!$("fiche-produit").open) $("fiche-produit").showModal();
}

function remplirFiche() {
  const p = etat.produits.find((x) => x.id === etat.produitOuvert);
  if (!p) { $("fiche-produit").close(); return; }
  $("fp-nom").textContent = p.nom;
  $("fp-etat").textContent = p.statut === "ok" || !p.statut
    ? `Suivi depuis le ${date(p.ajoute)} · ${p.nb_releves} relevé(s) · lecture automatique chaque jour à 8h`
    : `${p.message.replace(/ :.*$/, ".")} Notez ici le prix affiché sur Galaxus : la courbe et les alertes fonctionnent pareil.`;
  const chiffres = [["Prix actuel", p.prix], ["Plus bas", p.prix_min], ["Plus haut", p.prix_max], ["Au départ", p.premier_prix]];
  $("fp-chiffres").replaceChildren(
    ...chiffres.map(([titre, valeur]) => {
      const d = el("div");
      d.append(el("span", "", titre), el("strong", "", valeur == null ? "—" : `${fmt(valeur)} CHF`));
      return d;
    })
  );
  dessinerCourbe($("fp-graphique"), p.historique.map((h) => h.prix), 600, 160);
  $("fp-releves").replaceChildren(
    ...p.historique.slice().reverse().slice(0, 30).map((h) => {
      const ligne = el("div");
      ligne.append(
        el("span", "", `${dateHeure(h.horodatage)} · ${h.source === "auto" ? "lu sur Galaxus" : "saisi à la main"}`),
        el("span", "", `${fmt(h.prix)} CHF`)
      );
      return ligne;
    })
  );
}

$("fp-fermer").addEventListener("click", () => { $("fiche-produit").close(); });
$("fiche-produit").addEventListener("close", () => { etat.produitOuvert = null; });
$("fp-saisie").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api(`/api/produits/${etat.produitOuvert}/prix`, { method: "POST", body: JSON.stringify({ prix: Number($("fp-prix").value) }) });
    $("fp-prix").value = "";
    $("fp-erreur").textContent = "";
    chargerProduits();
  } catch (err) {
    $("fp-erreur").textContent = err.message;
  }
});
$("fp-relever").addEventListener("click", async () => {
  $("fp-etat").textContent = "Lecture du prix sur Galaxus…";
  try {
    const r = await api(`/api/produits/${etat.produitOuvert}/relever`, { method: "POST" });
    await chargerProduits();
    if (!r.releve.ok) $("fp-etat").textContent = r.releve.message;
  } catch (err) {
    $("fp-etat").textContent = err.message;
  }
});
$("fp-ouvrir").addEventListener("click", () => api(`/api/produits/${etat.produitOuvert}/ouvrir`, { method: "POST" }).catch(() => {}));
// Règle de sécurité : rien n'est supprimé sans le bouton « Confirmer ».
$("fp-supprimer").addEventListener("click", () => { $("fp-supprimer").hidden = true; $("fp-confirmation").hidden = false; });
$("fp-annuler").addEventListener("click", () => { $("fp-supprimer").hidden = false; $("fp-confirmation").hidden = true; });
$("fp-confirmer").addEventListener("click", async () => {
  try {
    await api(`/api/produits/${etat.produitOuvert}?confirmer=true`, { method: "DELETE" });
    $("fiche-produit").close();
    chargerProduits();
  } catch (err) {
    $("fp-erreur").textContent = err.message;
  }
});

// ------------------------------------------------------------ 50 agents

async function chargerAgents() {
  try {
    const agents = await api("/api/agents");
    const noms = Object.fromEntries(etat.sections.map((s) => [s.id, s.nom]));
    $("grille-agents").replaceChildren(
      ...agents.map((a) => {
        const c = el("span", a.actif ? "actif" : "");
        c.title = `${a.nom} — ${noms[a.section] || a.section} (${a.actif ? "en service" : "à construire"})`;
        return c;
      })
    );
    $("agents-compteur").textContent = `${agents.filter((a) => a.actif).length} / ${agents.length} en service`;
  } catch { /* hors ligne */ }
}

// ------------------------------------------------------------ réglages › apparence

function construireVignettes() {
  const grille = $("vignettes");
  grille.replaceChildren(
    ...Themes.liste.map((id) => {
      const t = Themes.donnees[id];
      const b = el("button", "vignette");
      b.type = "button";
      b.dataset.id = id;
      const apercu = el("span", "apercu");
      Themes.appliquerVariables(apercu, t.couleurs);   // les couleurs viennent du fichier du thème
      const gauche = el("span", "a-gauche");
      gauche.append(el("span", "trait court"), el("span", "trait"), el("span", "trait court"));
      const centre = el("span", "a-centre");
      centre.append(el("span", "bulle"), el("span", "trait fort"), el("span", "trait"));
      const barre = el("span", "barre");
      barre.append(el("i"));
      centre.append(barre);
      const droite = el("span", "a-droite");
      droite.append(el("span", "carte"), el("span", "carte"));
      apercu.append(gauche, centre, droite);
      b.append(apercu, el("span", "vignette-nom", `${String(t.numero).padStart(2, "0")} · ${t.nom}`));
      b.addEventListener("click", () => { Themes.choisir(id); majReglages(); });
      return b;
    })
  );
  const remplir = (select, sombre) => {
    select.replaceChildren(
      ...Themes.liste
        .filter((id) => Themes.donnees[id].sombre === sombre)
        .map((id) => { const o = el("option", "", Themes.donnees[id].nom); o.value = id; return o; })
    );
  };
  remplir($("theme-clair"), false);
  remplir($("theme-sombre"), true);
}

function majReglages() {
  const p = Themes.prefs;
  $("vignettes").querySelectorAll(".vignette").forEach((v) => v.classList.toggle("choisie", v.dataset.id === Themes.actuel));
  $("auto").checked = p.auto;
  $("theme-clair").value = p.theme_clair;
  $("theme-sombre").value = p.theme_sombre;
  $("budget").value = p.budget_jour_usd;
}

$("ouvrir-reglages").addEventListener("click", () => { majReglages(); $("reglages").showModal(); });
$("auto").addEventListener("change", async (e) => {
  await Themes.enregistrer({ auto: e.target.checked });
  Themes.choisirSelonPreferences(true);
  majReglages();
});
for (const id of ["theme-clair", "theme-sombre"]) {
  $(id).addEventListener("change", async (e) => {
    await Themes.enregistrer({ [id === "theme-clair" ? "theme_clair" : "theme_sombre"]: e.target.value });
    Themes.choisirSelonPreferences(true);
    majReglages();
  });
}
$("budget").addEventListener("change", async (e) => {
  await Themes.enregistrer({ budget_jour_usd: Number(e.target.value) || 1 });
  afficherQuota(await api("/api/consommation"));
});
Themes.surChangement(() => { if ($("reglages").open) majReglages(); });

// ⌘ + T : thème suivant (Ctrl + T sous Windows)
document.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && !e.shiftKey && !e.altKey && e.key.toLowerCase() === "t") {
    e.preventDefault();
    Themes.suivant();
  }
});

// ------------------------------------------------------------ clé API (premier lancement)

function demanderCle() {
  const m = messageChef(
    "Bonjour Monsieur. Pour réfléchir, il me faut votre clé API Anthropic. Créez-la sur platform.claude.com (menu « API Keys »), puis collez-la ici. Elle restera uniquement sur ce Mac.",
    { attente: false }
  );
  m.querySelector(".pied-message")?.remove();
  const form = el("form", "saisie");
  const input = el("input");
  input.type = "password";
  input.placeholder = "sk-ant-…";
  input.autocomplete = "off";
  input.style.cssText = "border:0;outline:0;background:none;width:100%;padding:4px 0 10px";
  const outils = el("div", "outils");
  const erreur = el("span", "discret");
  const ok = el("button", "bouton-accent", "Enregistrer");
  ok.type = "submit";
  outils.append(erreur, el("span", "espace"), ok);
  form.append(input, outils);
  m.append(form);
  input.focus();
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await api("/api/cle", { method: "POST", body: JSON.stringify({ cle: input.value.trim() }) });
      m.remove();
      accueil();
      etat.pret = true;
      bouton.disabled = false;
      champ.focus();
    } catch (err) {
      erreur.textContent = err.message;
    }
  });
}

// ------------------------------------------------------------ démarrage

async function attendreServeur() {
  for (let essai = 0; essai < 60; essai++) {
    try { return await api("/api/sante"); } catch { await new Promise((r) => setTimeout(r, 500)); }
  }
  throw new Error("Serveur injoignable");
}

async function demarrer() {
  bouton.disabled = true;
  $("suggestions").replaceChildren(
    ...SUGGESTIONS.map((s) => {
      const b = el("button", "", s);
      b.type = "button";
      b.addEventListener("click", () => envoyer(s));
      return b;
    })
  );
  accueil();
  try {
    const sante = await attendreServeur();
    await Themes.charger(API);
    construireVignettes();
    $("etat-systeme").textContent = `En ligne · ${sante.systeme} · ${sante.modele_grand_chef}`;
    afficherSections(await api("/api/sections"));
    afficherQuota(await api("/api/consommation"));
    chargerHistorique();
    chargerAgents();
    chargerActions();
    chargerProduits();
    setInterval(chargerActions, 5 * 60 * 1000);
    setInterval(chargerProduits, 30 * 60 * 1000);
    if (sante.cle_api) {
      etat.pret = true;
      bouton.disabled = false;
      champ.focus();
    } else {
      demanderCle();
    }
  } catch {
    $("etat-systeme").textContent = "Hors ligne";
    messageChef("Monsieur, je n'arrive pas à joindre mon serveur local. Quittez Sentinelle (⌘ + Q) puis rouvrez-la.", { erreur: true });
  }
}

function ajusterHauteur() {
  champ.style.height = "auto";
  champ.style.height = Math.min(champ.scrollHeight, 160) + "px";
}

$("formulaire").addEventListener("submit", (e) => { e.preventDefault(); envoyer(); });
champ.addEventListener("input", ajusterHauteur);
champ.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); envoyer(); }
});
$("nouvelle").addEventListener("click", nouvelleDiscussion);
let minuteurRecherche;
$("recherche").addEventListener("input", () => { clearTimeout(minuteurRecherche); minuteurRecherche = setTimeout(chargerHistorique, 250); });
$("periodes").addEventListener("click", (e) => {
  const p = e.target.dataset?.periode;
  if (p) { etat.graphique.periode = p; chargerGraphique(); }
});
$("modifier-actions").addEventListener("click", ouvrirFormulaire);
$("annuler-actions").addEventListener("click", fermerFormulaire);

demarrer();
