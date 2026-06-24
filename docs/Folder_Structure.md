## Project Structure

```
arcade-cafe/
├── backend/
│   ├── api/
│   │   └── routers/      # FastAPI route handlers
│   ├── services/         # Business logic (billing, sessions, members, packages)
│   ├── repositories/     # All database queries
│   ├── models/           # SQLAlchemy ORM models
│   ├── schemas/          # Pydantic request / response schemas
│   ├── licensing/        # License signature verification, hardware fingerprinting
│   └── core/
│       ├── config.py     # Settings loader
│       └── database.py   # Engine, WAL pragmas, session factory
├── frontend/              # React dashboard (Vite + TailwindCSS)
├── agent/                 # Electron client agent
├── alembic/               # Database migration scripts
├── launcher.py            # Tkinter GUI launcher (incl. Activation screen)
├── arcade.config.json     # Runtime config (created on first run)
└── README.md
```
