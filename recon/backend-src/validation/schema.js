/* =========================================================
   GENERIC RULE-TABLE VALIDATOR
   ---------------------------------------------------------
   Rules map a dotted field path to { type, required, ... }.
   A `[]` suffix marks a list of objects, e.g. "network.ports[].port".
   Optional rule keys:
     enum, pattern + hint, check + hint
     items   type of every list element
     values  type of every map value (keys are free)
     open    free-form object, its keys are not checked
   ========================================================= */

export const isPlainObject = (v) => v !== null && typeof v === "object" && !Array.isArray(v);

export const req = (type, extra = {}) => ({ type, required: true, ...extra });
export const opt = (type, extra = {}) => ({ type, required: false, ...extra });

export const SEMVER = { pattern: /^\d+\.\d+\.\d+$/, hint: 'a semantic version, e.g. "1.1.0"' };
export const NON_NEGATIVE = { check: (v) => v >= 0, hint: "an integer ≥ 0" };

const TYPE_CHECKS = {
    string: (v) => typeof v === "string",
    number: (v) => typeof v === "number" && Number.isFinite(v),
    integer: Number.isInteger,
    boolean: (v) => typeof v === "boolean",
    list: Array.isArray,
    object: isPlainObject
};

function describe(value) {
    if (Array.isArray(value)) return "list";
    if (isPlainObject(value)) return "object";
    return typeof value;
}

function typeError(expected, value) {
    const quoteTip = expected === "string" && ["number", "boolean"].includes(typeof value) ? " (wrap the value in quotes)" : "";
    return `must be ${expected}, got ${describe(value)}${quoteTip}`;
}

// Adds object/list rules for every ancestor of a declared field. An ancestor is
// required when a required field sits below it with no list in between, so
// `ports[].port` only becomes required once a port entry exists.
function withAncestors(rules) {
    const all = { ...rules };
    for (const [path, rule] of Object.entries(rules)) {
        const segs = path.split(".");
        for (let k = segs.length - 2; k >= 0; k--) {
            const ancestor = segs.slice(0, k + 1).join(".");
            const isList = segs[k].endsWith("[]");
            const implied = all[ancestor] ?? { type: isList ? "list" : "object", items: isList ? "object" : undefined, required: false, implied: true };
            const listBetween = segs.slice(k, -1).some((s) => s.endsWith("[]"));
            if (implied.implied && rule.required && !listBetween) implied.required = true;
            all[ancestor] = implied;
        }
    }
    return all;
}

// Every concrete location of a rule path whose parent exists, expanding lists.
function locate(node, segs, path) {
    if (!isPlainObject(node)) return [];
    const [seg, ...rest] = segs;
    const isList = seg.endsWith("[]");
    const key = isList ? seg.slice(0, -2) : seg;
    const childPath = path ? `${path}.${key}` : key;
    const child = node[key];

    if (rest.length === 0) return [{ path: childPath, value: child }];
    if (isList) {
        return Array.isArray(child) ? child.flatMap((el, i) => locate(el, rest, `${childPath}[${i}]`)) : [];
    }
    return locate(child, rest, childPath);
}

function checkValue(path, value, rule) {
    const fail = (message, at = path) => ({ path: at, message });

    if (value === undefined || value === null) {
        return rule.required ? fail("is required") : null;
    }
    if (!TYPE_CHECKS[rule.type](value)) {
        return fail(typeError(rule.type, value));
    }
    if (rule.enum && !rule.enum.includes(value)) {
        return fail(`must be one of: ${rule.enum.join(", ")}`);
    }
    if ((rule.pattern && !rule.pattern.test(value)) || (rule.check && !rule.check(value))) {
        return fail(`invalid value ${JSON.stringify(value)}, expected ${rule.hint}`);
    }
    if (rule.items) {
        const bad = value.findIndex((el) => !TYPE_CHECKS[rule.items](el));
        if (bad !== -1) return fail(typeError(rule.items, value[bad]), `${path}[${bad}]`);
    }
    if (rule.values) {
        const bad = Object.entries(value).find(([, v]) => !TYPE_CHECKS[rule.values](v));
        if (bad) return fail(typeError(rule.values, bad[1]), `${path}.${bad[0]}`);
    }
    return null;
}

function findUnknown(node, norm, path, rules, warnings) {
    if (Array.isArray(node)) {
        node.forEach((el, i) => findUnknown(el, norm, `${path}[${i}]`, rules, warnings));
        return;
    }
    if (!isPlainObject(node)) return;

    for (const [key, value] of Object.entries(node)) {
        const base = norm ? `${norm}.${key}` : key;
        const childPath = path ? `${path}.${key}` : key;
        const known = rules[base] ? base : rules[`${base}[]`] ? `${base}[]` : null;
        if (!known) {
            warnings.push({ path: childPath, target: "key", message: "unknown field, not part of the schema" });
            continue;
        }
        const rule = rules[known];
        if ((rule.type === "object" && !rule.values && !rule.open) || rule.items === "object") {
            findUnknown(value, known, childPath, rules, warnings);
        }
    }
}

// Returns (root, rootPath) => { errors, warnings }.
export function createValidator(rules) {
    const all = withAncestors(rules);

    return (root, rootPath) => {
        const errors = [];
        for (const [path, rule] of Object.entries(all)) {
            for (const loc of locate(root, path.split("."), rootPath)) {
                const error = checkValue(loc.path, loc.value, rule);
                if (error) errors.push(error);
            }
        }

        const warnings = [];
        findUnknown(root, "", rootPath, all, warnings);
        return { errors, warnings };
    };
}
