// ==UserScript==
// @name         Brocantor — remplisseur Leboncoin
// @namespace    brocantor.local
// @version      1.0.0
// @description  Injecte la prochaine fiche prête (titre/description/prix) dans le formulaire de dépôt Leboncoin. INJECTION DE TEXTE UNIQUEMENT — aucun clic, aucune soumission automatique.
// @match        https://www.leboncoin.fr/deposer-une-annonce*
// @grant        GM_xmlhttpRequest
// @connect      CHANGE-ME.ts.net
// @noframes
// ==/UserScript==

/*
 * LIGNE ROUGE : ce script ne fait QUE remplir des champs texte et déclencher les
 * événements input/change. Il ne clique sur rien, ne soumet rien, ne navigue pas.
 * L'utilisateur glisse les photos et clique « Publier » lui-même.
 */

(function () {
  "use strict";

  // ==========================================================================
  //  CONFIG — SEULE ZONE DE MAINTENANCE.
  //  À ajuster si Leboncoin change son formulaire (voir README, section
  //  « le formulaire a changé »). Remplace CHANGE-ME.ts.net par ton hôte Tailscale
  //  (le même que dans @connect ci-dessus).
  // ==========================================================================
  const CONFIG = {
    appUrl: "https://CHANGE-ME.ts.net", // URL Tailscale de l'app Brocantor (sans / final)
    selectors: {
      // Sélecteurs CSS des champs du formulaire de dépôt Leboncoin.
      // ⚠️ À vérifier/mettre à jour via l'inspecteur si le remplissage échoue.
      titre: 'input[name="subject"], input#subject',
      description: 'textarea[name="body"], textarea#body',
      prix: 'input[name="price"], input#price',
    },
  };
  // ==========================================================================

  // --- Appels à l'app (via GM_xmlhttpRequest, non soumis au CORS navigateur) ---
  function api(method, path) {
    return new Promise(function (resolve, reject) {
      GM_xmlhttpRequest({
        method: method,
        url: CONFIG.appUrl + path,
        headers: { "Content-Type": "application/json" },
        data: arguments.length > 2 ? arguments[2] : undefined,
        onload: function (r) {
          resolve({ status: r.status, text: r.responseText });
        },
        onerror: function () { reject(new Error("réseau (app injoignable ?)")); },
        ontimeout: function () { reject(new Error("délai dépassé")); },
        timeout: 15000,
      });
    });
  }

  // --- Remplissage d'un champ + événements pour que le front LBC enregistre ----
  function remplir(selector, valeur) {
    const el = document.querySelector(selector);
    if (!el) return false;
    // Passe par le setter natif : les frameworks (React) écoutent ce chemin.
    const proto = el.tagName === "TEXTAREA"
      ? window.HTMLTextAreaElement.prototype
      : window.HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value");
    if (setter && setter.set) setter.set.call(el, valeur == null ? "" : String(valeur));
    else el.value = valeur == null ? "" : String(valeur);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  }

  // --- UI : panneau flottant ---------------------------------------------------
  const panel = document.createElement("div");
  panel.id = "brocantor-panel";
  panel.style.cssText = [
    "position:fixed", "right:16px", "bottom:16px", "z-index:2147483647",
    "width:300px", "max-width:90vw", "background:#1b1f24", "color:#e8ebed",
    "border:1px solid #2e353d", "border-radius:14px", "padding:14px",
    "font:14px -apple-system,Segoe UI,Roboto,sans-serif",
    "box-shadow:0 8px 30px rgba(0,0,0,.5)",
  ].join(";");
  document.body.appendChild(panel);

  function bouton(label, bg) {
    const b = document.createElement("button");
    b.textContent = label;
    b.style.cssText = "display:block;width:100%;margin-top:8px;padding:10px;border-radius:10px;border:none;font-weight:700;cursor:pointer;background:" + (bg || "#242a31") + ";color:" + (bg ? "#06152b" : "#e8ebed");
    return b;
  }

  let ficheCourante = null;

  function ligneManuel(label, valeur) {
    const wrap = document.createElement("div");
    wrap.style.cssText = "margin-top:8px;padding:8px;background:#242a31;border-radius:8px";
    const t = document.createElement("div");
    t.style.cssText = "font-size:12px;color:#9aa4ad;margin-bottom:4px";
    t.textContent = label;
    const v = document.createElement("div");
    v.style.cssText = "word-break:break-word";
    v.textContent = valeur == null ? "—" : String(valeur);
    const copier = bouton("Copier", null);
    copier.style.marginTop = "6px";
    copier.style.padding = "6px";
    copier.addEventListener("click", function () {
      navigator.clipboard && navigator.clipboard.writeText(String(valeur || ""));
      copier.textContent = "Copié ✓";
      setTimeout(function () { copier.textContent = "Copier"; }, 1500);
    });
    wrap.appendChild(t); wrap.appendChild(v); wrap.appendChild(copier);
    return wrap;
  }

  function rendreAccueil(restantes) {
    panel.innerHTML = "";
    const titre = document.createElement("div");
    titre.style.cssText = "font-weight:800;margin-bottom:4px";
    titre.textContent = "🜂 Brocantor";
    const sub = document.createElement("div");
    sub.style.cssText = "color:#9aa4ad;font-size:13px";
    sub.textContent = restantes + " fiche(s) prête(s)";
    panel.appendChild(titre); panel.appendChild(sub);
    if (restantes > 0) {
      const b = bouton("Remplir la prochaine fiche", "#4c9aff");
      b.addEventListener("click", remplirProchaine);
      panel.appendChild(b);
    }
  }

  function messageErreur(msg) {
    const e = document.createElement("div");
    e.style.cssText = "margin-top:8px;color:#ffb3ad;font-size:13px";
    e.textContent = "⚠️ " + msg;
    panel.appendChild(e);
  }

  // --- Actions -----------------------------------------------------------------
  function rafraichir() {
    return api("GET", "/api/publication/next").then(function (r) {
      if (r.status === 204) { ficheCourante = null; rendreAccueil(0); return; }
      const data = JSON.parse(r.text);
      ficheCourante = data;
      rendreAccueil(data.restantes);
    }).catch(function (e) {
      panel.innerHTML = "<div style='font-weight:800'>🜂 Brocantor</div>";
      messageErreur(e.message + " — vérifie CONFIG.appUrl.");
    });
  }

  function remplirProchaine() {
    if (!ficheCourante) { rafraichir(); return; }
    const f = ficheCourante;
    panel.innerHTML = "";
    const h = document.createElement("div");
    h.style.cssText = "font-weight:800;margin-bottom:6px";
    h.textContent = "🜂 " + (f.titre || "Fiche");
    panel.appendChild(h);

    const remplis = [];
    const manuels = [];
    if (remplir(CONFIG.selectors.titre, f.titre)) remplis.push("titre"); else manuels.push(["Titre", f.titre]);
    if (remplir(CONFIG.selectors.description, f.description)) remplis.push("description"); else manuels.push(["Description", f.description]);
    if (remplir(CONFIG.selectors.prix, f.prix_choisi)) remplis.push("prix"); else manuels.push(["Prix", f.prix_choisi]);

    const ok = document.createElement("div");
    ok.style.cssText = "color:#7ee787;font-size:13px";
    ok.textContent = remplis.length ? "Rempli : " + remplis.join(", ") : "Aucun champ auto-rempli.";
    panel.appendChild(ok);

    // Catégorie : à sélectionner à la main (les listes déroulantes LBC varient).
    panel.appendChild(ligneManuel("Catégorie à sélectionner", f.categorie_lbc));

    // Champs non trouvés → copier à la main.
    manuels.forEach(function (m) { panel.appendChild(ligneManuel(m[0] + " (à coller)", m[1])); });

    // Lien photos.
    const dl = bouton("⬇ Télécharger les photos (.zip)", null);
    dl.addEventListener("click", function () {
      window.open(CONFIG.appUrl + f.photos_zip_url, "_blank");
    });
    panel.appendChild(dl);

    const note = document.createElement("div");
    note.style.cssText = "margin-top:8px;color:#9aa4ad;font-size:12px";
    note.textContent = "Glisse les photos et clique « Publier » toi-même.";
    panel.appendChild(note);

    const pub = bouton("Annonce publiée ✓", "#3fb950");
    pub.addEventListener("click", function () { marquerPubliee(f.id); });
    panel.appendChild(pub);

    const skip = bouton("↻ Rafraîchir", null);
    skip.addEventListener("click", rafraichir);
    panel.appendChild(skip);
  }

  function marquerPubliee(id) {
    const url = prompt("URL de l'annonce publiée (optionnel) :", location.href);
    const body = JSON.stringify({ url_annonce: url || "" });
    api("POST", "/api/publication/" + id + "/publiee", body).then(function (r) {
      if (r.status >= 200 && r.status < 300) { rafraichir(); }
      else { messageErreur("Clôture refusée (" + r.status + ")."); }
    }).catch(function (e) { messageErreur(e.message); });
  }

  // Démarrage.
  rafraichir();
})();
