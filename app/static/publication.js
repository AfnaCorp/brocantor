// Pack de publication (T06) : boutons « Copier » avec feedback + suivi des blocs copiés.
(function () {
  "use strict";

  function copier(texte) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(texte);
    }
    // Fallback navigateurs anciens / contexte non sécurisé.
    return new Promise(function (resolve, reject) {
      try {
        var ta = document.createElement("textarea");
        ta.value = texte;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
        resolve();
      } catch (e) { reject(e); }
    });
  }

  document.querySelectorAll(".btn-copier[data-copy]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      copier(btn.getAttribute("data-copy") || "").then(function () {
        var label = btn.textContent;
        btn.textContent = "Copié ✓";
        btn.classList.add("ok");
        var bloc = btn.closest("[data-bloc]");
        if (bloc) bloc.classList.add("copie");
        setTimeout(function () {
          btn.textContent = label;
          btn.classList.remove("ok");
        }, 2000);
      }).catch(function () {
        btn.textContent = "Échec copie";
        setTimeout(function () { btn.textContent = "Copier"; }, 2000);
      });
    });
  });
})();
