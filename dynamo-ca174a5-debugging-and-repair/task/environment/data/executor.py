"""Stage execution engine with validation and retry support."""
import time


class Executor:
    """Executes pipeline stages with retry and validation logic."""

    def __init__(self, max_retries=2):
        self._max_retries = max_retries
        self._status = {}
        self._attempt_counts = {}

    def get_status(self, stage_name):
        """Get the current status of a stage."""
        return self._status.get(stage_name, "pending")

    def get_attempt_count(self, stage_name):
        """Get number of execution attempts for a stage."""
        return self._attempt_counts.get(stage_name, 0)

    def execute_stage(self, stage_def, input_state, state_store):
        """Execute a stage with retry on validation failure.

        A stage's output is recorded as successful only after validation
        passes. Failed validation attempts are recorded with success=False.

        Args:
            stage_def: Stage definition dict with 'name', 'action', 'validator'.
            input_state: Input state dict for this stage.
            state_store: StateStore instance for recording snapshots.

        Returns:
            Tuple of (final_status, output_state).
        """
        name = stage_def["name"]
        action = stage_def["action"]
        validator = stage_def.get("validator")

        self._attempt_counts[name] = 0

        for attempt in range(self._max_retries + 1):
            self._attempt_counts[name] += 1
            time.sleep(0)  # yield for event loop scheduling

            # Execute the action
            output = action(input_state, attempt)

            # Record as successful snapshot immediately
            state_store.record_snapshot(name, output, True)

            # Validate if validator exists
            if validator:
                is_valid = validator(output)
                if not is_valid:
                    # Mark this snapshot as actually failed
                    state_store.record_snapshot(name, output, False)
                    if attempt < self._max_retries:
                        continue
                    else:
                        self._status[name] = "failed"
                        return "failed", output

            self._status[name] = "completed"
            return "completed", output

        self._status[name] = "failed"
        return "failed", {}
