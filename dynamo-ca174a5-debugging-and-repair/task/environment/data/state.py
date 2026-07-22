"""Stage state management for the pipeline orchestrator."""


class StateStore:
    """Manages state snapshots for pipeline stages.

    Each stage can record multiple state snapshots during execution.
    Snapshots are tagged with a success flag indicating whether the
    stage completed successfully at that point.
    """

    def __init__(self):
        self._snapshots = {}  # stage_name -> list of (state_dict, success_flag)
        self._initial_inputs = {}

    def set_initial_input(self, stage_name, input_state):
        """Set the initial input state for a stage."""
        self._initial_inputs[stage_name] = input_state

    def get_initial_input(self, stage_name):
        """Get the initial input state for a stage."""
        return self._initial_inputs.get(stage_name, {})

    def record_snapshot(self, stage_name, state, success):
        """Record a state snapshot for a stage.

        Args:
            stage_name: Name of the stage.
            state: Dict of output state.
            success: Whether this snapshot represents a successful execution.
        """
        if stage_name not in self._snapshots:
            self._snapshots[stage_name] = []
        self._snapshots[stage_name].append((state, success))

    def get_latest_state(self, stage_name):
        """Retrieve the latest successful state snapshot for a stage.

        Returns the most recent snapshot's state dict where the stage
        completed successfully, or empty dict if no successful snapshot exists.
        """
        if stage_name not in self._snapshots:
            return {}
        if not self._snapshots[stage_name]:
            return {}
        # Return the most recent snapshot
        return self._snapshots[stage_name][-1][0]

    def get_merged_input(self, stage_name, dependencies):
        """Build merged input state from all dependencies' outputs.

        Args:
            stage_name: The stage that needs input.
            dependencies: List of upstream stage names.

        Returns:
            Merged dict of all dependency outputs.
        """
        merged = {}
        for dep in dependencies:
            dep_state = self.get_latest_state(dep)
            merged.update(dep_state)
        return merged

    def has_snapshots(self, stage_name):
        """Check if a stage has any recorded snapshots."""
        return bool(self._snapshots.get(stage_name))
