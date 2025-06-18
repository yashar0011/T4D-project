"""Entrypoint shim so `python -m amts_pipeline` works."""
from .main import main

if __name__ == "__main__":
    main()