# My Social Networks API

Ce projet propose une API REST inspirée de Facebook permettant de créer et gérer des événements (publics/privés), des groupes (public, privé, secret) et leurs fils de discussion. Elle prend en charge les participants, organisateurs/administrateurs, albums photo avec commentaires, sondages à choix unique, ainsi qu’une billetterie (types de billets, achat externe, quotas). Des bonus incluent la shopping list (apports uniques par événement) et le covoiturage (trajets, places, prix, tolérance de détour). 

L’API applique des techniques de sécurité telles que l’authentification et l’autorisation via JWT, la validation des entrées, la sécurisation des communications avec HTTPS, la limitation des requêtes, et la gestion des erreurs.

Plus de détails : [Consulter le cahier des charges](./My_Social_Networks_API.pdf)


---

## Sommaire
1. [Stack & architecture](#stack--architecture)
2. [Fonctionnalités](#fonctionnalités)
3. [Mise en route](#mise-en-route)
4. [Configuration](#configuration)
5. [Sécurité intégrée](#sécurité-intégrée)
6. [Tests & audit](#tests--audit)
7. [Roadmap / améliorations](#roadmap--améliorations)
8. [Références](#références)

---

## Stack & architecture

| Couche | Technologies | Raison du choix |
|--------|--------------|-----------------|
| API | **FastAPI** (async) | Performance, typage, documentation interactive automatique. |
| ORM | **SQLModel** (SQLAlchemy 2.x) | Combine Pydantic + SQLAlchemy, réduit le boilerplate. |
| Auth | **OAuth2 password flow + JWT** | Compatible SPA/mobile, stateless et facilement testable. |
| DB (dev) | **SQLite + aiosqlite** | Simplicité pour le prototypage, switchable via `DATABASE_URL`. |
| Tests | **pytest, pytest-asyncio, httpx** | Permet de rejouer un flux utilisateur complet. |
| Sécurité | **slowapi**, **secure**, validations Pydantic | Rate limiting, headers type Helmet, normalisation des entrées. |

Organisation du code (extrait) :
```
app/
├─ core/        # configuration, sécurité (JWT, rate limit, headers)
├─ routers/     # routes classées par domaine (auth, groups, events, …)
├─ schemas.py   # contrats Pydantic
├─ models.py    # SQLModel
├─ database.py  # connexion async + transactions
└─ main.py      # point d’entrée FastAPI + middlewares
tests/
├─ test_app.py        # scénario fonctionnel complet
└─ test_security.py   # tests ciblés (password policy, rate limit)
```

---

## Fonctionnalités

- **Authentification & profils** : inscription, login, JWT avec claims `iss/aud/iat/exp`, endpoint `/api/users/me`.
- **Groupes** : création, adhésions avec rôles (admin, droit de créer des événements), listing détaillé des membres.
- **Événements** : organisateurs multiples, participants, options activables (polls, billetterie, shopping, covoiturage).
- **Discussions** : fils attachés à un groupe ou un événement, messages hiérarchiques.
- **Médias** : albums liés aux événements, photos, commentaires.
- **Sondages** : questions/options multiples, votes traçables par participant.
- **Billetterie** : types de billets, achat avec contrôle de quota et d’unicité email.
- **Addons** : shopping list collaborative, offres de covoiturage.
- **Gestion des erreurs** : réponses normalisées `{"error": "...", "detail": ...}` quelle que soit l’origine de l’exception.

Le test `tests/test_app.py` illustre ce parcours de bout en bout.

---

## Mise en route

```bash
# 1. Créer un environnement isolé (recommandé)
python -m venv .venv
. .venv/Scripts/activate        # Windows PowerShell
# source .venv/bin/activate     # macOS/Linux

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Démarrer l’API en mode dev
uvicorn app.main:app --reload
# Documentation : http://127.0.0.1:8000/docs
```

Pour un test HTTPS local :
```bash
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout key.pem -out cert.pem -days 365 -subj "/CN=localhost"
uvicorn app.main:app --ssl-keyfile=key.pem --ssl-certfile=cert.pem
```
Activer ensuite `ENABLE_HTTPS_REDIRECT=true` dans l’environnement.

---

## Configuration

Créer un fichier `.env` à la racine si nécessaire. Principales variables :

| Variable | Rôle | Valeur par défaut |
|----------|------|-------------------|
| `SECRET_KEY` | Signature JWT | `change-me` |
| `DATABASE_URL` | Connexion SQLAlchemy | `sqlite+aiosqlite:///./app.db` |
| `ALLOWED_ORIGINS` | Whitelist CORS | `*` (à restreindre en prod) |
| `ALLOWED_HOSTS` | Filtre `TrustedHostMiddleware` | `*` |
| `ENABLE_HTTPS_REDIRECT` | Force HTTPS | `false` |
| `CONTENT_SECURITY_POLICY`, `PERMISSIONS_POLICY`, `REFERRER_POLICY` | Headers sécurité personnalisables | Valeurs strictes adaptées aux SPA |
| `RATE_LIMIT_DEFAULT` | Limite globale SlowAPI | `100/hour` |
| `RATE_LIMIT_AUTH`, `RATE_LIMIT_REGISTER` | Limites dédiées aux endpoints sensibles | `20/minute`, `5/hour` |
| `TOKEN_ISSUER`, `TOKEN_AUDIENCE` | Claims exigés pour décoder les JWT | `my-social-networks-api`, `my-social-networks-clients` |

Exemple `.env` minimal :
```ini
SECRET_KEY=change-me
DATABASE_URL=sqlite+aiosqlite:///./app.db
ALLOWED_ORIGINS=["http://localhost:3000"]
ALLOWED_HOSTS=["localhost","127.0.0.1"]
ENABLE_HTTPS_REDIRECT=false
RATE_LIMIT_DEFAULT=100/hour
RATE_LIMIT_AUTH=20/minute
RATE_LIMIT_REGISTER=5/hour
```

---

## Sécurité intégrée

1. **Headers type Helmet** : via la bibliothèque `secure` + middleware custom (HSTS, X-Content-Type-Options, X-Frame-Options, CSP, Permissions Policy, Referrer Policy).
2. **Trusted hosts & HTTPS** : `TrustedHostMiddleware` + option de redirection automatique pour bloquer les requêtes non autorisées.
3. **JWT** : tokens enrichis (`iat`, `exp`, `iss`, `aud`) et vérification centralisée via `decode_access_token`/`get_current_user`.
4. **Validation & hygiène** : Pydantic normalise les champs texte, impose des `AnyHttpUrl`, vérifie la complexité des mots de passe et les règles métier.
5. **Rate limiting** : `slowapi` applique une limite globale et des quotas spécifiques aux routes d’authentification pour réduire brute force/DDoS applicatif.
6. **Gestion des erreurs** : handlers dédiés pour HTTPException, validation Pydantic, RateLimitExceeded et erreurs générales, afin de ne jamais exposer les stacks.
7. **Audit des dépendances** : `pip-audit` recommandé. Les dépendances critiques (ex. `python-jose`, `python-multipart`) ont été mises à jour ; les vulnérabilités liées à l’environnement Anaconda doivent être traitées côté poste (virtualenv propre conseillé).

---

## Tests & audit

| Commande | Description |
|----------|-------------|
| `pytest` | Lance le test end-to-end + les tests ciblés sécurité. |
| `pip-audit` | Analyse les dépendances Python à la recherche de CVE connues. |

Les warnings Pydantic (migration complète vers v2) sont connus et listés comme axe d’amélioration.

---

## Roadmap / améliorations

1. **Migration Pydantic v2 “pure”** : remplacer les anciennes configurations `Config` par `model_config` et supprimer `from_orm` pour éliminer les warnings.
2. **Storage rate limit distribué** : brancher SlowAPI sur Redis/Memcached pour supporter plusieurs instances.
3. **Pagination & filtres** : indispensable pour l’UX lorsque le volume d’événements/discussions augmente.
4. **CI/CD** : ajouter un pipeline (lint, tests, pip-audit) avant déploiement.
5. **Gestion avancée des tokens** : intégration d’un rafraîchissement et d’une stratégie de révocation/rotation de clés.

Contributions bienvenues : ouvrir une issue ou proposer une pull request avec description claire, tests associés et mise à jour de la documentation si nécessaire.

---

## Références

- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLModel](https://sqlmodel.tiangolo.com/)
- [SlowAPI](https://github.com/laurents/slowapi)
- [pip-audit](https://github.com/pypa/pip-audit)

Projet réalisé dans le cadre du module API & Web Services (Mastere DE AI 2025‑2027).

