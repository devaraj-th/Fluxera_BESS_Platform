"use client";

import { ChangeEvent, useState } from "react";

const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const actor = process.env.NEXT_PUBLIC_ACTOR_ID ?? "00000000-0000-0000-0000-000000000001";
type Project = { id: string; name: string; timezone?: string };

export default function Home() {
  const [tenantId, setTenantId] = useState("");
  const [projectId, setProjectId] = useState("");
  const [projectName, setProjectName] = useState("CEB RFP");
  const [projects, setProjects] = useState<Project[]>([]);
  const [message, setMessage] = useState("Create a workspace to begin your evidence review.");
  const [busy, setBusy] = useState(false);
  const [documentReady, setDocumentReady] = useState(false);
  const headers = { "X-Actor-Id": actor, "X-Tenant-Id": tenantId };

  async function createTenant() {
    setBusy(true);
    try {
      const response = await fetch(`${api}/tenants?name=Fluxera%20workspace`, { method: "POST", headers: { "X-Actor-Id": actor } });
      if (!response.ok) throw new Error("Workspace creation failed");
      const tenant = await response.json() as { id: string };
      setTenantId(tenant.id);
      setMessage("Workspace ready. Add a project to start a pre-bid review.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Request failed"); }
    finally { setBusy(false); }
  }

  async function createProject() {
    setBusy(true);
    try {
      const response = await fetch(`${api}/projects`, { method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify({ name: projectName }) });
      if (!response.ok) throw new Error("Project creation failed");
      const project = await response.json() as Project;
      setProjectId(project.id);
      setProjects((current) => [...current, project]);
      setMessage("Project ready. Upload the source RFP to begin page-level review.");
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
      setDocumentReady(true);
      setMessage("Source accepted and parsed. Pages are ready for evidence selection.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Upload failed"); }
    finally { setBusy(false); }
  }

  return (
    <main className="app-shell">
      <aside className="side-nav">
        <div className="brand"><img src="/logo%20(1).png" alt="Fluxera" /><span>BESS INTELLIGENCE PLATFORM</span></div>
        <nav aria-label="Primary navigation"><a className="active" href="#overview"><span>01</span>Overview</a><a href="#projects"><span>02</span>Projects</a><a href="#evidence"><span>03</span>Evidence review</a><a href="#register"><span>04</span>Requirement register</a></nav>
        <div className="side-footer"><span className="online-dot" /> Local workspace<br /><small>India beachhead</small></div>
      </aside>
      <section className="content" id="overview">
        <header className="topbar"><div><p className="eyebrow">PROCUREMENT INTELLIGENCE / PRE-BID</p><h1>BESS Intelligence Platform</h1></div><button className="user-chip" aria-label="Workspace administrator"><span>LA</span> Local administrator</button></header>
        <div className="welcome"><div><p className="kicker">EVIDENCE-LED DECISIONS</p><h2>Make every requirement<br /><em>traceable.</em></h2><p>Establish a reviewable baseline from source documents before bidder claims enter the process.</p></div><div className="assurance-badge"><strong>0</strong><span>verified requirements</span><i>Baseline not yet established</i></div></div>
        <section className="metrics" aria-label="Workspace summary"><div><span>ACTIVE PROJECTS</span><strong>{projects.length.toString().padStart(2, "0")}</strong><small>Across this workspace</small></div><div><span>SOURCE DOCUMENTS</span><strong>{documentReady ? "01" : "00"}</strong><small>Immutable PDF sources</small></div><div><span>REVIEW STATUS</span><strong className="blue-text">{documentReady ? "READY" : "OPEN"}</strong><small>{message}</small></div></section>
        <section className="workspace-card" id="projects"><div className="card-heading"><div><p className="eyebrow">PROCUREMENT INTELLIGENCE</p><h3>Create your first pre-bid review project</h3></div><span className="step-count">STEP 01 / 03</span></div><div className="setup-grid"><div className="form-panel"><label>Project name<input value={projectName} onChange={(event) => setProjectName(event.target.value)} placeholder="e.g. CEB RFP" /></label><div className="button-row"><button onClick={createTenant} disabled={busy}>{busy ? "Working..." : "Create workspace"}</button><button className="secondary" onClick={createProject} disabled={!tenantId || busy}>Create project <span>→</span></button></div></div><div className="upload-panel"><div className={`upload-icon ${documentReady ? "ready" : ""}`}>↑</div><div><strong>{documentReady ? "Source document ready" : "Upload source document"}</strong><p>{documentReady ? "Your PDF is ready for page inspection." : "PDF only · SHA-256 protected · Private storage"}</p></div><label className="upload-button">{documentReady ? "Replace PDF" : "Choose PDF"}<input type="file" accept="application/pdf" onChange={upload} disabled={!projectId || busy} /></label></div></div></section>
        <section className="next-step" id="evidence"><div><span className="next-number">02</span><div><p className="eyebrow">NEXT STEP</p><h3>Inspect pages and capture evidence</h3><p>Review exact source text, select evidence spans, and attach them to atomic requirements.</p></div></div><button className="icon-button" disabled={!documentReady} aria-label="Open evidence review">→</button></section>
      </section>
    </main>
  );
}
