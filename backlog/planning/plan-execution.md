# Plan d'exécution — Brocantor

Ordre d'exécution des tickets, avec parallélisation par subagents quand les périmètres de fichiers sont disjoints. Chaque agent reçoit comme prompt : le contenu de son ticket `backlog/tickets/T0X-*.md` + l'instruction de lire `CLAUDE.md` d'abord et de mettre à jour `backlog/backlog.md` en fin de ticket.

## Vue d'ensemble

```
Phase 0        Phase 1 (3 subagents ∥)      Phase 2 (2 subagents ∥)     Phase 3 (2 subagents ∥)
┌─────┐        ┌─────┐                       ┌─────┐
│ T01 │──┬────▶│ T02 │──────────┬───────────▶│ T03 │
└─────┘  │     └─────┘          │            └─────┘                    ┌─────┐
         ├────▶┌─────┐          │                                  ┌───▶│ T07 │
         │     │ T04 │──────────┼───────────▶┌─────┐               │    └─────┘
         │     └─────┘          │            │ T06 │───────────────┤
         └────▶┌─────┐          │            └─────┘               │    ┌─────┐
               │ T05 │──────────┘                                  └───▶│ T08 │
               └─────┘                                                  └─────┘
```

## Phase 0 — Fondations (séquentiel, bloquant)

**T01 — Socle applicatif.** Un seul agent. Rien ne peut démarrer avant : T01 crée le schéma, la machine à états, le layout et surtout les **routers vides qui délimitent les territoires** des agents suivants. Vérifier ses critères d'acceptation avant de lancer la phase 1 (en particulier : seed OK, transitions illégales refusées).

## Phase 1 — Les trois écrans (3 subagents en parallèle)

| Subagent | Ticket | Territoire fichiers |
|----------|--------|---------------------|
| A | T02 Dépôt mobile | `routers/depot.py`, `templates/depot*`, `static/depot.js`, manifest |
| B | T04 Fiches produits | `routers/produits.py`, `templates/produits*` |
| C | T05 Dashboard | `routers/dashboard.py`, `templates/dashboard*` |

Parallélisables car : périmètres de fichiers strictement disjoints (délimités par T01), et T04/T05 travaillent sur les données du seed sans dépendre de l'upload réel ni de l'IA. Règles : aucun agent ne modifie `main.py`/`db.py`/`models.py`/`base.html` (exception : T02 a droit à UNE ligne dans `base.html` pour le manifest) ; en cas de besoin transverse, le noter dans le backlog plutôt que de sortir de son territoire.

**Point de synchro fin de phase 1** : lancer l'app, vérifier que les trois écrans coexistent (pas de collision de routes/templates), faire le tour des critères d'acceptation. C'est le premier moment où l'app est montrable.

## Phase 2 — Le moteur et le fallback (2 subagents en parallèle)

| Subagent | Ticket | Pourquoi maintenant |
|----------|--------|---------------------|
| D | T03 Worker IA | A besoin de vrais produits déposés (T02) pour ses tests de bout en bout |
| E | T06 Pack de publication | A besoin des fiches et de l'état `prete` (T04) |

Territoires disjoints (`worker.py`/`analyse.py`/`images.py` vs `routers/publication.py`/templates). Les deux touchent `routers/api.py` ? Non : seul T03 y ajoute sa route `relancer` (section commentée `# T03`) — pas de conflit avec E.

**Point de synchro fin de phase 2 = POC complet** : parcours réel photographier → fiche IA → valider → publier en copier-coller. **Faire ici le test grandeur nature : un batch de 10 vrais objets**, pour juger la qualité des fiches IA et itérer sur le prompt de `analyse.py` avant la phase 3.

## Phase 3 — Confort et industrialisation (2 subagents en parallèle)

| Subagent | Ticket | Territoire |
|----------|--------|-----------|
| F | T07 Userscript | `userscript/`, `routers/api.py` section `# T07` |
| G | T08 Déploiement | `deploy/`, `routers/api.py` section `# T08` |

Attention au seul chevauchement du plan : F et G ajoutent chacun des routes dans `routers/api.py`. Sections commentées distinctes (`# T07` / `# T08`), chacun n'écrit que dans la sienne ; si les agents tournent dans des worktrees isolés, le merge est trivial (additions disjointes).

## Récapitulatif charge

| Phase | Tickets | Durée (calendaire, avec parallélisation) |
|-------|---------|------------------------------------------|
| 0 | T01 | ½ j |
| 1 | T02 ∥ T04 ∥ T05 | ~1 j (durée du plus long : T02) |
| 2 | T03 ∥ T06 | ~1–1,5 j (durée de T03) |
| 3 | T07 ∥ T08 | ~½–1 j |
| **Total** | | **~3 à 4 jours** (vs 4,5–6 j en séquentiel) |

## Consignes d'orchestration des subagents

1. Prompt de chaque agent = son fichier ticket, précédé de : « Tu travailles sur le projet Brocantor. Lis d'abord `CLAUDE.md` puis `docs/cahier-des-charges.md`. Respecte STRICTEMENT ton périmètre de fichiers. À la fin : vérifie tes critères d'acceptation réellement, mets à jour `backlog/backlog.md` (statut + une ligne de commentaire), et liste ce que tu n'as pas pu vérifier. »
2. Après chaque phase, l'orchestrateur (ou l'humain) exécute les points de synchro avant de lancer la suivante — ne jamais empiler deux phases sans vérification.
3. Un agent bloqué (dépendance manquante, critère invérifiable) le note dans le backlog et s'arrête proprement plutôt que d'improviser hors périmètre.
4. Les critères marqués « vérifié par l'utilisateur » (test 4G, page Leboncoin réelle, PWA sur iPhone) sont à sortir du chemin des agents : les regrouper pour une session de test humaine par phase.
