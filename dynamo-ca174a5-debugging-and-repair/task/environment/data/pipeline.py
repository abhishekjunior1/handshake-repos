"""Pipeline orchestrator — loads DAG definition and executes stages."""
import json

from scheduler import Scheduler

DAG_PATH = "/app/dag.json"
OUTPUT_PATH = "/app/execution_log.json"


def make_action(stage_def):
    """Create an action callable for a stage based on its definition."""
    transform = stage_def.get("transform", "passthrough")
    output_key = stage_def.get("output_key", stage_def["name"])
    fail_on_attempt = stage_def.get("fail_on_attempt")

    def action(input_state, attempt):
        if fail_on_attempt is not None and attempt < fail_on_attempt:
            return {"error": f"{stage_def['name']}_failed", "partial": True}

        if transform == "passthrough":
            result = dict(input_state)
            result[output_key] = f"{stage_def['name']}_done"
        elif transform == "merge":
            result = dict(input_state)
            result[output_key] = "+".join(sorted(input_state.keys())) + f"+{stage_def['name']}"
        elif transform == "compute":
            result = dict(input_state)
            values = [v for v in input_state.values() if isinstance(v, str) and not v.startswith("error")]
            result[output_key] = f"computed({len(values)})"
        else:
            result = dict(input_state)
            result[output_key] = transform

        return result

    return action


def make_validator(stage_def):
    """Create a validator callable if the stage has validation rules."""
    if not stage_def.get("validate"):
        return None

    def validator(output):
        # Validation passes if no error keys and no partial flag
        if output.get("partial"):
            return False
        if any(k == "error" for k in output):
            return False
        return True

    return validator


def run():
    with open(DAG_PATH) as f:
        dag = json.load(f)

    actions = {}
    validators = {}
    for stage_def in dag["stages"]:
        actions[stage_def["name"]] = make_action(stage_def)
        v = make_validator(stage_def)
        if v:
            validators[stage_def["name"]] = v

    scheduler = Scheduler(dag, actions, validators)
    log = scheduler.run()

    with open(OUTPUT_PATH, "w") as f:
        json.dump(log, f, indent=2)
    print(f"Pipeline complete: {len(log)} stages executed")


if __name__ == "__main__":
    run()
