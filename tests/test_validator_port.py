"""The Python port must say exactly what the IDE backend validator says.

Expected messages below were produced by the real validator (validation/*.js from donmichael/ide-backend:latest)
on these exact inputs; the full differential run is evaluation/validator_parity.py (CI job validator-parity).
"""

from pathlib import Path

from steward import hyperai_schema, spec, templates

FIX = Path(__file__).parent / "fixtures" / "cookbook"
NATIVE = (FIX / "native-hello-world.yaml").read_text()
DEVICE = (FIX / "device-hello-world-docker.yaml").read_text()


def _errors(text):
    return [(e.path, e.message) for e in hyperai_schema.validate_profile(text).errors]


def test_yaml_1_2_semantics_match_the_backend():
    assert _errors(NATIVE.replace("isHighlyAvailable: false", "isHighlyAvailable: no")) == [
        ("applicationProfile.specs.constraints.isHighlyAvailable", "must be boolean, got string")]
    unquoted = "\n".join("    schemaVersion: 1.1" if "schemaVersion" in line else line for line in NATIVE.splitlines())
    assert _errors(unquoted) == [("applicationProfile.metadata.schemaVersion",
                                  "must be string, got number (wrap the value in quotes)")]


def test_duplicate_keys_are_a_yaml_error():
    r = hyperai_schema.validate_profile("kind: Application\nkind: Application\n")
    assert r.parse_error and "unique" in r.parse_error


def test_device_requires_sections_through_implied_ancestors():
    fields = {p for p, _ in _errors("apiVersion: hyper.ai/v1\nkind: Application\nmetadata:\n  name: x\nspec: {}\n")}
    assert {"spec.app", "spec.workload", "spec.network", "spec.qos", "spec.constraints"} <= fields
    assert "spec.network.ports" not in fields  # list members are only required once a list entry exists


def test_unknown_fields_are_warnings_not_errors():
    r = hyperai_schema.validate_profile("foo: 1\n" + NATIVE)
    assert r.valid and [w.path for w in r.warnings] == ["foo"]


def test_workload_block_must_match_kind():
    text = DEVICE.replace("dockerImage:", "androidApk:")
    assert ("spec.workload.dockerImage", "is required when workload.kind is DockerImage") in _errors(text)


def test_every_builder_output_is_valid_for_the_ide():
    outputs = [
        templates.build_device_profile("nginx-web", image="nginx:1.27", ports=[80]),
        templates.build_device_profile("cam", workload="AndroidApk", apk_url="https://e.com/a.apk",
                                       package_name="com.e.cam", device_name="pixel-7"),
        templates.build_device_profile("t", workload="esp32Binary", binary_url="https://e.com/f.bin", chip="esp32s3"),
        templates.build_native_profile("api", image="acme/api", tag="1.0.0", entry_point="uvicorn", ports=[8000]),
    ]
    for text in outputs:
        report = spec.check_profile(text)
        assert report.ok, report.errors
        assert not [i for i in report.issues if i.severity is spec.Severity.WARNING]
