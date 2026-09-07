"""Layered agent memory: episodic, semantic, procedural.

    from mem import Store, recall
    store = Store("minor-itr1").init()
    hits = recall.working_set(store, "deploy hook keeps failing")
"""
from .store import Record, Store, default_root  # noqa: F401
from . import (consolidate, errorlog, frontmatter, index, migrate,  # noqa: F401
               recall, schema)
from .errorlog import ErrorLog  # noqa: F401

__version__ = "0.1.0"
__all__ = ["Store", "Record", "ErrorLog", "default_root", "schema",
           "frontmatter", "index", "recall", "consolidate", "errorlog",
           "migrate", "__version__"]
