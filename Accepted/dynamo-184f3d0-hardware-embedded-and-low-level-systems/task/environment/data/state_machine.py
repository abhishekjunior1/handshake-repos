"""
Interrupt State Machine — tracks handler states for NVIC-style interrupt
controller simulation.

Each interrupt can be in one of the following states:
- inactive: Not pending, not active
- pending: Asserted but waiting for higher-priority handler to complete
- active: Currently executing its handler
- masked: Disabled by BASEPRI or individual enable bit

The active handler stack maintains nesting depth for nested interrupts.
When a higher-priority interrupt preempts, the current handler is suspended
(remains active) and the new handler becomes the top of the active stack.
"""


class InterruptStateMachine:
    """
    Tracks the state of all registered interrupts and maintains
    the active handler stack for nested interrupt handling.

    ARM NVIC semantics:
    - Only one handler executes at a time (the highest priority active)
    - Lower-priority handlers are suspended (still marked active)
    - Same-priority interrupts do NOT preempt — they pend until current completes
    - Pending interrupts are serviced in priority order when current handler exits
    """

    STATE_INACTIVE = "inactive"
    STATE_PENDING = "pending"
    STATE_ACTIVE = "active"
    STATE_MASKED = "masked"

    NO_ACTIVE_PRIORITY = 256

    def __init__(self):
        """Initialize the interrupt state machine."""
        self._states = {}
        self._priorities = {}
        self._active_stack = []
        self._transition_log = []

    def register_interrupt(self, vector_number, configured_priority):
        """
        Register an interrupt with its configured priority.

        Args:
            vector_number: The interrupt vector number
            configured_priority: The configured priority value (0-255)
        """
        self._states[vector_number] = self.STATE_INACTIVE
        self._priorities[vector_number] = configured_priority

    def transition(self, vector_number, new_state):
        """
        Transition an interrupt to a new state.

        Handles active stack management:
        - Transition to 'active': push onto active stack
        - Transition from 'active' to 'inactive': pop from active stack

        Same-priority interrupts arriving while a handler is active at
        that priority level remain in pending state — they do NOT preempt.
        This is correct ARMv7-M behavior: preemption requires strictly
        higher priority (numerically lower value).

        Args:
            vector_number: The interrupt to transition
            new_state: Target state
        """
        old_state = self._states.get(vector_number, self.STATE_INACTIVE)

        if new_state == self.STATE_ACTIVE:
            self._active_stack.append(vector_number)

        if old_state == self.STATE_ACTIVE and new_state == self.STATE_INACTIVE:
            if vector_number in self._active_stack:
                self._active_stack.remove(vector_number)

        self._states[vector_number] = new_state
        self._transition_log.append({
            "vector": vector_number,
            "from_state": old_state,
            "to_state": new_state
        })

    def get_active_priority(self):
        """
        Get the priority of the currently executing (top of stack) handler.

        Returns NO_ACTIVE_PRIORITY (256) if no handler is currently active,
        which allows any enabled interrupt to execute.
        """
        if not self._active_stack:
            return self.NO_ACTIVE_PRIORITY
        top_vector = self._active_stack[-1]
        return self._priorities.get(top_vector, self.NO_ACTIVE_PRIORITY)

    def get_active_handlers(self):
        """Return list of currently active handler vector numbers."""
        return list(self._active_stack)

    def is_handler_completing(self, vector_number):
        """
        Check if a handler is in the process of completing (exiting).

        A handler is considered completing if it's the top of the active
        stack (currently executing) and about to return.

        Args:
            vector_number: Vector to check

        Returns:
            True if this handler is the active top and would be completing
        """
        if not self._active_stack:
            return False
        return self._active_stack[-1] == vector_number

    def get_pending_interrupts(self):
        """Return list of interrupts currently in pending state."""
        return [
            (vec, self._priorities[vec])
            for vec, state in self._states.items()
            if state == self.STATE_PENDING
        ]

    def get_priority_state(self):
        """
        Generate the priority state report for output.

        Returns current state of all registered interrupts with
        their priorities and states.
        """
        state_report = {}
        for vec_num in sorted(self._states.keys()):
            state_report[str(vec_num)] = {
                "state": self._states[vec_num],
                "configured_priority": self._priorities[vec_num],
                "is_active": vec_num in self._active_stack,
                "nesting_depth": (
                    self._active_stack.index(vec_num) + 1
                    if vec_num in self._active_stack else 0
                )
            }
        return state_report

    def get_nesting_depth(self):
        """Return current interrupt nesting depth."""
        return len(self._active_stack)

    def get_transition_log(self):
        """Return the complete state transition log."""
        return self._transition_log
