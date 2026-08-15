"use client";

import { ChangeEvent, useState } from "react";

const api = process.env.NEXT_PUBLIC_API_URL ?? "/api";
const actor = process.env.NEXT_PUBLIC_ACTOR_ID ?? "00000000-0000-0000-0000-000000000001";
type Project = { id: string; name: string; timezone?: string };
type PreBidReport = {
  document_count: number;
  pages_extracted: number;
  requirements_created: number;
  evidence_spans_count: number;
  review_progress_percent: number;
  ready_for_export: boolean;
  report_status: string;
  intelligence_notice: string;
  source_documents: Array<{ filename: string; page_count: number; state: string }>;
};
type PageRecord = { id: string; page_number: number; text: string };
type DetailedRequirement = {
  id: string;
  stable_key: string;
  taxonomy: string;
  text: string;
  state: string;
  version: number;
  evidence: Array<{ id: string; page_number: number; exact_text: string; verified: boolean }>;
};
const taxonomyCodes = ["ADM", "ELG", "PRJ", "TEC", "GRD", "SAF", "TST", "PER", "COM", "CON", "SCH", "OAM", "WAR", "LIF", "DOC"];

export default function Home() {
  const [tenantId, setTenantId] = useState("");
  const [projectId, setProjectId] = useState("");
  const [projectName, setProjectName] = useState("CEB RFP");
  const [projects, setProjects] = useState<Project[]>([]);
  const [message, setMessage] = useState("Create a workspace to begin your evidence review.");
  const [busy, setBusy] = useState(false);
  const [documentReady, setDocumentReady] = useState(false);
  const [report, setReport] = useState<PreBidReport | null>(null);
  const [pages, setPages] = useState<PageRecord[]>([]);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [selectedPageId, setSelectedPageId] = useState("");
  const [evidenceText, setEvidenceText] = useState("");
  const [requirementText, setRequirementText] = useState("");
  const [taxonomy, setTaxonomy] = useState("ADM");
  const [requirementKey, setRequirementKey] = useState("BES001-ADM-0001");
  const [requirements, setRequirements] = useState<DetailedRequirement[]>([]);
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
    const files = Array.from(event.target.files ?? []);
    if (!files.length || !projectId) return;
    setBusy(true);
    try {
      for (const file of files) {
        const form = new FormData(); form.append("file", file);
        const response = await fetch(`${api}/projects/${projectId}/documents`, { method: "POST", headers, body: form });
        if (!response.ok) throw new Error((await response.json() as { detail?: string }).detail ?? `Upload failed for ${file.name}`);
      }
      const reportResponse = await fetch(`${api}/projects/${projectId}/pre-bid-report`, { headers });
      if (!reportResponse.ok) throw new Error("Pre-Bid Intelligence report could not be generated");
      setReport(await reportResponse.json() as PreBidReport);
      setDocumentReady(true);
      setMessage(`${files.length} source document${files.length === 1 ? "" : "s"} added to the Pre-Bid Intelligence report.`);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Upload failed"); }
    finally { setBusy(false); }
  }

  async function openEvidenceReview() {
    if (!projectId) return;
    setBusy(true);
    try {
      const response = await fetch(`${api}/projects/${projectId}/pages`, { headers });
      if (!response.ok) throw new Error("Document pages could not be loaded");
      const loadedPages = await response.json() as PageRecord[];
      setPages(loadedPages);
      setSelectedPageId(loadedPages[0]?.id ?? "");
      setEvidenceText(loadedPages[0]?.text ?? "");
      await loadRequirements();
      setReviewOpen(true);
      setMessage("Select exact source text and create an evidence-backed proposed requirement.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Could not open evidence review"); }
    finally { setBusy(false); }
  }

  async function loadRequirements() {
    if (!projectId) return;
    const response = await fetch(`${api}/projects/${projectId}/requirements/detailed`, { headers });
    if (!response.ok) throw new Error("Requirement register could not be loaded");
    setRequirements(await response.json() as DetailedRequirement[]);
  }

  async function createEvidenceBackedRequirement() {
    if (!projectId || !selectedPageId || !evidenceText.trim() || !requirementText.trim()) return;
    setBusy(true);
    try {
      const evidenceResponse = await fetch(`${api}/projects/${projectId}/evidence`, { method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify({ page_id: selectedPageId, exact_text: evidenceText }) });
      if (!evidenceResponse.ok) throw new Error((await evidenceResponse.json() as { detail?: string }).detail ?? "Evidence creation failed");
      const evidence = await evidenceResponse.json() as { id: string };
      const requirementResponse = await fetch(`${api}/projects/${projectId}/requirements`, { method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify({ stable_key: requirementKey, taxonomy, text: requirementText, evidence_span_ids: [evidence.id] }) });
      if (!requirementResponse.ok) throw new Error((await requirementResponse.json() as { detail?: string }).detail ?? "Requirement creation failed");
      const reportResponse = await fetch(`${api}/projects/${projectId}/pre-bid-report`, { headers });
      if (reportResponse.ok) setReport(await reportResponse.json() as PreBidReport);
      setRequirementText("");
      setRequirementKey((key) => {
        const [source, category, sequence = "0000"] = key.split("-");
        return `${source}-${category}-${(Number(sequence) + 1).toString().padStart(4, "0")}`;
      });
      await loadRequirements();
      setMessage("Proposed requirement created and linked to its source evidence. Reviewer verification is next.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Requirement creation failed"); }
    finally { setBusy(false); }
  }

  async function reviewRequirement(requirement: DetailedRequirement, decision: "verified" | "rejected") {
    if (!projectId) return;
    setBusy(true);
    try {
      if (decision === "verified") {
        for (const evidence of requirement.evidence.filter((item) => !item.verified)) {
          const evidenceResponse = await fetch(`${api}/projects/${projectId}/requirements/${requirement.id}/evidence/${evidence.id}/verify`, { method: "POST", headers });
          if (!evidenceResponse.ok) throw new Error("Evidence verification failed");
        }
      }
      const response = await fetch(`${api}/projects/${projectId}/requirements/${requirement.id}/review`, { method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify({ decision, expected_version: requirement.version }) });
      if (!response.ok) throw new Error((await response.json() as { detail?: string }).detail ?? "Review decision failed");
      await loadRequirements();
      const reportResponse = await fetch(`${api}/projects/${projectId}/pre-bid-report`, { headers });
      if (reportResponse.ok) setReport(await reportResponse.json() as PreBidReport);
      setMessage(`Requirement ${decision}. The decision and reviewer are recorded in the audit trail.`);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Review decision failed"); }
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
        <section className="workspace-card" id="projects"><div className="card-heading"><div><p className="eyebrow">PROCUREMENT INTELLIGENCE</p><h3>Create your first pre-bid review project</h3></div><span className="step-count">STEP 01 / 03</span></div><div className="setup-grid"><div className="form-panel"><label>Project name<input value={projectName} onChange={(event) => setProjectName(event.target.value)} placeholder="e.g. CEB RFP" /></label><div className="button-row"><button onClick={createTenant} disabled={busy}>{busy ? "Working..." : "Create workspace"}</button><button className="secondary" onClick={createProject} disabled={!tenantId || busy}>Create project <span>→</span></button></div></div><div className="upload-panel"><div className={`upload-icon ${documentReady ? "ready" : ""}`}>↑</div><div><strong>{documentReady ? "Add source documents" : "Upload source documents"}</strong><p>{documentReady ? "Add more PDFs to refresh the project report." : "PDF only · Select one or more files · SHA-256 protected"}</p></div><label className="upload-button">Choose PDFs<input type="file" accept="application/pdf" multiple onChange={upload} disabled={!projectId || busy} /></label></div></div></section>
        {report && <section className="report-card" id="register" aria-labelledby="report-title"><div className="card-heading"><div><p className="eyebrow">PRE-BID INTELLIGENCE REPORT</p><h3 id="report-title">Uploaded source coverage</h3></div><span className="report-state">{report.report_status.replaceAll("_", " ")}</span></div><div className="report-metrics"><div><strong>{report.document_count}</strong><span>source documents</span></div><div><strong>{report.pages_extracted}</strong><span>pages extracted</span></div><div><strong>{report.requirements_created}</strong><span>requirements reviewed</span></div><div><strong>{report.review_progress_percent}%</strong><span>review progress</span></div></div><ul className="source-list">{report.source_documents.map((document) => <li key={document.filename}><span>{document.filename}</span><small>{document.page_count} pages · {document.state.replaceAll("_", " ")}</small></li>)}</ul><p className="report-notice">{report.intelligence_notice}</p></section>}
        <section className="next-step" id="evidence"><div><span className="next-number">02</span><div><p className="eyebrow">NEXT STEP</p><h3>Inspect pages and capture evidence</h3><p>Review exact source text, select evidence spans, and attach them to atomic requirements.</p></div></div><button className="icon-button" onClick={openEvidenceReview} disabled={!documentReady || busy} aria-label="Open evidence review">→</button></section>
        {reviewOpen && <section className="evidence-workbench" aria-labelledby="evidence-title"><div className="card-heading"><div><p className="eyebrow">MANUAL EVIDENCE REVIEW</p><h3 id="evidence-title">Create an evidence-backed requirement</h3></div><span className="step-count">STEP 02 / 03</span></div><div className="evidence-grid"><div className="page-panel"><label>Document page<select value={selectedPageId} onChange={(event) => { const page = pages.find((item) => item.id === event.target.value); setSelectedPageId(event.target.value); setEvidenceText(page?.text ?? ""); }}>{pages.map((page) => <option key={page.id} value={page.id}>Page {page.page_number}</option>)}</select></label><pre>{pages.find((page) => page.id === selectedPageId)?.text || "No extractable text was found on this page. Enter an exact transcription from the source."}</pre></div><div className="requirement-panel"><label>Exact source evidence<textarea value={evidenceText} onChange={(event) => setEvidenceText(event.target.value)} placeholder="Paste the exact text from the selected page" /></label><label>Taxonomy<select value={taxonomy} onChange={(event) => { setTaxonomy(event.target.value); setRequirementKey((key) => { const [source, , sequence = "0001"] = key.split("-"); return `${source}-${event.target.value}-${sequence}`; }); }}>{taxonomyCodes.map((code) => <option key={code}>{code}</option>)}</select></label><label>Stable requirement key<input value={requirementKey} onChange={(event) => setRequirementKey(event.target.value)} /><small>Format: three letters, three digits, taxonomy, four digits (for example: CEB160-PER-0042).</small></label><label>Atomic requirement<textarea value={requirementText} onChange={(event) => setRequirementText(event.target.value)} placeholder="State one testable procurement requirement" /></label><button onClick={createEvidenceBackedRequirement} disabled={busy || !evidenceText.trim() || !requirementText.trim()}>Create proposed requirement</button></div></div></section>}
        {requirements.length > 0 && <section className="review-register" aria-labelledby="register-title"><div className="card-heading"><div><p className="eyebrow">REVIEWER REGISTER</p><h3 id="register-title">Evidence-backed requirements</h3></div><span className="step-count">STEP 03 / 03</span></div><div className="requirement-list">{requirements.map((requirement) => <article key={requirement.id}><div className="requirement-heading"><div><strong>{requirement.stable_key}</strong><span>{requirement.taxonomy}</span></div><em className={`state-${requirement.state}`}>{requirement.state.replaceAll("_", " ")}</em></div><p>{requirement.text}</p><ul>{requirement.evidence.map((evidence) => <li key={evidence.id}>Page {evidence.page_number}: {evidence.exact_text}<small>{evidence.verified ? "Evidence verified" : "Evidence pending"}</small></li>)}</ul>{requirement.state === "proposed" && <div className="review-actions"><button onClick={() => reviewRequirement(requirement, "verified")} disabled={busy}>Verify requirement</button><button className="secondary" onClick={() => reviewRequirement(requirement, "rejected")} disabled={busy}>Reject</button></div>}</article>)}</div></section>}
      </section>
    </main>
  );
}
