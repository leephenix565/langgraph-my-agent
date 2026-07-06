"""Internal fixed-DAG external compute boundary modules.

The entry points formerly at ``fixed_dag_external_*.py`` were moved into this
package during Phase 1 consolidation with backward-compatible shims at their
old import paths.  Leaf modules are import-light and do not call endpoints at
import time.
"""

__all__: list[str] = []
