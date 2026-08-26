import os

# Explicitly load the feature registration layer. This avoids relying on
# Python's optional automatic sitecustomize discovery in Railway.
import sitecustomize  # noqa: F401

from app import app
from waitress import serve

serve(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
