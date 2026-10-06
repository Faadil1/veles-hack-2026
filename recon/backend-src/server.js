import express from "express";
import fs from "fs";
import path from "path";
import cors from "cors";
import axios from "axios";
import { Blob } from "buffer";
import { v4 as uuidv4 } from "uuid";
import { createRemoteJWKSet, jwtVerify } from "jose";
const app = express();
import FormData from "form-data";
import { createValidationRouter } from "./validation/index.js";

const TRANSLATOR_API_BASE = "http://translator-app.apm.svc.cluster.local:8000";

const AUTH_ENABLED = process.env.AUTH_ENABLED !== "false";
const KEYCLOAK_BASE_URL = "https://keycloak.hyperai.di.uoa.gr";
const KEYCLOAK_REALM = "hyper-ai-realm";
const KEYCLOAK_ISSUER = `${KEYCLOAK_BASE_URL}/realms/${KEYCLOAK_REALM}`;
const KEYCLOAK_AUDIENCE = "ide-gui";
const KEYCLOAK_JWKS = createRemoteJWKSet(new URL(`${KEYCLOAK_ISSUER}/protocol/openid-connect/certs`));



/* =========================================================
   MIDDLEWARE
   ========================================================= */

app.use(cors());
app.use(express.json({ limit: "1000mb" }));
app.use(express.urlencoded({ extended: true, limit: "1000mb" }));

async function authenticateKeycloakToken(req, res, next) {
    if (!AUTH_ENABLED) {
        req.user = { preferred_username: "guest (auth disabled)" };
        return next();
    }

    try {
        const authHeader = req.headers.authorization || "";
        if (!authHeader.startsWith("Bearer ")) {
            return res.status(401).json({ error: "Missing Bearer token" });
        }

        const token = authHeader.slice("Bearer ".length).trim();
        if (!token) {
            return res.status(401).json({ error: "Missing Bearer token" });
        }

        const { payload } = await jwtVerify(token, KEYCLOAK_JWKS, {
            issuer: KEYCLOAK_ISSUER,
            algorithms: ["RS256"]
        });

        const audClaim = payload.aud;
        const audValues = Array.isArray(audClaim) ? audClaim : (typeof audClaim === "string" ? [audClaim] : []);
        const hasExpectedAud = audValues.includes(KEYCLOAK_AUDIENCE);
        const hasExpectedAzp = payload.azp === KEYCLOAK_AUDIENCE;

        if (!hasExpectedAud && !hasExpectedAzp) {
            return res.status(401).json({
                error: "Token audience/client mismatch",
                details: `Expected aud or azp to match '${KEYCLOAK_AUDIENCE}'`
            });
        }

        req.user = payload;
        next();
    } catch (error) {
        return res.status(401).json({ error: "Invalid or expired token", details: error.message });
    }
}

app.use("/api", authenticateKeycloakToken);

/* =========================================================
   ROOT WORKSPACE DIRECTORY (FILES API)
   ========================================================= */

const ROOT = path.resolve(process.cwd(), "helm-charts");

// Ensure root exists
if (!fs.existsSync(ROOT)) {
    fs.mkdirSync(ROOT, { recursive: true });
}

/* =========================================================
   SAFE PATH RESOLUTION (FILES)
   ========================================================= */

function resolveSafe(relativePath = "") {
    const resolved = path.resolve(ROOT, relativePath);
    if (!resolved.startsWith(ROOT)) {
        throw new Error("Invalid path");
    }
    return resolved;
}

/* =========================================================
   FILE API ENDPOINTS
   ========================================================= */

app.get("/api/files", (req, res) => {
    try {
        const target = resolveSafe(req.query.path || "");

        if (!fs.existsSync(target)) {
            return res.json([]);
        }

        const items = fs.readdirSync(target, { withFileTypes: true });

        const response = items.map(item => ({
            name: item.name,
            type: item.isDirectory() ? "folder" : "file",
            path: path.join(req.query.path || "", item.name)
        }));

        res.json(response);
    } catch (err) {
        res.status(400).json({ error: err.message });
    }
});

app.get("/api/file", (req, res) => {
    try {
        const file = resolveSafe(req.query.path);

        if (!fs.existsSync(file)) {
            return res.status(404).json({ error: "File not found" });
        }

        const content = fs.readFileSync(file, "utf8");
        res.json({ content });
    } catch (err) {
        res.status(400).json({ error: err.message });
    }
});

