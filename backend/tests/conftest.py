import os

# Must be set before app modules are imported so Pydantic-Settings can read it.
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-tests-only-do-not-use-in-production")
