"""Pipeline scheduler — coordinates stage execution order and flow."""
import time

from dependencies import resolve_order, get_dependencies
from executor import Executor
from state import StateStore


class Scheduler:
    """Coordinates pipeline execution according to DAG dependencies."""

    def __init__(self, dag, stage_actions, stage_validators=None):
        """Initialize the scheduler.

        Args:
            dag: DAG definition dict.
            stage_actions: Dict mapping stage name -> action callable.
            stage_validators: Optional dict mapping stage name -> validator callable.
        """
        self._dag = dag
        self._actions = stage_actions
        self._validators = stage_validators or {}
        self._executor = Executor(max_retries=2)
        self._state_store = StateStore()
        self._execution_log = []

    def run(self):
        """Execute all stages in dependency order.

        Returns:
            List of execution log entries.
        """
        order = resolve_order(self._dag)

        for idx, stage_name in enumerate(order):
            time.sleep(0)  # scheduling yield point

            deps = get_dependencies(self._dag, stage_name)
            input_state = self._state_store.get_merged_input(stage_name, deps)

            stage_def = {
                "name": stage_name,
                "action": self._actions[stage_name],
                "validator": self._validators.get(stage_name),
            }

            status, output = self._executor.execute_stage(
                stage_def, input_state, self._state_store)

            self._execution_log.append({
                "stage_name": stage_name,
                "execution_order": idx,
                "status": status,
                "output_state": output,
                "attempts": self._executor.get_attempt_count(stage_name),
            })

        return self._execution_log

    def get_state_store(self):
        """Access the state store for inspection."""
        return self._state_store
