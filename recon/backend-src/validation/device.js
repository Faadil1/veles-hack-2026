import { createValidator, isPlainObject, req, opt, SEMVER, NON_NEGATIVE } from "./schema.js";

/* =========================================================
   DEVICE APPS — rules from docs/dsl/devices.md
   Paths are relative to the manifest root (apiVersion, kind, ...).
   ========================================================= */

const URI = { pattern: /^[a-z][a-z0-9+.-]*:\/\/\S+$/i, hint: 'a URI, e.g. "https://example.com/app.apk"' };
const HEX = { pattern: /^0x[0-9a-fA-F]+$/, hint: 'a hex value, e.g. "0x10000"' };
const STRING_MAP = { values: "string" };
const TIME_UNITS = ["ms", "s"];
const SIZE_UNITS = ["KiB", "MiB", "GiB", "TiB"];

const RULES = {
    "apiVersion": req("string", { enum: ["hyper.ai/v1"] }),
    "kind": req("string", { enum: ["Application"] }),

    // metadata
    "metadata.name": req("string"),
    "metadata.annotations": opt("object", STRING_MAP),

    // spec
    "spec.device_name": opt("string"),
    "spec.device_uuid": opt("string"),

    // spec.app
    "spec.app.type": req("string", { enum: ["device"] }),
    "spec.app.schemaVersion": req("string", SEMVER),
    "spec.app.name": req("string"),
    "spec.app.version": req("string"),
    "spec.app.owner": req("string"),
    "spec.app.lifecyclePhase": req("string", { enum: ["development", "testing", "production"] }),
    "spec.app.description": opt("string"),
    "spec.app.parentApp.name": opt("string"),
    "spec.app.parentApp.uid": opt("string"),

    // spec.workload — the block matching `kind` is enforced in checkWorkloadBlock
    "spec.workload.kind": req("string", { enum: ["AndroidApk", "DockerImage", "esp32Binary"] }),

    "spec.workload.androidApk": opt("object"),
    "spec.workload.androidApk.apkUrl": req("string", URI),
    "spec.workload.androidApk.packageName": req("string"),
    "spec.workload.androidApk.sha256": opt("string"),
    "spec.workload.androidApk.installMode": opt("string", { enum: ["install", "update"] }),
    "spec.workload.androidApk.launch.activity": opt("string"),
    "spec.workload.androidApk.launch.action": opt("string"),
    "spec.workload.androidApk.launch.category": opt("string"),

    "spec.workload.dockerImage": opt("object"),
    "spec.workload.dockerImage.image": req("string"),
    "spec.workload.dockerImage.imagePullPolicy": opt("string", { enum: ["Always", "IfNotPresent", "Never"] }),
    "spec.workload.dockerImage.imagePullSecretRef": opt("string"),

    "spec.workload.esp32Binary": opt("object"),
    "spec.workload.esp32Binary.binaryUrl": req("string", URI),
    "spec.workload.esp32Binary.chip": req("string", { enum: ["esp32", "esp32s2", "esp32s3", "esp32c3", "esp32c6", "esp32h2"] }),
    "spec.workload.esp32Binary.flash.method": req("string", { enum: ["serial", "ota"] }),
    "spec.workload.esp32Binary.sha256": opt("string"),
    "spec.workload.esp32Binary.flash.port": opt("string"),
    "spec.workload.esp32Binary.flash.baudRate": opt("integer", { check: (v) => v >= 1200, hint: "an integer ≥ 1200, e.g. 115200" }),
    "spec.workload.esp32Binary.flash.offset": opt("string", HEX),
    "spec.workload.esp32Binary.flash.partition": opt("string"),
    "spec.workload.esp32Binary.flash.eraseFlash": opt("boolean"),

    // spec.exec
    "spec.exec.parameters": opt("object", STRING_MAP),
    "spec.exec.command": opt("list", { items: "string" }),
    "spec.exec.env": opt("object", STRING_MAP),
    "spec.exec.workingDir": opt("string"),

    // spec.resources
    "spec.resources.cpu.value": opt("number"),
    "spec.resources.cpu.unit": opt("string", { enum: ["cores", "millicores"] }),
    "spec.resources.memory.value": opt("number"),
    "spec.resources.memory.unit": opt("string", { enum: SIZE_UNITS }),
    "spec.resources.storage.value": opt("number"),
    "spec.resources.storage.unit": opt("string", { enum: SIZE_UNITS }),
    "spec.resources.gpu": opt("integer", NON_NEGATIVE),
    "spec.resources.tpu": opt("integer", NON_NEGATIVE),
    "spec.resources.accelerators": opt("list", { items: "string" }),

    // spec.network
    "spec.network.ports[].port": req("integer", { check: (v) => v >= 1 && v <= 65535, hint: "a port between 1 and 65535" }),
    "spec.network.ports[].protocol": req("string"),
    "spec.network.networkBandwidthMin.value": req("number"),
    "spec.network.networkBandwidthMin.unit": req("string", { enum: ["bps", "Kbps", "Mbps", "Gbps"] }),

    // spec.qos
    "spec.qos.latencyToleranceMax.value": req("number"),
    "spec.qos.latencyToleranceMax.unit": req("string", { enum: TIME_UNITS }),
    "spec.qos.energyCost.value": req("number"),
    "spec.qos.energyCost.unit": req("string", { enum: ["mW", "W"] }),
    "spec.qos.monetaryCost.value": req("number"),
    "spec.qos.monetaryCost.currency": req("string"),
    "spec.qos.monetaryCost.per": req("string", { enum: ["second", "minute", "hour", "day"] }),
    "spec.qos.resilience": req("string"),
    "spec.qos.availability.value": req("number", { check: (v) => v >= 0 && v <= 1, hint: "a number from 0 to 1, e.g. 0.95" }),
    "spec.qos.availability.unit": req("string", { enum: ["fraction"] }),
    "spec.qos.startupTime.value": req("number"),
    "spec.qos.startupTime.unit": req("string", { enum: TIME_UNITS }),

    // spec.constraints
    "spec.constraints.schedulingPriority": req("integer"),
    "spec.constraints.supportedArchitectures": req("list", { items: "string" }),
    "spec.constraints.geoLocationRequirement": req("string"),
    "spec.constraints.isHighlyAvailable": req("boolean"),
    "spec.constraints.faultTolerance": req("string"),
    "spec.constraints.dataClassification": req("string"),
    "spec.constraints.trustScore": opt("number", { check: (v) => v >= 0, hint: "a number ≥ 0" }),
    "spec.constraints.batteryLevelMin": opt("integer", { check: (v) => v >= 0 && v <= 100, hint: "an integer from 0 to 100" }),
    "spec.constraints.securityLevel": opt("string"),

    // spec.sensors — the cookbook examples omit it, so the section itself is optional
    "spec.sensors": opt("object"),
    "spec.sensors.sensorType": req("string"),
    "spec.sensors.isActive": req("boolean"),
    "spec.sensors.taskStatus": req("string", { enum: ["IDLE", "RUNNING", "SCHEDULED"] }),
    "spec.sensors.sensorIDs": opt("list", { items: "string" }),
    "spec.sensors.platformInfo": opt("string"),

    // spec.runtime
    "spec.runtime.baseOS.name": opt("string"),
    "spec.runtime.baseOS.version": opt("string"),
    "spec.runtime.acceleratorRuntime[].name": opt("string"),
    "spec.runtime.hypervisor": opt("string"),

    // spec — miscellaneous
    "spec.logs_url": opt("string", URI),
    "spec.metrics_url": opt("string", URI),
    "spec.config": opt("object", { open: true }),

    // status — set by the platform
    "status": opt("object"),
    "status.phase": opt("string", { enum: ["pending", "scheduled", "deployed", "failed", "removed"] })
};

const WORKLOAD_BLOCKS = { AndroidApk: "androidApk", DockerImage: "dockerImage", esp32Binary: "esp32Binary" };

// Exactly one parameter block, the one matching workload.kind, must be present.
function checkWorkloadBlock(root, rootPath) {
    const workload = root.spec?.workload;
    const block = WORKLOAD_BLOCKS[workload?.kind];
    if (!isPlainObject(workload) || !block) return []; // a missing or invalid kind is reported by the rules

    const at = (key) => [rootPath, "spec.workload", key].filter(Boolean).join(".");
    const errors = [];
    if (workload[block] == null) {
        errors.push({ path: at(block), message: `is required when workload.kind is ${workload.kind}` });
    }
    for (const other of Object.values(WORKLOAD_BLOCKS)) {
        if (other !== block && workload[other] != null) {
            errors.push({ path: at(other), target: "key", message: `must not be set when workload.kind is ${workload.kind}` });
        }
    }
    return errors;
}

const validateRules = createValidator(RULES);

export function validateDevice(root, rootPath) {
    const report = validateRules(root, rootPath);
    report.errors.push(...checkWorkloadBlock(root, rootPath));
    return report;
}
