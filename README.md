# My Social Networks API

API REST sécurisée développée avec FastAPI pour répondre au cahier des charges « My Social Networks ». Elle couvre la gestion des utilisateurs, groupes, événements, discussions, médias, sondages, billetterie ainsi que les modules optionnels (shopping list, covoiturage).

## Fonctionnalités principales
- Authentification JWT (inscription, login, profil courant).
- Gestion des groupes : création, adhésion, rôles (admin, création d’évènements).
- Gestion des événements : organisateurs multiples, participants, fonctionnalités activables (polls, billetterie, shopping list, covoiturage).
- Discussions : fils liés à un groupe ou un événement, réponses hiérarchiques.
- Médias : albums, photos, commentaires.
- Sondages : questions, options, vote unique par question, statistiques de votes.
- Billetterie : création de types de billets, achat (contrôle quota et ticket unique par email).
- Addons : shopping list et offres de covoiturage.
- Validation stricte des données (Pydantic) et sécurisation des accès (rôles, vérifications d’appartenance).

## Structure du projet
```
.
├── app
│   ├── core          # Configuration et sécurité (settings, JWT, hash mots de passe)
│   ├── routers       # Routes FastAPI organisées par domaine (auth, groups, events, ...)
│   ├── schemas       # Modèles Pydantic (entrées/sorties)
│   ├── models.py     # Modèles SQLModel & relations
│   ├── database.py   # Connexion et session async vers SQLite (SQLAlchemy/SQLModel)
│   └── main.py       # Point d’entrée FastAPI
├── scripts
│   └── read_pdf.py   # Outil d’extraction texte depuis le PDF du cahier des charges
├── tests
│   ├── conftest.py   # Fixtures (client HTTP async, base de données test)
│   └── test_app.py   # Scénario end-to-end couvrant les fonctionnalités majeures
├── requirements.txt
├── pytest.ini
└── README.md
```

## Prérequis
- Python 3.11+ (3.12 utilisé lors du développement).
- Virtualenv recommandé (`python -m venv .venv` puis `.\.venv\Scripts\activate` sous Windows).

## Installation
```bash
pip install -r requirements.txt
```

## Variables d’environnement
| Variable         | Description                                        | Valeur par défaut            |
|------------------|----------------------------------------------------|------------------------------|
| `SECRET_KEY`      | Clé secrète JWT (à changer en production)          | `change-me`                  |
| `DATABASE_URL`    | URL base de données SQLModel/SQLAlchemy            | `sqlite+aiosqlite:///./app.db` |
| `ALLOWED_ORIGINS` | Liste CORS (format JSON ou valeurs multiples)      | `*`                          |

Créer un fichier `.env` à la racine si besoin :
```
SECRET_KEY=remplacez-moi
DATABASE_URL=sqlite+aiosqlite:///./app.db
ALLOWED_ORIGINS=["http://localhost:3000"]
```

## Lancement de l’API
```bash
uvicorn app.main:app --reload
```
L’API est disponible sur `http://127.0.0.1:8000`, documentation interactive sur `/docs` ou `/redoc`.

## Tests automatisés
```bash
pytest
```
Le test `tests/test_app.py` orchestre un scénario complet (inscription, création de groupe, événement, sondage, billetterie, shopping list, covoiturage, etc.).

## Conception & choix techniques
- **FastAPI + SQLModel (async)** pour la rapidité de développement, type hints, et intégration avec SQLAlchemy 2.x.
- **SQLite (aiosqlite)** pour le mode développement rapide, extensible vers PostgreSQL via `DATABASE_URL`.
- **JWT** via `python-jose` et hash Bcrypt (passlib) pour sécuriser les endpoints.
- **Validation Pydantic**: champs typés, contrôles métiers (dates événements, contexte discussion, unicité par contrainte SQL).
- **Organisation modulaire**: chaque « feature » possède son routeur pour respecter les responsabilités et préparer une montée en complexité.
- **Tests async** avec `pytest-asyncio` et client `httpx` pour reproduire un flux utilisateur réaliste.

## Scénario fonctionnel couvert (extrait du test)
1. Inscription et authentification de deux utilisateurs.
2. Création d’un groupe + ajout de membre avec permissions.
3. Création d’un événement (activations fonctionnalités) et ajout participant.
4. Discussion associée à l’événement + messages.
5. Album photo, ajout photo et commentaire.
6. Sondage (création, consultation, vote).
7. Billetterie (type de billet, achat).
8. Shopping list et covoiturage.
9. Vérifications finales (`/api/events/{id}` et `/api/users/me`).

## Améliorations possibles
- Migrer vers Pydantic v2 complet (`model_config`, suppression `from_orm`) pour éliminer les warnings.
- Ajout d’un système de pagination / filtres sur les listes (événements, groupes, fils, etc.).
- Webhooks ou notifications temps réel (ex. via WebSocket) pour discussions et votes.
- Couverture test supplémentaire (tests unitaires ciblés sur autorisations spécifiques, contraintes d’unicité, cas d’erreurs).
- Intégration CI/CD (lint + tests) et conteneurisation (Dockerfile, compose).

## Ressources
- Cahier des charges extrait : `spec.txt` (généré depuis « My Social Networks API.pdf »).
- Documentation FastAPI : <https://fastapi.tiangolo.com/>
- Documentation SQLModel : <https://sqlmodel.tiangolo.com/>

---
Projet réalisé dans le cadre du module « API & Web services / sécurité ».*** End Patch
