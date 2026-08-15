"use client";

import { ChangeEvent, useState } from "react";

const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const actor = process.env.NEXT_PUBLIC_ACTOR_ID ?? "00000000-0000-0000-0000-000000000001";

export default function Home() {
  const [tenantId, setTenantId] = useState("");
  const [projectId, setProjectId] = useState("");
  const [projectName, setProjectName] = useState("CEB RFP");
  const [projects, setProjects] = useState<Array<{ id: string; name: string }>>([]);
  const [message, setMessage] = useState("Create a tenant to begin.");
  const [busy, setBusy] = useState(false);

  const headers = { "X-Actor-Id": actor, "X-Tenant-Id": tenantId };

  async function createTenant() {
    setBusy(true);
    try {
      const response = await fetch(`${api}/tenants?name=Local%20workspace`, { method: "POST", headers: { "X-Actor-Id": actor } });
      if (!response.ok) throw new Error("Tenant creation failed");
      const tenant = await response.json() as { id: string };
      setTenantId(tenant.id);
      setMessage("Tenant ready. Create a project to start a review.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Request failed"); }
    finally { setBusy(false); }
  }

  async function createProject() {
    setBusy(true);
    try {
      const response = await fetch(`${api}/projects`, { method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify({ name: projectName }) });
      if (!response.ok) throw new Error("Project creation failed");
      const project = await response.json() as { id: string; name: string };
      setProjectId(project.id);
      setProjects((current) => [...current, project]);
      setMessage("Project created. Upload evidence through the API while document review UI is being completed.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Request failed"); }
    finally { setBusy(false); }
  }

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || !projectId) return;
    setBusy(true);
    try {
      const form = new FormData(); form.append("file", file);
      const response = await fetch(`${api}/projects/${projectId}/documents`, { method: "POST", headers, body: form });
      if (!response.ok) throw new Error((await response.json() as { detail?: string }).detail ?? "Upload failed");
      setMessage("PDF accepted and parsed. Pages are ready for evidence selection.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Upload failed"); }
    finally { setBusy(false); }
  }

  return <main><header><p className="kicker">FLUXERA / PROCUREMENT ASSURANCE</p><h1>Evidence before confidence.</h1><p className="lede">Build a reviewable requirement baseline from source documents, one verified decision at a time.</p></header><section className="workspace" aria-label="Pre-bid workspace"><div className="toolbar"><button onClick={createTenant} disabled={busy}>{busy ? "Working..." : "Create workspace"}</button><label className="file">Upload PDF<input type="file" accept="application/pdf" onChange={upload} disabled={!projectId || busy} /></label></div><div className="grid"><section><p className="eyebrow">PROJECTS</p><label>Project name<input value={projectName} onChange={(event) => setProjectName(event.target.value)} /></label><button onClick={createProject} disabled={!tenantId || busy}>Create project</button>{projects.length > 0 && <ul>{projects.map((project) => <li key={project.id}>{project.name}<span>active</span></li>)}</ul>}</section><aside><p className="eyebrow">STATUS</p><p className="status">{message}</p><dl><div><dt>Source</dt><dd>{projectId ? "Project selected" : "Waiting"}</dd></div><div><dt>Baseline</dt><dd>Manual review</dd></div><div><dt>Decision rule</dt><dd>Unknown until verified</dd></div></dl></aside></div></section></main>;
}