function findFileByName(name, dir = ROOT, prefix = "") {
    const matches = [];

    for (const item of fs.readdirSync(dir, { withFileTypes: true })) {
        const relative = prefix ? `${prefix}/${item.name}` : item.name;
        if (item.isDirectory()) {
            matches.push(...findFileByName(name, path.join(dir, item.name), relative));
        } else if (item.name === name) {
            matches.push(relative);
        }
    }

    return matches;
}

function httpError(status, message, extra = {}) {
    return Object.assign(new Error(message), { status }, extra);
}

// Resolves a workspace path, or a bare file name searched across the tree.
function lookupAgentFile(rawPath) {
    const given = String(rawPath || "").replace(/^\/+/, "");
    if (!given) {
        throw httpError(400, "Missing path");
    }

    const direct = resolveSafe(given);
    if (fs.existsSync(direct) && fs.statSync(direct).isFile()) {
        return { path: given, content: fs.readFileSync(direct, "utf8") };
    }

    const matches = given.includes("/") ? [] : findFileByName(given);
    if (matches.length === 0) {
        throw httpError(404, "File not found");
    }
    if (matches.length > 1) {
        throw httpError(409, "Ambiguous file name", { matches });
    }

    return { path: matches[0], content: fs.readFileSync(resolveSafe(matches[0]), "utf8") };
}

app.get("/api/agent/file", (req, res) => {
    try {
        res.json(lookupAgentFile(req.query.path));
    } catch (err) {
        res.status(err.status || 400).json({ error: err.message, matches: err.matches });
    }
});

app.use("/api/agent/validation", createValidationRouter(lookupAgentFile));

app.post("/api/file", (req, res) => {
    try {
        const file = resolveSafe(req.body.path);

        fs.mkdirSync(path.dirname(file), { recursive: true });
        fs.writeFileSync(file, req.body.content ?? "", "utf8");

        res.json({ success: true });
    } catch (err) {
        res.status(400).json({ error: err.message });
    }
});

app.post("/api/file/create", (req, res) => {
    try {
        const file = resolveSafe(req.body.path);

        if (fs.existsSync(file)) {
            return res.status(400).json({ error: "File already exists" });
        }

        fs.mkdirSync(path.dirname(file), { recursive: true });
        fs.writeFileSync(file, req.body.content ?? "", "utf8");

        res.json({ success: true });
    } catch (err) {
        res.status(400).json({ error: err.message });
    }
});

app.post("/api/folder/create", (req, res) => {
    try {
        const folder = resolveSafe(req.body.path);

        if (fs.existsSync(folder)) {
            return res.status(400).json({ error: "Folder already exists" });
        }

        fs.mkdirSync(folder, { recursive: true });
        res.json({ success: true });
    } catch (err) {
        res.status(400).json({ error: err.message });
    }
});

app.delete("/api/delete", (req, res) => {
    try {
        const target = resolveSafe(req.query.path);

        if (!fs.existsSync(target)) {
            return res.status(404).json({ error: "Path not found" });
        }

        const stat = fs.statSync(target);

        if (stat.isDirectory()) {
            fs.rmSync(target, { recursive: true, force: true });
        } else {
            fs.unlinkSync(target);
        }

        res.json({ success: true });
    } catch (err) {
        res.status(400).json({ error: err.message });
    }
});

/* =========================================================
   TEMPLATES WORKSPACE
   ========================================================= */

const TEMPLATES_ROOT = path.resolve(process.cwd(), "templates");

// Ensure templates root exists
if (!fs.existsSync(TEMPLATES_ROOT)) {
    fs.mkdirSync(TEMPLATES_ROOT, { recursive: true });
}

/* =========================================================
   SAFE PATH RESOLUTION (TEMPLATES)
   ========================================================= */

function resolveTemplateSafe(relativePath = "") {
    const resolved = path.resolve(TEMPLATES_ROOT, relativePath);
    if (!resolved.startsWith(TEMPLATES_ROOT)) {
        throw new Error("Invalid template path");
    }
    return resolved;
}

/* =========================================================
   TEMPLATE API ENDPOINTS
   ========================================================= */

/**
 * List all templates
 */
