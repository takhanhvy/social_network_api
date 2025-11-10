# My Social Networks API

Plateforme REST écrite avec **FastAPI + SQLModel** pour couvrir l’ensemble du cahier des charges “My Social Networks” : gestion des utilisateurs, groupes, événements, discussions, médias, sondages, billetterie et extensions (shopping list, covoiturage). L’objectif principal est de proposer une API riche tout en garantissant un niveau de sécurité comparable à des services exposés publiquement.

---

## 1. Architecture en un coup d’œil

```
.
├── app
│   ├── core/            # Configuration, sécurité (JWT, rate limiting, headers)
│   ├── routers/         # Routes par domaine métier (auth, groups, events, …)
│   ├── schemas.py       # Contrats Pydantic (validation stricte + normalisation)
│   ├── models.py        # Modèles SQLModel (SQLAlchemy 2.x)
│   ├── database.py      # Connexion async + gestion des transactions
│   └── main.py          # Point d’entrée FastAPI / middlewares
├── tests/               # Scénarios end‑to‑end et tests de sécurité
├── requirements.txt     # Dépendances figées
├── pytest.ini
└── README.md
```

**Justification des choix techniques**
- *FastAPI + SQLModel (async)* : typage strict, performances élevées, intégration transparente avec SQLAlchemy 2.x.
- *Organisation modulaire* : chaque domaine fonctionnel possède son routeur → responsabilités claires, montée en complexité plus simple.
- *SQLite (aiosqlite)* pour le dev local : rapide à mettre en place, facilement remplaçable par PostgreSQL/MySQL via `DATABASE_URL`.
- *Tests asynchrones* (`pytest-asyncio` + `httpx`) pour rejouer un flux utilisateur complet (inscription → événements → addons) et valider les garde‑fous de sécurité.

---

## 2. Fonctionnalités couvertes

| Domaine           | Capacités clés | Pourquoi ce choix ? |
|-------------------|----------------|---------------------|
| **Auth JWT**      | inscription, login OAuth2 password flow, `/api/users/me` | JWT stateless facilite le scaling horizontal et l’interopérabilité front/mobile. |
| **Groupes**       | CRUD groupes, rôles (admin, création d’événements), adhésions | Central pour structurer la communauté et fédérer les permissions. |
| **Événements**    | Organisateurs multiples, participants, options (polls, billetterie, addons) | Permet de couvrir tous les cas d’usage du cahier des charges (lancement produit, meetups…). |
| **Discussions**   | Threads liés à un groupe ou un événement, réponses hiérarchiques | Facilite l’engagement autour d’un événement ou d’une communauté. |
| **Médias**        | Albums, photos, commentaires | Nécessaire pour animer les événements avant/après. |
| **Sondages**      | Questions + options, votes par participant, statistiques | Favorise la co‑construction (ex. choix du menu, logistique). |
| **Billetterie**   | Types de billets, achats (contrôle quota/email) | Couverture complète de la monétisation simple. |
| **Addons**        | Shopping list, offres de covoiturage | Differencie l’application via des services pratiques complémentaires. |

Chaque module est contrôlé par des permissions serveur (par ex. seuls les organisateurs ou participants peuvent manipuler les ressources événementielles).

---

## 3. Posture sécurité

| Thématique | Mise en œuvre | Pourquoi |
|------------|---------------|----------|
| **Headers façon Helmet** | Middleware `Secure` + en-têtes personnalisés (`Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`, CSP, Referrer & Permissions Policy). | Réduit les attaques XSS, clickjacking, downgrade HTTP et fuite de metadata. |
| **Trusted hosts & HTTPS** | `TrustedHostMiddleware` et redirection optionnelle via `ENABLE_HTTPS_REDIRECT`. | Empêche l’empoisonnement Host header, force le transport chiffré en prod. |
| **JWT renforcé** | Claims `iat`, `exp`, `iss`, `aud` + `expires_in` retourné côté client ; dépendance `get_current_user` valide systématiquement les tokens. | Évite la réutilisation inter‑services et simplifie les renouvellements côté client. |
| **Validation & hygiène d’entrées** | Pydantic normalise les textes (trim, champs obligatoires non vides), vérifie les URL (`AnyHttpUrl`) et applique une politique de mot de passe (majuscule, minuscule, chiffre, caractère spécial). | Réduit la surface d’injection (SQL/JS) et garantit la qualité des données persistées. |
| **Rate limiting** | `slowapi` avec clés par IP (ou `X-Forwarded-For`). Limite globale + seuils serrés sur `/api/auth/register` et `/api/auth/token`. | Mitigue la force brute et les tentatives DDoS applicatives économiques. |
| **Transport sécurisé** | Documentation pour générer un certificat, démarrer uvicorn en HTTPS et activer HSTS. | Simplifie la bascule prod en mode TLS complet. |
| **Gestion centralisée des erreurs** | `app/core/error_handlers.py` forge des réponses `{"error": "...", "detail": ...}` pour 4xx/5xx, en loggant côté serveur. | Évite d’exposer des traces ou informations internes tout en restant explicite pour le client. |
| **Audit de dépendances** | `pip-audit` intégré dans la doc. Les vulnérabilités critiques (`python-jose`, `python-multipart`) sont corrigées directement dans `requirements.txt`. Les alertes restantes (ex. `django`, `pip`, `starlette`) proviennent de l’environnement global Anaconda : utilisez un virtualenv propre ou mettez à jour ces packages au niveau système avant déploiement. | Assure une supply chain maîtrisée même sans écosystème npm. |

