"""Internal execution helpers for the fixed-DAG runtime.

The public compatibility surface remains ``react_agent.fixed_dag_executor``.
This package keeps low-level execution foundations importable without pulling
in the full runner or external compute seams.
"""

PACKAGE_VERSION = "fixed_dag_execution_internal_v1"

__all__ = ["PACKAGE_VERSION"]
