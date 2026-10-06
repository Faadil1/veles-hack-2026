import pytest

from steward import runnability, spec, templates


@pytest.mark.parametrize("kwargs", [
    {"name": "Sensor Reader", "image": "acme/sensor:1.2", "architectures": ["arm64"], "latency_ms": 200},
    {"name": "phone app", "workload": "AndroidApk", "apk_url": "https://x/app.apk", "package_name": "com.x.app",
     "device_name": "pixel-1"},
    {"name": "fw", "workload": "esp32Binary", "binary_url": "https://x/fw.bin", "chip": "esp32c3"},
])
def test_device_builder_outputs_spec_valid_profiles(kwargs):
    text = templates.build_device_profile(**kwargs)
    report = spec.check_profile(text)
    assert report.ok, [i.as_dict() for i in report.errors]
    assert runnability.assess(text).verdict is not runnability.Verdict.WILL_NOT_RUN


def test_native_builder_valid_and_runnable():
    text = templates.build_native_profile(name="hello api", image="acme/hello-api:1.0.0", entry_point="uvicorn",
                                          args=["main:app", "--host", "0.0.0.0", "--port", "8000"], ports=[8000],
                                          latency_ms=150, availability_percent=99.0)
    assert spec.check_profile(text).ok
    assert runnability.assess(text).verdict is runnability.Verdict.NO_KNOWN_BLOCKER
    assert "tag: 1.0.0" in text and "uri: acme/hello-api" in text


def test_builder_rejects_missing_required_inputs():
    with pytest.raises(ValueError):
        templates.build_device_profile(name="x", workload="DockerImage")
