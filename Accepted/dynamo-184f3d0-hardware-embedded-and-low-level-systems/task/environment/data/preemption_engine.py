"""
Preemption Engine — decides whether an incoming interrupt should preempt
the currently active handler based on ARM NVIC priority conventions.

In ARM NVIC, preemption occurs only when the incoming interrupt has
a strictly HIGHER priority (numerically LOWER value) than the active handler.
Same-priority interrupts do NOT preempt — they remain pending until the
active handler completes.
"""


class PreemptionEngine:
    """
    Evaluates preemption decisions for nested vectored interrupts.

    Implements the ARM NVIC preemption logic where:
    - Lower numeric priority = higher actual priority
    - Preemption requires STRICTLY lower numeric value
    - No handler is active: any enabled interrupt can execute
    - Same priority: no preemption (pending until active completes)
    """

    # Maximum priority value (lowest actual priority)
    MAX_PRIORITY = 255
    # Priority value indicating no active handler
    NO_ACTIVE_PRIORITY = 256

    def __init__(self):
        """Initialize the preemption engine."""
        self._preemption_count = 0
        self._denied_count = 0
        self._history = []

    def evaluate_preemption(self, incoming_priority, active_priority, vector_number):
        """
        Determine if incoming interrupt should preempt the active handler.

        ARM NVIC preemption rules:
        - If no handler is active (priority=256), any interrupt can execute
        - If a handler is active, incoming must have strictly lower numeric
          priority (higher actual priority) to preempt
        - Equal priority does NOT cause preemption

        Args:
            incoming_priority: Effective priority of the incoming interrupt
            active_priority: Effective priority of the currently active handler
                           (256 if no handler is active)
            vector_number: Vector number of incoming interrupt (for logging)

        Returns:
            True if preemption should occur, False otherwise
        """
        if active_priority == self.NO_ACTIVE_PRIORITY:
            self._preemption_count += 1
            self._history.append({
                "vector": vector_number,
                "decision": "execute",
                "incoming": incoming_priority,
                "active": active_priority
            })
            return True

        if incoming_priority < active_priority:
            self._preemption_count += 1
            self._history.append({
                "vector": vector_number,
                "decision": "preempt",
                "incoming": incoming_priority,
                "active": active_priority
            })
            return True

        self._denied_count += 1
        self._history.append({
            "vector": vector_number,
            "decision": "denied",
            "incoming": incoming_priority,
            "active": active_priority
        })
        return False

    def get_preemption_statistics(self):
        """Return preemption decision statistics."""
        total = self._preemption_count + self._denied_count
        return {
            "total_decisions": total,
            "preemptions_granted": self._preemption_count,
            "preemptions_denied": self._denied_count,
            "preemption_rate": (
                self._preemption_count / total if total > 0 else 0.0
            )
        }

    def get_decision_history(self):
        """Return the full history of preemption decisions."""
        return self._history

    def evaluate_priority_inversion(self, pending_interrupts, active_priority):
        """
        Check for priority inversion conditions.

        Priority inversion occurs when a higher-priority interrupt
        is blocked by a lower-priority handler holding a resource.
        In pure NVIC without resource locking, this manifests as
        a higher-priority interrupt remaining pending while a lower-priority
        handler runs (should not happen with correct preemption).

        Args:
            pending_interrupts: List of (vector, priority) tuples currently pending
            active_priority: Priority of the currently active handler

        Returns:
            List of vectors experiencing priority inversion
        """
        inversions = []
        for vector, priority in pending_interrupts:
            if priority < active_priority:
                inversions.append({
                    "vector": vector,
                    "blocked_priority": priority,
                    "blocking_priority": active_priority,
                    "severity": active_priority - priority
                })
        return inversions

    def reset_statistics(self):
        """Reset all counters and history."""
        self._preemption_count = 0
        self._denied_count = 0
        self._history = []
