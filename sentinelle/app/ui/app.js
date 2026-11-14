// Sentinelle — interface. Parle au serveur local Python (127.0.0.1:8765).
"use strict";

const PORT = 8765;
const SERVI_PAR_LE_SERVEUR = location.protocol.startsWith("http") && location.port === String(PORT);
const API = SERVI_PAR_LE_SERVEUR ? "" : `http://127.0.0.1:${PORT}`;

const $ = (id) => document.getElementById(id);
const fil = $("fil");
const champ = $("message");
const bouton = $("envoyer");

if (window.__TAURI_INTERNALS__) document.body.classList.add("tauri");
document.documentElement.dataset.theme = "sombre"; // mode sombre par défaut

async function api(chemin, options = {}) {
  const r = await fetch(API + chemin, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (!r.ok) throw new Error(`Erreur ${r.status}`);
  return r.json();
}

function ajouterBulle(texte, qui, { meta = "", erreur = false, attente = false } = {}) {
  const b = document.createElement("div");
  b.className = `bulle ${qui}` + (erreur ? " erreur" : "") + (attente ? " attente" : "");
  // **gras** → <strong>, sans jamais interpréter de HTML venant de la réponse.
  texte.split(/\*\*(.+?)\*\*/gs).forEach((morceau, i) => {
    if (i % 2) {
      const fort = document.createElement("strong");
      fort.textContent = morceau;
      b.appendChild(fort);
    } else if (morceau) {
      b.appendChild(document.createTextNode(morceau));
    }
  });
  if (meta) {
    const m = document.createElement("span");
    m.className = "meta";
    m.textContent = meta;
    b.appendChild(m);
  }
  fil.appendChild(b);
  fil.scrollTop = fil.scrollHeight;
  return b;
}

function afficherConso(c) {
  if (!c) return;
  const tokens = (c.tokens_entree + c.tokens_sortie).toLocaleString("fr-CH");
  $("conso").textContent = `Aujourd'hui : ${tokens} tokens · ${c.cout_usd.toFixed(4)} $`;
}

function afficherSections(sections) {
  const libelles = { active: "active", en_preparation: "en préparation", a_construire: "à construire" };
  const ul = $("liste-sections");
  ul.replaceChildren(
    ...sections.map((s) => {
      const li = document.createElement("li");
      li.className = s.statut;
      li.title = `${s.commandant} — ${libelles[s.statut]}`;
      const icone = document.createElement("span");
      icone.textContent = s.icone;
      const nom = document.createElement("span");
      nom.className = "nom";
      nom.textContent = s.nom;
      const point = document.createElement("i");
      point.className = `point ${s.statut}`;
      li.append(icone, nom, point);
      return li;
    })
  );
}

// Attend que le serveur Python soit prêt (il démarre en même temps que la fenêtre).
async function attendreServeur() {
  for (let essai = 0; essai < 60; essai++) {
    try {
      return await api("/api/sante");
    } catch {
      await new Promise((r) => setTimeout(r, 500));
    }
  }
  throw new Error("Serveur injoignable");
}

async function demarrer() {
  bouton.disabled = true;
  try {
    const sante = await attendreServeur();
    $("etat-systeme").textContent = `En ligne · ${sante.systeme}`;
    $("modele-chef").textContent = `JARVIS · ${sante.modele_grand_chef}`;
    afficherSections(await api("/api/sections"));
    afficherConso(await api("/api/consommation"));
    chargerActions();
    setInterval(chargerActions, 5 * 60 * 1000); // toutes les 5 minutes
    ajouterBulle(
      sante.cle_api
        ? "Bonjour Monsieur. Tous les systèmes sont opérationnels. Que puis-je faire pour vous ?"
        : "Bonjour Monsieur. Mes systèmes sont en ligne, mais ma clé API est absente : je ne peux pas encore réfléchir. Le guide README explique comment l'ajouter.",
      "chef",
      { erreur: !sante.cle_api }
    );
    bouton.disabled = false;
    champ.focus();
  } catch {
    $("etat-systeme").textContent = "Hors ligne";
    ajouterBulle(
      "Monsieur, je n'arrive pas à joindre le serveur local. Lancez Sentinelle avec « Demarrer-Mac.command ».",
      "chef",
      { erreur: true }
    );
  }
}

async function envoyer(e) {
  e.preventDefault();
  const texte = champ.value.trim();
  if (!texte || bouton.disabled) return;
  champ.value = "";
  ajusterHauteur();
  ajouterBulle(texte, "moi");
  const attente = ajouterBulle("Je m'en occupe, Monsieur", "chef", { attente: true });
  bouton.disabled = true;
  try {
    const r = await api("/api/chat", { method: "POST", body: JSON.stringify({ message: texte }) });
    attente.remove();
    const aides = r.intervenants.length > 1 ? ` · ${r.intervenants.length} appels` : "";
    const meta = r.erreur
      ? ""
      : `${(r.duree_ms / 1000).toFixed(1)} s${aides} · ${r.tokens.toLocaleString("fr-CH")} tokens · ${r.cout_usd.toFixed(4)} $`;
    ajouterBulle(r.reponse, "chef", { meta, erreur: r.erreur });
    afficherConso(r.consommation);
  } catch {
    attente.remove();
    ajouterBulle("Toutes mes excuses, Monsieur : le serveur local ne répond plus.", "chef", { erreur: true });
  } finally {
    bouton.disabled = false;
    champ.focus();
  }
}

function ajusterHauteur() {
  champ.style.height = "auto";
  champ.style.height = Math.min(champ.scrollHeight, 140) + "px";
}

$("formulaire").addEventListener("submit", envoyer);
champ.addEventListener("input", ajusterHauteur);
champ.addEventListener("keydown", (e) => {
  // Entrée = envoyer ; Maj+Entrée = nouvelle ligne
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) envoyer(e);
});

