"""shortcut-forge: build, lint and sign Apple Shortcuts from Python, JSON or an LLM (via MCP)."""
from .builder import Shortcut
from .lint import lint_file, lint_plist
from .refs import CURRENT_DATE, REPEAT_ITEM, SHORTCUT_INPUT, var
from .spec import build_from_spec

__version__ = "0.2.1"
__all__ = ["Shortcut", "var", "CURRENT_DATE", "REPEAT_ITEM", "SHORTCUT_INPUT", "build_from_spec",
           "lint_plist", "lint_file", "__version__"]
