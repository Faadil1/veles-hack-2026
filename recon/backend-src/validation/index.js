import express from "express";
import { parseDocument, LineCounter, isMap, isSeq, isScalar } from "yaml";
import { isPlainObject } from "./schema.js";
import { validateNative } from "./native.js";
import { validateDevice } from "./device.js";

/* =========================================================
   VALIDATION SERVICE
   ---------------------------------------------------------
   Every error/warning is returned as
   { line, column, endLine, endColumn, field, message }
   (1-based, ready for Monaco markers), sorted by position.
   ========================================================= */

// The two profile formats are told apart by their root keys.
const FORMATS = [
    {
        type: "native",
        detect: (doc) => "applicationProfile" in doc,
        rootPath: "applicationProfile",
        root: (doc) => doc.applicationProfile,
        validate: validateNative
    },
    {
        type: "device",
        detect: (doc) => "apiVersion" in doc || "kind" in doc,
        rootPath: "",
        root: (doc) => doc,
        validate: validateDevice
    }
];

// "a.b[0].c" -> ["a", "b", 0, "c"]
function splitField(field) {
    return (field.match(/[^.[\]]+|\[\d+\]/g) || []).map((s) => (s.startsWith("[") ? Number(s.slice(1, -1)) : s));
}

// Finds the YAML node for a field. When the field is missing, returns the
// deepest ancestor that exists — that is where the user has to add it.
function findNode(doc, field) {
    let node = doc.contents;
    let key = null;
    for (const seg of splitField(field)) {
        if (isMap(node)) {
            const pair = node.items.find((p) => String(isScalar(p.key) ? p.key.value : p.key) === String(seg));
            if (!pair) return { key, node, found: false };
            key = pair.key;
            node = pair.value;
        } else if (isSeq(node) && typeof seg === "number" && node.items[seg]) {
            key = null;
            node = node.items[seg];
        } else {
            return { key, node, found: false };
        }
    }
    return { key, node, found: true };
}

function createLocator(doc, content, lineCounter) {
    const lines = content.split(/\r?\n/);
    const lineEnd = (line) => (lines[line - 1] ?? "").length + 1;

    // Highlights a single line: multi-line nodes are cut at the end of their first line.
    function range(start, end) {
        const from = lineCounter.linePos(start);
        const to = lineCounter.linePos(end);
        const sameLine = to.line === from.line;
        return {
            line: from.line,
            column: from.col,
            endLine: from.line,
            endColumn: Math.max(sameLine ? to.col : lineEnd(from.line), from.col + 1)
        };
    }

    return function locate(field, onKey) {
        const { key, node, found } = findNode(doc, field);
        // An empty value (`metadata:`) has no text to highlight, so fall back to its key.
        const isEmpty = isScalar(node) && node.value === null;
        const valueNode = (isScalar(node) && !isEmpty) || (node && !key) ? node : null;
        const target = !found ? key ?? node : onKey ? key ?? node : valueNode ?? key ?? node;
        if (!target?.range) return { line: 1, column: 1, endLine: 1, endColumn: Math.max(lineEnd(1), 2) };
        return range(target.range[0], target.range[1]);
    };
}

const byPosition = (a, b) => a.line - b.line || a.column - b.column;

function result(type, errors, warnings = []) {
    return { type, valid: errors.length === 0, errors: errors.sort(byPosition), warnings: warnings.sort(byPosition) };
}

export function validateProfile(content) {
    const lineCounter = new LineCounter();
    const doc = parseDocument(content, { lineCounter, prettyErrors: false });

    if (doc.errors.length > 0) {
        return result(null, doc.errors.map((err) => {
            const from = lineCounter.linePos(err.pos[0]);
            const to = lineCounter.linePos(Math.max(err.pos[1], err.pos[0] + 1));
            return {
                line: from.line,
                column: from.col,
                endLine: from.line,
                endColumn: to.line === from.line ? to.col : from.col + 1,
                field: "",
                message: `Invalid YAML: ${err.message}`
            };
        }));
    }

    const locate = createLocator(doc, content, lineCounter);
    const place = (item) => ({ ...locate(item.path, item.target === "key"), field: item.path, message: item.message });

    const data = doc.toJS();
    const format = isPlainObject(data) ? FORMATS.find((f) => f.detect(data)) : undefined;
    if (!format) {
        return result(null, [place({
            path: "",
            message: 'unrecognised profile, expected "applicationProfile" (native app) or "apiVersion"/"kind" (device app) at the root'
        })]);
    }

    const root = format.root(data);
    if (!isPlainObject(root)) {
        return result(format.type, [place({ path: format.rootPath, message: "must be an object" })]);
    }

    // Keys beside a nested root (native) aren't seen by the rule walker.
    const extraRootKeys = format.rootPath
        ? Object.keys(data)
            .filter((key) => key !== format.rootPath)
            .map((key) => ({ path: key, target: "key", message: "unknown field, not part of the schema" }))
        : [];

    const { errors, warnings } = format.validate(root, format.rootPath);
    return result(format.type, errors.map(place), [...extraRootKeys, ...warnings].map(place));
}

// lookupFile(path) -> { path, content }, or throws an error carrying
// `status` (and optionally `matches`) — shared with /api/agent/file.
export function createValidationRouter(lookupFile) {
    const router = express.Router();

    router.get("/file", (req, res) => {
        try {
            const file = lookupFile(req.query.path);
            const report = validateProfile(file.content);
            console.log(`[validation] ${file.path} (${report.type ?? "unknown"}): ${report.valid ? "valid" : `${report.errors.length} error(s)`}, ${report.warnings.length} warning(s)`);
            for (const e of report.errors) console.log(`  ERROR   line ${e.line}:${e.column} ${e.field}: ${e.message}`);
            for (const w of report.warnings) console.log(`  WARNING line ${w.line}:${w.column} ${w.field}: ${w.message}`);
            res.json({ path: file.path, ...report });
        } catch (err) {
            res.status(err.status || 400).json({ error: err.message, matches: err.matches });
        }
    });

    return router;
}
