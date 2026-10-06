import { createValidator, req, opt, SEMVER, NON_NEGATIVE } from "./schema.js";

/* =========================================================
   NATIVE APPS — rules from docs/dsl/native-apps.md
   Paths are relative to `applicationProfile`.
   ========================================================= */

const unit = (units, example) => ({
    pattern: new RegExp(`^\\d+(\\.\\d+)?(${units.join("|")})$`),
    hint: `a number followed by ${units.join("/")}, e.g. "${example}"`
});
const RFC3339 = {
    pattern: /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$/,
    hint: 'an RFC 3339 timestamp, e.g. "2026-06-04T12:00:00Z"'
};
const MILLICORES = { pattern: /^[1-9]\d*m$/, hint: 'millicores greater than 0, e.g. "2000m"' };
const SIZE = unit(["Mi", "Gi", "Ti"], "10Gi");

const RULES = {
    // metadata
    "metadata.type": req("string", { enum: ["native"] }),
    "metadata.schemaVersion": req("string", SEMVER),
    "metadata.name": req("string"),
    "metadata.version": req("string"),
    "metadata.description": opt("string"),
    "metadata.owner": req("string"),
    "metadata.lifecyclePhase": req("string", { enum: ["development", "testing", "production"] }),
    // Required in the spec, but deliberately optional here.
    "metadata.createdAt": opt("string", RFC3339),
    "metadata.updatedAt": opt("string", RFC3339),
    "metadata.annotations.intent": opt("string"),
    "metadata.annotations.domain": opt("string"),
    "metadata.annotations.language": opt("string"),
    "metadata.annotations.dependencies": opt("list", { items: "string" }),

    // specs.runtime
    "specs.runtime.executionType": req("string", { enum: ["container", "vm"] }),
    "specs.runtime.entryPoint": req("string"),
    "specs.runtime.args": req("list", { items: "string" }),
    "specs.runtime.baseOS.name": req("string"),
    "specs.runtime.baseOS.version": req("string"),
    "specs.runtime.containerImage.uri": req("string"),
    "specs.runtime.containerImage.tag": req("string"),
    "specs.runtime.hypervisor": opt("string", { enum: ["qemu", "kvm", "xen", "vmware"] }),
    "specs.runtime.acceleratorRuntime[].name": opt("string"),
    "specs.runtime.acceleratorRuntime[].version": opt("string"),

    // specs.resources
    "specs.resources.cpu": req("string", MILLICORES),
    "specs.resources.memory": req("string", SIZE),
    "specs.resources.storage": req("string", SIZE),
    "specs.resources.gpu": opt("integer", NON_NEGATIVE),
    "specs.resources.tpu": opt("integer", NON_NEGATIVE),
    "specs.resources.accelerators": opt("integer", NON_NEGATIVE),

    // specs.network
    "specs.network.ports[].port": req("integer", { check: (v) => v >= 1 && v <= 65535, hint: "a port between 1 and 65535" }),
    "specs.network.ports[].protocol": req("string"),
    "specs.network.ports[].publicExposure": opt("boolean"),
    "specs.network.protocols": opt("list", { items: "string" }),
    "specs.network.networkBandwidthMin": opt("string", unit(["Mbps", "Gbps"], "100Mbps")),

    // specs.constraints
    "specs.constraints.supportedArchitectures": req("list", { items: "string" }),
    "specs.constraints.trustScore": opt("string", {
        check: (v) => /^\d+(\.\d+)?$/.test(v) && Number(v) >= 1 && Number(v) <= 5,
        hint: 'a number from 1 to 5, e.g. "4.5"'
    }),
    "specs.constraints.geoLocationRequirement": opt("string"),
    "specs.constraints.isHighlyAvailable": opt("boolean"),
    "specs.constraints.faultTolerance": opt("string"),
    // The spec says "1–3" but its example is "high", so any string is accepted.
    "specs.constraints.securityLevel": opt("string"),
    "specs.constraints.dataClassification": opt("string"),

    // specs.qos
    "specs.qos.latencyToleranceMax": opt("string", unit(["ms"], "150ms")),
    "specs.qos.energyCost": opt("string", unit(["kWh"], "0.5kWh")),
    "specs.qos.monetaryCost": opt("string"),
    "specs.qos.resilience": opt("string"),
    "specs.qos.availability": opt("string", unit(["%"], "99.0%")),
    "specs.qos.startupTime": opt("string", unit(["s"], "10s")),

    // status — set by the platform, so the section itself is optional
    "status": opt("object"),
    "status.isOnline": req("boolean"),
    "status.lastHeartBeat": req("string", RFC3339),
    "status.runtimeState": req("string"),
    "status.isStateless": opt("boolean"),
    "status.resourceUsage.cpu": req("string"),
    "status.resourceUsage.memory": req("string"),
    "status.resourceUsage.storage": req("string"),
    "status.resourceUsage.gpu": opt("integer", NON_NEGATIVE),
    "status.resourceUsage.tpu": opt("integer", NON_NEGATIVE),
    "status.resourceUsage.accelerators": opt("integer", NON_NEGATIVE)
};

export const validateNative = createValidator(RULES);
