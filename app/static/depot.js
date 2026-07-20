// Dépôt mobile (T02) : compression canvas + upload robuste, JS vanilla.
(function () {
  "use strict";

  var MAX_PHOTOS = 5;
  var MAX_SIDE = 1600;   // côté max après redimensionnement
  var JPEG_Q = 0.85;
  var TIMEOUT_MS = 120000; // 2 min : généreux pour la 4G

  // File compressée en attente d'envoi : { blob, url (objectURL pour l'aperçu) }.
  var selection = [];
  var sessionCount = 0;
  var enCours = false;

  var input = document.getElementById("input-photos");
  var vignettes = document.getElementById("vignettes");
  var note = document.getElementById("note");
  var btnEnvoyer = document.getElementById("btn-envoyer");
  var form = document.getElementById("depot-form");
  var progressWrap = document.getElementById("progress-wrap");
  var progressFill = document.getElementById("progress-fill");
  var progressTxt = document.getElementById("progress-txt");
  var echec = document.getElementById("echec");
  var echecMsg = document.getElementById("echec-msg");
  var btnReessayer = document.getElementById("btn-reessayer");
  var compteur = document.getElementById("compteur");
  var toast = document.getElementById("toast");

  // --- Compression via canvas -----------------------------------------------
  function compresser(file) {
    return new Promise(function (resolve, reject) {
      var img = new Image();
      var objectUrl = URL.createObjectURL(file);
      img.onload = function () {
        var w = img.naturalWidth, h = img.naturalHeight;
        var scale = Math.min(1, MAX_SIDE / Math.max(w, h));
        var cw = Math.round(w * scale), ch = Math.round(h * scale);
        var canvas = document.createElement("canvas");
        canvas.width = cw; canvas.height = ch;
        var ctx = canvas.getContext("2d");
        ctx.drawImage(img, 0, 0, cw, ch);
        URL.revokeObjectURL(objectUrl);
        canvas.toBlob(function (blob) {
          if (!blob) { reject(new Error("compression échouée")); return; }
          resolve(blob);
        }, "image/jpeg", JPEG_Q);
      };
      img.onerror = function () {
        URL.revokeObjectURL(objectUrl);
        reject(new Error("image illisible"));
      };
      img.src = objectUrl;
    });
  }

  // --- Aperçu vignettes ------------------------------------------------------
  function rendreVignettes() {
    vignettes.innerHTML = "";
    selection.forEach(function (item, i) {
      var cell = document.createElement("div");
      cell.className = "vignette";
      var im = document.createElement("img");
      im.src = item.url;
      im.alt = "photo " + (i + 1);
      var del = document.createElement("button");
      del.type = "button";
      del.className = "vignette-del";
      del.setAttribute("aria-label", "Supprimer");
      del.textContent = "×";
      del.addEventListener("click", function () { retirer(i); });
      var pos = document.createElement("span");
      pos.className = "vignette-pos";
      pos.textContent = i + 1;
      cell.appendChild(im);
      cell.appendChild(pos);
      cell.appendChild(del);
      vignettes.appendChild(cell);
    });
    btnEnvoyer.disabled = enCours || selection.length === 0;
  }

  function retirer(i) {
    var item = selection.splice(i, 1)[0];
    if (item) URL.revokeObjectURL(item.url);
    rendreVignettes();
  }

  // --- Sélection de fichiers -------------------------------------------------
  input.addEventListener("change", function () {
    var files = Array.prototype.slice.call(input.files || []);
    input.value = ""; // permet de re-sélectionner le même fichier
    var libres = MAX_PHOTOS - selection.length;
    if (libres <= 0) { afficherToast("Maximum " + MAX_PHOTOS + " photos"); return; }
    files.slice(0, libres).forEach(function (f) {
      compresser(f).then(function (blob) {
        selection.push({ blob: blob, url: URL.createObjectURL(blob) });
        rendreVignettes();
      }).catch(function () {
        afficherToast("Photo ignorée (illisible)");
      });
    });
  });

  // --- Toast -----------------------------------------------------------------
  var toastTimer = null;
  function afficherToast(msg) {
    toast.textContent = msg;
    toast.hidden = false;
    toast.classList.add("show");
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      toast.classList.remove("show");
      setTimeout(function () { toast.hidden = true; }, 300);
    }, 2500);
  }

  function majCompteur() {
    if (sessionCount > 0) {
      compteur.hidden = false;
      compteur.textContent = sessionCount + " envoyé" + (sessionCount > 1 ? "s" : "");
    }
  }

  // --- Envoi -----------------------------------------------------------------
  function envoyer() {
    if (enCours || selection.length === 0) return;
    enCours = true;
    echec.hidden = true;
    btnEnvoyer.disabled = true;
    progressWrap.hidden = false;
    progressFill.style.width = "0%";
    progressTxt.textContent = "Envoi…";

    var fd = new FormData();
    fd.append("note", note.value || "");
    selection.forEach(function (item, i) {
      fd.append("photos", item.blob, "photo_" + i + ".jpg");
    });

    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/depot");
    xhr.timeout = TIMEOUT_MS;
    xhr.upload.onprogress = function (e) {
      if (e.lengthComputable) {
        var pct = Math.round((e.loaded / e.total) * 100);
        progressFill.style.width = pct + "%";
        progressTxt.textContent = "Envoi… " + pct + "%";
      }
    };
    xhr.onload = function () {
      enCours = false;
      progressWrap.hidden = true;
      if (xhr.status >= 200 && xhr.status < 300) {
        sessionCount += 1;
        succes();
      } else {
        var msg = "Erreur serveur (" + xhr.status + ")";
        try { msg = JSON.parse(xhr.responseText).erreur || msg; } catch (e) {}
        montrerEchec(msg);
      }
    };
    xhr.onerror = function () { enCours = false; progressWrap.hidden = true; montrerEchec("Réseau indisponible"); };
    xhr.ontimeout = function () { enCours = false; progressWrap.hidden = true; montrerEchec("Délai dépassé"); };
    xhr.send(fd);
  }

  function succes() {
    afficherToast("Produit #" + sessionCount + " envoyé ✓");
    majCompteur();
    // Reset pour l'objet suivant, sans recharger la page.
    selection.forEach(function (item) { URL.revokeObjectURL(item.url); });
    selection = [];
    note.value = "";
    rendreVignettes();
  }

  function montrerEchec(msg) {
    // On garde la sélection : l'utilisateur peut réessayer sans re-photographier.
    echecMsg.textContent = msg + " — vos photos sont conservées.";
    echec.hidden = false;
    btnEnvoyer.disabled = selection.length === 0;
  }

  form.addEventListener("submit", function (e) { e.preventDefault(); envoyer(); });
  btnReessayer.addEventListener("click", function () { echec.hidden = true; envoyer(); });

  rendreVignettes();
})();
