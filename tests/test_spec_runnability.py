from pathlib import Path

from steward import runnability, spec

FIX = Path(__file__).parent / "fixtures" / "cookbook"
NATIVE = (FIX / "native-hello-world.yaml").read_text()
DEVICE = (FIX / "device-hello-world-docker.yaml").read_text()


def test_official_device_example_passes_local_spec():
    report = spec.check_profile(DEVICE)
    assert report.kind is spec.ProfileKind.DEVICE and report.ok


def test_official_native_example_is_schema_ok_but_flags_security_level_wording():
    report = spec.check_profile(NATIVE)
    assert report.ok  # docs disagree on securityLevel wording, so it is a warning, not an error
    assert any(i.field.endswith("securityLevel") and i.severity is spec.Severity.WARNING for i in report.issues)


def test_official_native_example_will_not_run():
    run = runnability.assess(NATIVE)
    assert run.verdict is runnability.Verdict.WILL_NOT_RUN
    assert any(f.rule == "entrypoint-image-mismatch" for f in run.findings)


def test_device_missing_required_sections_are_errors():
    report = spec.check_profile("apiVersion: hyper.ai/v1\nkind: Application\nmetadata:\n  name: x\nspec: {}\n")
    fields = {i.field for i in report.errors}
    assert {"spec.app", "spec.workload", "spec.network", "spec.qos", "spec.constraints"} <= fields


def test_device_value_unit_and_ranges():
    bad = DEVICE.replace("availability: { value: 0.90, unit: \"fraction\" }",
                         "availability: { value: 90, unit: \"percent\" }")
    fields = {i.field for i in spec.check_profile(bad).errors}
    assert "spec.qos.availability.value" in fields and "spec.qos.availability.unit" in fields


def test_workload_block_must_match_kind():
    bad = DEVICE.replace("kind: DockerImage", "kind: AndroidApk")
    fields = {i.field for i in spec.check_profile(bad).errors}
    assert "spec.workload.androidApk" in fields and "spec.workload.dockerImage" in fields


def test_native_cpu_and_memory_formats():
    bad = NATIVE.replace('cpu: "2000m"', 'cpu: "2"').replace('memory: "10Gi"', 'memory: "10GB"')
    fields = {i.field for i in spec.check_profile(bad).errors}
    assert {"applicationProfile.specs.resources.cpu", "applicationProfile.specs.resources.memory"} <= fields


def test_yaml_parse_error_reported():
    report = spec.check_profile("a: [unclosed")
    assert report.parse_error and not report.ok


def test_listen_port_not_exposed_is_blocker():
    text = NATIVE.replace("- port: 8000", "- port: 9000")
    assert any(f.rule == "listen-port-not-exposed" and f.level == "blocker" for f in runnability.assess(text).findings)


def test_fixed_native_profile_has_no_known_blocker():
    fixed = (NATIVE.replace('uri: "nginx"', 'uri: "acme/hello-api"').replace('tag: "latest"', 'tag: "1.0.0"')
             .replace('securityLevel: "high"', 'securityLevel: "3"').replace("publicExposure: true", "publicExposure: false"))
    assert spec.check_profile(fixed).ok
    assert runnability.assess(fixed).verdict is runnability.Verdict.NO_KNOWN_BLOCKER


def test_android_without_device_name_is_at_risk():
    text = """apiVersion: hyper.ai/v1
kind: Application
metadata: {name: a}
spec:
  workload: {kind: AndroidApk, androidApk: {apkUrl: "https://x/a.apk", packageName: com.x}}
  constraints: {supportedArchitectures: ["arm64-v8a"]}
"""
    assert any(f.rule == "android-device-name" for f in runnability.assess(text).findings)