---

## 4. Configuration

| Variable | Description | Défaut & justification |
|----------|-------------|------------------------|
| `SECRET_KEY` | Clé de signature JWT. | `change-me` (doit être remplacé en prod). |
| `DATABASE_URL` | Connexion SQLAlchemy. | `sqlite+aiosqlite:///./app.db` pour le dev local rapide. |
| `ALLOWED_ORIGINS` | Whitelist CORS. | `*` afin de ne pas bloquer les tests ; restreindre en prod. |
| `ALLOWED_HOSTS` | Hosts autorisés par `TrustedHostMiddleware`. | `*` pour le dev ; utiliser vos domaines en prod. |
| `ENABLE_HTTPS_REDIRECT` | Active `HTTPSRedirectMiddleware`. | `false` (utile uniquement en prod). |
| `CONTENT_SECURITY_POLICY`, `PERMISSIONS_POLICY`, `REFERRER_POLICY` | Headers de sécurité personnalisables. | Valeurs strictes couvrant la majorité des front SPA. |
| `RATE_LIMIT_*` | Limites globales/auth/register. | `100/hour`, `20/min`, `5/hour` : équilibre entre confort dev et protection brute-force. |
| `TOKEN_ISSUER`, `TOKEN_AUDIENCE` | Claims obligatoires lors du décodage JWT. | Valeurs par défaut alignées sur l’API pour éviter les erreurs côté client. |

Créer un `.env` à la racine pour surcharger :

```ini
SECRET_KEY=change-me-now
DATABASE_URL=sqlite+aiosqlite:///./app.db
ALLOWED_ORIGINS=["http://localhost:3000"]
ALLOWED_HOSTS=["localhost","127.0.0.1"]
ENABLE_HTTPS_REDIRECT=false
RATE_LIMIT_DEFAULT=100/hour
RATE_LIMIT_AUTH=20/minute
RATE_LIMIT_REGISTER=5/hour
```

---

## 5. Mise en route

1. **Prérequis** : Python 3.11+ (3.12 utilisé en dev). Recommandation forte : créer un virtualenv dédié (`python -m venv .venv && source .venv/Scripts/activate` sur Windows PowerShell).
2. **Installer les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```
3. **Démarrer l’API** :
   ```bash
   uvicorn app.main:app --reload
   ```
   Documentation interactive sur `http://127.0.0.1:8000/docs`.
4. **Tester** :
   ```bash
   pytest
   ```
   - `tests/test_app.py` : scénario end-to-end couvrant le cycle complet (deux utilisateurs, groupes, événements, médias, sondages, billets, addons).
   - `tests/test_security.py` : vérifie la politique de mot de passe et le déclenchement du rate limit.

### Activer HTTPS localement

```bash
openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 365 -subj "/CN=localhost"
uvicorn app.main:app --ssl-keyfile=key.pem --ssl-certfile=cert.pem
```

Ensuite, passez `ENABLE_HTTPS_REDIRECT=true` et restreignez `ALLOWED_HOSTS` à `["localhost"]`.

### Audit de sécurité Python

```bash
pip install pip-audit
pip-audit
```

Documentez les vulnérabilités résiduelles (voir tableau ci-dessus) : si elles proviennent d’outils hors projet (ex. `django` installé globalement), migrez vers un environnement isolé avant la mise en production.

---

## 6. Décisions architecturales & impacts

| Décision | Justification | Trade-off |
|----------|---------------|-----------|
| **JWT stateless + OAuth2 Password Flow** | Simple à intégrer avec front SPAs/mobiles, compatible refresh token ultérieur. | Pas de révocation centralisée par défaut → nécessite rotation courte (`access_token_expire_minutes`). |
| **SQLModel + SQLite** | API typed-friendly, migrations légères, parfait pour tests en mémoire. | Passage à PostgreSQL impliquera d’ajouter Alembic + revoir `DATABASE_URL`. |
| **Normalisation Pydantic** | Les champs utilisateurs sont trimés/validés avant persistance → cohérence des données. | Validation plus stricte peut surprendre certains clients (ex. URL invalide rejettée). |
| **SlowAPI in-process** | Pas de dépendance Redis : idéal pour démonstration/projet académique. | Pour une prod multi-instances, prévoir un backend partagé (Redis) afin de synchroniser les quotas. |
| **Handlers d’erreurs custom** | Format unique + logs internes → debugging facilité sans fuite d’info. | Les messages sont volontairement succincts pour éviter les leaks ; côté front, prévoir des libellés utilisateur. |

---

## 7. Pistes d’amélioration

1. **Migration complète vers Pydantic v2 idiomatique** (remplacer `Config` par `model_config`, éviter `from_orm`) afin de supprimer les warnings.
2. **Pagination et filtres** sur les listes volumineuses (groupes, événements, discussions).
3. **Notifications temps réel** (WebSocket ou WebPush) pour discussions et votes.
4. **CI/CD** : lint auto (ruff/mypy) + exécution de `pip-audit` et `pytest` dans un pipeline.
5. **Gestion avancée des tokens** : rafraîchissement, révocation via liste noire ou rotation clé.

---

## 8. Références

- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLModel](https://sqlmodel.tiangolo.com/)
- [slowapi (Rate limiting)](https://github.com/laurents/slowapi)
- [pip-audit](https://github.com/pypa/pip-audit)

Projet réalisé dans le cadre du module **API & Web services** (Mastere DE AI 2025‑2027).
