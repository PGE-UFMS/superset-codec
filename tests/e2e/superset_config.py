import os

# For SQLite database examples.db
PREVENT_UNSAFE_DB_CONNECTIONS = False

SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]
SQLALCHEMY_DATABASE_URI = "postgresql+psycopg2://superset:superset@postgres:5432/superset"
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = None
TALISMAN_ENABLED = False

FEATURE_FLAGS = {
    # Enable Jinja2 templating in SQL Lab (e.g. {{ filter_values() }})
    "ENABLE_TEMPLATE_PROCESSING": True,
    "EMBEDDED_SUPERSET": True,
    "DRILL_BY": True,
    "DRILL_TO_DETAIL": True,
}