app.get("/api/templates", (req, res) => {
    try {
        const dirs = fs.readdirSync(TEMPLATES_ROOT, { withFileTypes: true })
            .filter(d => d.isDirectory());

        const templates = dirs.map(dir => {
            const files = fs.readdirSync(
                path.join(TEMPLATES_ROOT, dir.name)
            );

            return {
                name: dir.name,
                hasYaml: files.some(f => f.endsWith(".yaml")),
                hasIcon: files.some(f => f.endsWith(".png"))
            };
        });

        res.json(templates);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

/**
 * Get full template (yaml + icon url)
 */
app.get("/api/templates/:name", (req, res) => {
    try {
        const name = req.params.name;
        const templateDir = resolveTemplateSafe(name);
        const files = fs.readdirSync(templateDir);

        const yamlFile = files.find(f => f.endsWith(".yaml"));
        const iconFile = files.find(f => f.endsWith(".png"));

        if (!yamlFile) {
            return res.status(404).json({ error: "Template YAML missing" });
        }

        const yaml = fs.readFileSync(
            path.join(templateDir, yamlFile),
            "utf8"
        );

        res.json({
            name,
            yaml,
            iconUrl: iconFile ? `/api/templates/${name}/icon` : null
        });
    } catch (err) {
        res.status(400).json({ error: err.message });
    }
});

/**
 * Get template YAML only
 */
app.get("/api/templates/:name/yaml", (req, res) => {
    try {
        const templateDir = resolveTemplateSafe(req.params.name);
        const yamlFile = fs.readdirSync(templateDir)
            .find(f => f.endsWith(".yaml"));

        if (!yamlFile) {
            return res.status(404).json({ error: "YAML not found" });
        }

        const content = fs.readFileSync(
            path.join(templateDir, yamlFile),
            "utf8"
        );

        res.json({ content });
    } catch (err) {
        res.status(400).json({ error: err.message });
    }
});

/**
 * Get template icon
 */
app.get("/api/templates/:name/icon", (req, res) => {
    try {
        const templateDir = resolveTemplateSafe(req.params.name);
        const iconFile = fs.readdirSync(templateDir)
            .find(f => f.endsWith(".png"));

        if (!iconFile) {
            return res.status(404).json({ error: "Icon not found" });
        }

        res.sendFile(path.join(templateDir, iconFile));
    } catch (err) {
        res.status(400).json({ error: err.message });
    }
});



/* =========================================================
   POST: UPLOAD TEMPLATE (NO LIBRARIES)
   ========================================================= */
app.post("/api/templates/upload", (req, res) => {
    try {
        const { name, yaml, iconBase64 } = req.body;

        if (!name || !yaml) {
            return res.status(400).json({ error: "Name and YAML required" });
        }

        const safeName = name.replace(/[^a-zA-Z0-9-_]/g, "");
        const tplDir = path.join(TEMPLATES_ROOT, safeName);

        if (fs.existsSync(tplDir)) {
            return res.status(400).json({ error: "Template already exists" });
        }

        // Create template folder
        fs.mkdirSync(tplDir, { recursive: true });

        // Write YAML file
        fs.writeFileSync(
            path.join(tplDir, `${safeName}.yaml`),
            yaml,
            "utf8"
        );

        // Write icon if provided
        if (iconBase64) {
            const buffer = Buffer.from(iconBase64, "base64");
            fs.writeFileSync(path.join(tplDir, "icon.png"), buffer);
        }

        res.json({ success: true });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

/* =========================================================
   POST: RENAME FILE OR FOLDER
   ========================================================= */
app.post("/api/rename", (req, res) => {
    try {
        const { oldPath, newName } = req.body;
        if (!oldPath || !newName) return res.status(400).json({ error: "Old path and new name required" });

        const resolvedOld = resolveSafe(oldPath);
        const newPath = path.join(path.dirname(resolvedOld), newName);

        if (fs.existsSync(newPath)) {
            return res.status(400).json({ error: "A file/folder with that name already exists" });
        }

        fs.renameSync(resolvedOld, newPath);
        res.json({ success: true });
    } catch (err) {
        res.status(400).json({ error: err.message });
    }
});

function fileToBase64(absPath) {
    const buffer = fs.readFileSync(absPath);
    return buffer.toString("base64");
}
function normalizeError(error) {
    const status = error.response?.status || 500;
    const raw = error.response?.data;
    let message = error.message;

    if (typeof raw === "string") {
        message = raw;
    } else if (raw && typeof raw === "object") {
        message = raw.error || raw.message || JSON.stringify(raw);
    }

    return { status, message, raw };
}

function isReplicaFieldConflict(payloadOrMessage) {
    const text = typeof payloadOrMessage === "string"
        ? payloadOrMessage
        : JSON.stringify(payloadOrMessage || {});
    const lowered = text.toLowerCase();
    return lowered.includes("conflict") && lowered.includes(".spec.replicas");
}

function stripDeploymentReplicas(yamlBody) {
    const lines = yamlBody.split(/\r?\n/);
    const output = [];
    let changed = false;

    let inDeployment = false;
    let inSpec = false;
    let specIndent = -1;

    const indentOf = (line) => line.match(/^\s*/)?.[0].length ?? 0;

    for (const line of lines) {
        const trimmed = line.trim();
        const indent = indentOf(line);

        if (trimmed === "---") {
            inDeployment = false;
            inSpec = false;
            specIndent = -1;
            output.push(line);
            continue;
        }

        if (/^kind\s*:\s*/i.test(trimmed)) {
            inDeployment = /^kind\s*:\s*Deployment\s*$/i.test(trimmed);
            inSpec = false;
            specIndent = -1;
            output.push(line);
            continue;
        }

        if (inDeployment && /^spec\s*:\s*$/i.test(trimmed)) {
            inSpec = true;
            specIndent = indent;
            output.push(line);
            continue;
        }

        if (inDeployment && inSpec) {
            if (trimmed && indent <= specIndent) {
                inSpec = false;
                specIndent = -1;
            } else if (/^replicas\s*:\s*.+$/i.test(trimmed) && indent > specIndent) {
                changed = true;
                continue;
            }
        }

        output.push(line);
    }

    return { changed, yaml: changed ? output.join("\n") : yamlBody };
}

function stripAllReplicaKeys(yamlBody) {
    const lines = yamlBody.split(/\r?\n/);
    let changed = false;
    const filtered = lines.filter((line) => {
        const shouldDrop = /^\s*replicas\s*:\s*.+$/i.test(line.trim());
        if (shouldDrop) changed = true;
        return !shouldDrop;
    });

    return { changed, yaml: changed ? filtered.join("\n") : yamlBody };
}

async function postKubestreamApply({ yamlBody, workflowId }) {
    const form = new FormData();
    form.append("data", Buffer.from(yamlBody, "utf8"), {
        filename: "manifest.yaml",
        contentType: "application/x-yaml"
    });

    if (workflowId && String(workflowId).trim()) {
        form.append("workflow_id", String(workflowId).trim());
    }

    return axios.post(
        `${TRANSLATOR_API_BASE}/kubestream/apply`,
        form,
        {
            headers: {
                ...form.getHeaders()
            }
        }
    );
}

async function deleteKubestreamResourcesByWorkflow(workflowId) {
    if (!workflowId || !String(workflowId).trim()) {
        throw new Error("workflowId is required for delete fallback");
    }

    const q = new URLSearchParams({ workflow_id: String(workflowId).trim() }).toString();
    return axios.delete(`${TRANSLATOR_API_BASE}/kubestream/resources?${q}`);
}

async function uploadWorkflowFromFiles(files = [], name = "default-workflow") {
    if (!Array.isArray(files) || files.length === 0) {
        throw new Error("No files selected");
    }

    const form = new FormData();
    form.append("name", name || "default-workflow");

    for (const relativePath of files) {
        const absolutePath = resolveSafe(relativePath);

        if (!fs.existsSync(absolutePath)) {
            throw new Error(`File not found: ${relativePath}`);
        }

        form.append("data", fs.createReadStream(absolutePath), path.basename(absolutePath));
    }

    const response = await axios.post(`${TRANSLATOR_API_BASE}/workflows`, form, {
        headers: {
            ...form.getHeaders()
        }
    });

    return response.data;
}

/* =========================================================
   WORKFLOWS API PROXY
   ========================================================= */

app.get("/api/workflows", async (req, res) => {
    try {
        const response = await axios.get(`${TRANSLATOR_API_BASE}/workflows`);
        res.json(response.data);
    } catch (error) {
        const { status, message } = normalizeError(error);
        res.status(status).json({ error: message });
    }
});

app.post("/api/workflows", async (req, res) => {
    const { files, name } = req.body || {};

    try {
        const data = await uploadWorkflowFromFiles(files, name);
        res.json({
            success: true,
            data
        });
    } catch (error) {
        const { status, message, raw } = normalizeError(error);
        res.status(status).json({
            error: message,
            details: raw ?? null
        });
    }
});

app.get("/api/workflows/:id", async (req, res) => {
    try {
        const response = await axios.get(`${TRANSLATOR_API_BASE}/workflows/${req.params.id}`);
        res.json(response.data);
    } catch (error) {
        const { status, message } = normalizeError(error);
        res.status(status).json({ error: message });
    }
});

app.post("/api/workflows/:id", async (req, res) => {
    const action = req.body?.message?.action || req.body?.action;

    if (!["start", "delete"].includes(action)) {
        return res.status(400).json({ error: "action must be one of: start, delete" });
    }

    try {
        const payload = {
            message: {
                action
            }
        };

        const response = await axios.post(`${TRANSLATOR_API_BASE}/workflows/${req.params.id}`, payload, {
            headers: {
                "Content-Type": "application/json"
            }
        });

        res.json(response.data);
    } catch (error) {
        const { status, message, raw } = normalizeError(error);
        console.error("[ERROR] Workflow action failed:", raw || message);
        res.status(status).json({
            error: message,
            details: raw ?? null
        });
    }
});

/* =========================================================
   KUBESTREAM API PROXY
   ========================================================= */

app.get("/api/kubestream/health", async (req, res) => {
    try {
        const response = await axios.get(`${TRANSLATOR_API_BASE}/kubestream/health`);
        res.status(response.status).json(response.data);
    } catch (error) {
        const { status, message, raw } = normalizeError(error);
        res.status(status).json(typeof raw === "object" && raw ? raw : { error: message });
    }
});

app.get("/api/kubestream/namespaces", async (req, res) => {
    try {
        const response = await axios.get(`${TRANSLATOR_API_BASE}/kubestream/namespaces`);
        res.status(response.status).json(response.data);
    } catch (error) {
        const { status, message, raw } = normalizeError(error);
        res.status(status).json(typeof raw === "object" && raw ? raw : { error: message });
    }
});

app.get("/api/kubestream/devicenodes", async (req, res) => {
    try {
        const response = await axios.get(`${TRANSLATOR_API_BASE}/kubestream/devicenodes`);
        res.status(response.status).json(response.data);
    } catch (error) {
        const { status, message, raw } = normalizeError(error);
        res.status(status).json(typeof raw === "object" && raw ? raw : { error: message });
    }
});

app.get("/api/kubestream/metrics", async (req, res) => {
    const workflowId = req.query.workflow_id;

    if (!workflowId || !String(workflowId).trim()) {
        return res.status(400).json({ error: "workflow_id query param is required" });
    }

    try {
        const params = new URLSearchParams();
        params.append("workflow_id", String(workflowId).trim());
        const suffix = `?${params.toString()}`;

        const response = await axios.get(`${TRANSLATOR_API_BASE}/kubestream/metrics${suffix}`);
        res.status(response.status).json(response.data);
    } catch (error) {
        const { status, message, raw } = normalizeError(error);
        console.error("[ERROR] Metrics fetch failed:", raw || message);
        res.status(status).json({
            error: message,
            details: raw ?? null
        });
    }
});

app.post("/api/kubestream/apply", async (req, res) => {
    const {
        yaml: yamlBody,
        workflowId: workflowIdRaw,
        workflow_id: workflowIdSnake,
        allowReplicaConflictRetry = true,
        allowDeleteAndReapplyOnReplicaConflict = true
    } = req.body || {};
    const workflowId = workflowIdRaw || workflowIdSnake;

    if (!yamlBody || typeof yamlBody !== "string") {
        return res.status(400).json({ error: "yaml string is required" });
    }

    try {
        const response = await postKubestreamApply({ yamlBody, workflowId });
        res.status(response.status).json(response.data);
    } catch (error) {
        const first = normalizeError(error);
        if (allowReplicaConflictRetry && isReplicaFieldConflict(first.raw || first.message)) {
            let latestYaml = yamlBody;
            try {
                const deploymentScoped = stripDeploymentReplicas(latestYaml);
                if (deploymentScoped.changed) {
                    latestYaml = deploymentScoped.yaml;
                    const retryResponse = await postKubestreamApply({ yamlBody: latestYaml, workflowId });
                    return res.status(retryResponse.status).json({
                        ...retryResponse.data,
                        warning: "Deployment replicas were removed before apply due to field-manager conflict on .spec.replicas"
                    });
                }

                const genericReplicaStrip = stripAllReplicaKeys(latestYaml);
                if (genericReplicaStrip.changed) {
                    latestYaml = genericReplicaStrip.yaml;
                    const retryResponse = await postKubestreamApply({ yamlBody: latestYaml, workflowId });
                    return res.status(retryResponse.status).json({
                        ...retryResponse.data,
                        warning: "Generic replicas keys were removed before apply due to field-manager conflict on .spec.replicas"
                    });
                }
            } catch (retryError) {
                const second = normalizeError(retryError);
                if (
                    allowDeleteAndReapplyOnReplicaConflict &&
                    workflowId &&
                    isReplicaFieldConflict(second.raw || second.message)
                ) {
                    try {
                        await deleteKubestreamResourcesByWorkflow(workflowId);
                        const thirdResponse = await postKubestreamApply({ yamlBody: latestYaml, workflowId });
                        return res.status(thirdResponse.status).json({
                            ...thirdResponse.data,
                            warning: "Resources were deleted and reapplied due to persistent .spec.replicas field-manager conflict"
                        });
                    } catch (thirdError) {
                        const third = normalizeError(thirdError);
                        return res.status(third.status).json(typeof third.raw === "object" && third.raw ? third.raw : { error: third.message });
                    }
                }

                return res.status(second.status).json(typeof second.raw === "object" && second.raw ? second.raw : { error: second.message });
            }

            if (allowDeleteAndReapplyOnReplicaConflict && workflowId) {
                try {
                    await deleteKubestreamResourcesByWorkflow(workflowId);
                    const thirdResponse = await postKubestreamApply({ yamlBody, workflowId });
                    return res.status(thirdResponse.status).json({
                        ...thirdResponse.data,
                        warning: "Resources were deleted and reapplied due to .spec.replicas field-manager conflict"
                    });
                } catch (thirdError) {
                    const third = normalizeError(thirdError);
                    return res.status(third.status).json(typeof third.raw === "object" && third.raw ? third.raw : { error: third.message });
                }
            }
        }

        res.status(first.status).json(typeof first.raw === "object" && first.raw ? first.raw : { error: first.message });
    }
});

app.delete("/api/kubestream/resources", async (req, res) => {
    const workflowId = req.query.workflow_id;

    if (!workflowId || !String(workflowId).trim()) {
        return res.status(400).json({ error: "workflow_id query param is required" });
    }

    try {
        const params = new URLSearchParams({ workflow_id: String(workflowId).trim() });
        const response = await axios.delete(`${TRANSLATOR_API_BASE}/kubestream/resources?${params.toString()}`);
        res.status(response.status).json(response.data);
    } catch (error) {
        const { status, message, raw } = normalizeError(error);
        res.status(status).json(typeof raw === "object" && raw ? raw : { error: message });
    }
});

app.get("/api/kubestream/rollout/status", async (req, res) => {
    const { kind, name, namespace } = req.query;

    if (!kind || !name) {
        return res.status(400).json({ error: "kind and name query params are required" });
    }

    try {
        const params = new URLSearchParams({ kind: String(kind), name: String(name) });
        if (namespace) params.append("namespace", String(namespace));

        const response = await axios.get(`${TRANSLATOR_API_BASE}/kubestream/rollout/status?${params.toString()}`);
        res.status(response.status).json(response.data);
    } catch (error) {
        const { status, message, raw } = normalizeError(error);
        res.status(status).json(typeof raw === "object" && raw ? raw : { error: message });
    }
});

/* =========================================================
   LEGACY COMPATIBILITY ROUTES
   ========================================================= */

app.post('/api/deploy', async (req, res) => {
    const { files, name } = req.body || {};

    try {
        const data = await uploadWorkflowFromFiles(files, name);
        res.json({
            message: "Success",
            externalResponse: data
        });
    } catch (error) {
        const { status, message, raw } = normalizeError(error);
        res.status(status).json({
            error: message,
            details: raw ?? null
        });
    }
});

app.get("/api/test-connection", async (req, res) => {
    try {
        const response = await axios.get(`${TRANSLATOR_API_BASE}/workflows`);
        res.json({
            success: true,
            status: response.status,
            data: response.data
        });
    } catch (error) {
        const { status, message } = normalizeError(error);
        res.status(status).json({
            success: false,
            status,
            error: message
        });
    }
});

/* =========================================================
   SERVER START
   ========================================================= */

const PORT = 3001;

app.listen(PORT, () => {
    console.log(` File API server running at http://localhost:${PORT}`);
    if (!AUTH_ENABLED) {
        console.warn(" AUTH_ENABLED=false — Keycloak token verification is DISABLED (dev only)");
    }
    console.log(` Files root: ${ROOT}`);
    console.log(` Templates root: ${TEMPLATES_ROOT}`);
});

