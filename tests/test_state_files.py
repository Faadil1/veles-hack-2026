"""Governance files must stay machine-readable, and the binding deadline must be consistent everywhere."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
YAML_FILES = ["state/CURRENT.yaml", "state/HANDOVER.yaml", "docs/CONDITIONAL-GATEWAY-REGISTRY.yaml",
              "docs/PROJECT-CONTROL-PLANE.yaml"]
DEADLINE = "2026-10-07T14:59Z"
FREEZE = "2026-10-07T11:59Z"


def test_state_yaml_parses():
    for rel in YAML_FILES:
        assert yaml.safe_load((ROOT / rel).read_text()) is not None, rel


def test_binding_deadline_and_freeze_are_consistent():
    current = yaml.safe_load((ROOT / "state/CURRENT.yaml").read_text())["project"]
    assert str(current["deadline_utc"]) == DEADLINE
    assert str(current["safety_boundary_utc"]) == FREEZE
    registry = yaml.safe_load((ROOT / "docs/CONDITIONAL-GATEWAY-REGISTRY.yaml").read_text())
    assert str(registry["gateways"]["SUBMISSION_EXECUTION_ASSURANCE"]["official_deadline"]) == DEADLINE