// ------------------------------------------------------------ Carte « Mes actions »

const fmt = (n, dec = 2) => n.toLocaleString("fr-CH", { minimumFractionDigits: dec, maximumFractionDigits: dec });
const signe = (n) => (n > 0 ? "+" : "") + fmt(n);
const devise = (d) => (d === "GBp" ? "p" : d);

function el(tag, classe, texte) {
  const e = document.createElement(tag);
  if (classe) e.className = classe;
  if (texte !== undefined) e.textContent = texte;
  return e;
}

async function chargerActions() {
  const zone = $("actions-contenu");
  try {
    const res = await api("/api/bourse/mes-actions");
    zone.className = "";
    const lignes = res.positions.map((p) => {
      const ligne = el("div", "ligne-action");
      ligne.title = p.date_cours ? `Cours du ${p.date_cours}` : "";
      ligne.append(el("div", "nom-action", p.nom));
      ligne.append(el("div", "prix", p.prix == null ? "—" : `${fmt(p.prix)} ${devise(p.devise)}`));
      const detail = p.valeur_chf != null
        ? `${fmt(p.quantite, 0)} pièces · ${fmt(p.valeur_chf)} CHF` + (p.gain_pct != null ? ` · ${signe(p.gain_pct)} %` : "")
        : p.ticker;
      ligne.append(el("div", "detail", detail));
      const v = p.variation_jour_pct;
      ligne.append(el("div", "var " + (v > 0 ? "hausse" : v < 0 ? "baisse" : ""), v == null ? "" : `${signe(v)} %`));
      return ligne;
    });
    zone.replaceChildren(...lignes);
    if (res.positions.some((p) => p.valeur_chf != null)) {
      const total = el("div", "total-actions");
      total.append(el("span", "", "Total"), el("span", "", `${fmt(res.valeur_totale_chf)} CHF`));
      zone.append(total);
    }
  } catch {
    zone.className = "carte-vide";
    zone.textContent = "Cours indisponibles pour le moment.";
  }
}

async function ouvrirFormulaire() {
  const pf = await api("/api/portefeuille");
  const champs = $("actions-champs");
  champs.replaceChildren(
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
  $("actions-contenu").hidden = true;
  $("actions-formulaire").hidden = false;
}

function fermerFormulaire() {
  $("actions-formulaire").hidden = true;
  $("actions-contenu").hidden = false;
}

$("modifier-actions").addEventListener("click", ouvrirFormulaire);
$("annuler-actions").addEventListener("click", fermerFormulaire);
$("actions-formulaire").addEventListener("submit", async (e) => {
  e.preventDefault();
  const formulaire = e.currentTarget;
  const pf = JSON.parse(formulaire.dataset.portefeuille);
  for (const input of formulaire.querySelectorAll("input")) {
    pf.positions[input.dataset.index][input.dataset.cle] = input.value === "" ? null : Number(input.value);
  }
  try {
    const r = await fetch(API + "/api/portefeuille", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(pf),
    });
    if (!r.ok) {
      $("actions-erreur").textContent = (await r.json()).detail || "Erreur.";
      return;
    }
    fermerFormulaire();
    chargerActions();
  } catch {
    $("actions-erreur").textContent = "Serveur injoignable.";
  }
});

demarrer();
