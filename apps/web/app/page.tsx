"use client";

import { ChangeEvent, useState } from "react";

const api = process.env.NEXT_PUBLIC_API_URL ?? "/api";
const actor = process.env.NEXT_PUBLIC_ACTOR_ID ?? "00000000-0000-0000-0000-000000000001";
type Project = { id: string; name: string; timezone?: string; module_mode?: string };
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
type DesignBasisRecord = { id: string; version: number; status: string; data: Record<string, unknown> };
type Finding = { id: string; severity: string; state: string; title: string; explanation: string; suggested_action: string; resolution: string | null };
type Clarification = { id: string; question: string; status: string };
type Baseline = { id: string; version: number; content_hash: string; frozen_at: string };
type FormulaCalculation = { id: string; output_value: string; created_at: string; inputs: Record<string, number> };
type FormulaConfig = { id: string; version: number; template: string; source_clause_text: string | null; calculations: FormulaCalculation[] };
type FormulaResult = FormulaCalculation & { unit: string; formula: string };
type AssuranceReport = { project: { name: string }; requirement_coverage: { total: number; verified: number }; findings: Finding[]; clarifications: Clarification[]; baseline: Baseline | null; limitations: string[] };
const taxonomyCodes = ["ADM", "ELG", "PRJ", "TEC", "GRD", "SAF", "TST", "PER", "COM", "CON", "SCH", "OAM", "WAR", "LIF", "DOC"];

export default function Home() {
  const [tenantId, setTenantId] = useState("");
  const [projectId, setProjectId] = useState("");
  const [projectName, setProjectName] = useState("CEB RFP");
  const [projectMode, setProjectMode] = useState("pre_bid");
  const [bidderEntity, setBidderEntity] = useState("");
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
  const [designBasis, setDesignBasis] = useState<DesignBasisRecord | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [clarifications, setClarifications] = useState<Clarification[]>([]);
  const [baselines, setBaselines] = useState<Baseline[]>([]);
  const [formulaResult, setFormulaResult] = useState<FormulaResult | null>(null);
  const [formulaConfigs, setFormulaConfigs] = useState<FormulaConfig[]>([]);
  const [formulaConfigId, setFormulaConfigId] = useState("");
  const [formulaClauseText, setFormulaClauseText] = useState("");
  const [formulaInputs, setFormulaInputs] = useState({ quoted_capacity_charge: "100000", baseline_rte_percent: "85", guaranteed_rte_percent: "80" });
  const [assuranceReport, setAssuranceReport] = useState<AssuranceReport | null>(null);
  const [basisForm, setBasisForm] = useState({ rated_power_mw: "100", nominal_energy_mwh: "400", required_usable_energy_mwh: "380", duration_hours: "4", project_life_years: "20", availability_target_percent: "98", round_trip_efficiency_target_percent: "88", cycles_per_day: "1", use_case: "capacity", ac_dc_boundary: "AC point of interconnection", response_time_seconds: "", capacity_retention_final_year: "" });
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
      const response = await fetch(`${api}/projects`, { method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify({ name: projectName, module_mode: projectMode }) });
      if (!response.ok) throw new Error("Project creation failed");
      const project = await response.json() as Project;
      setProjectId(project.id);
      setProjects((current) => [...current, project]);
      setFormulaConfigs([]);
      setFormulaConfigId("");
      setMessage("Project ready. Upload the source RFP to begin page-level review.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Request failed"); }
    finally { setBusy(false); }
  }

  async function createBidderProfile() {
    if (!projectId || !bidderEntity.trim()) return;
    setBusy(true);
    try {
      const response = await fetch(`${api}/projects/${projectId}/bidder-profile`, { method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify({ legal_entity: bidderEntity }) });
      if (!response.ok) throw new Error((await response.json() as { detail?: string }).detail ?? "Bidder profile could not be saved");
      setMessage("Bidder legal entity recorded for Bid Intelligence review.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Bidder profile could not be saved"); }
    finally { setBusy(false); }
  }

  async function saveDesignBasis() {
    if (!projectId) return;
    setBusy(true);
    try {
      const numeric = (value: string) => Number(value);
      const payload = {
        rated_power_mw: numeric(basisForm.rated_power_mw), nominal_energy_mwh: numeric(basisForm.nominal_energy_mwh), required_usable_energy_mwh: numeric(basisForm.required_usable_energy_mwh), duration_hours: numeric(basisForm.duration_hours), project_life_years: numeric(basisForm.project_life_years), availability_target_percent: numeric(basisForm.availability_target_percent), round_trip_efficiency_target_percent: numeric(basisForm.round_trip_efficiency_target_percent), cycles_per_day: numeric(basisForm.cycles_per_day), use_case: basisForm.use_case, ac_dc_boundary: basisForm.ac_dc_boundary, response_time_seconds: basisForm.response_time_seconds ? numeric(basisForm.response_time_seconds) : null, capacity_retention_final_year: basisForm.capacity_retention_final_year ? numeric(basisForm.capacity_retention_final_year) : null,
      };
      const response = await fetch(`${api}/projects/${projectId}/design-basis`, { method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      if (!response.ok) throw new Error((await response.json() as { detail?: string }).detail ?? "Design Basis could not be saved");
      setDesignBasis(await response.json() as DesignBasisRecord);
      setMessage("Design Basis draft saved. Approve it when the engineering assumptions are confirmed.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Design Basis could not be saved"); }
    finally { setBusy(false); }
  }

  async function approveDesignBasis() {
    if (!projectId || !designBasis) return;
    setBusy(true);
    try {
      const response = await fetch(`${api}/projects/${projectId}/design-basis/${designBasis.id}/approve`, { method: "POST", headers });
      if (!response.ok) throw new Error((await response.json() as { detail?: string }).detail ?? "Design Basis approval failed");
      setDesignBasis(await response.json() as DesignBasisRecord);
      setMessage("Design Basis approved. It can now be used for deterministic completeness checks.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Design Basis approval failed"); }
    finally { setBusy(false); }
  }

  async function advanceWorkflow() {
    if (!designBasis) {
      setMessage("Save a validated Design Basis draft before moving to document review.");
      return;
    }
    if (designBasis.status === "draft") {
      await approveDesignBasis();
      return;
    }
    if (!documentReady) {
      document.getElementById("projects")?.scrollIntoView({ behavior: "smooth" });
      setMessage("Design Basis approved. Upload the RFP volumes, schedules, and addenda next.");
      return;
    }
    await openEvidenceReview();
  }

  async function runCompletenessAnalysis() {
    if (!projectId) return;
    setBusy(true);
    try {
      const response = await fetch(`${api}/projects/${projectId}/findings/run`, { method: "POST", headers });
      if (!response.ok) throw new Error((await response.json() as { detail?: string }).detail ?? "Completeness analysis failed");
      const result = await response.json() as Finding[];
      setFindings(result);
      const openFindings = result.filter((finding) => finding.state === "open");
      setMessage(openFindings.length ? `${openFindings.length} deterministic finding${openFindings.length === 1 ? "" : "s"} require review.` : "Completeness analysis found no open findings.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Completeness analysis failed"); }
    finally { setBusy(false); }
  }

  async function resolveFinding(finding: Finding, state: "accepted_risk" | "false_positive") {
    if (!projectId || !window.confirm(`Record ${state.replaceAll("_", " ")} for ${finding.title}?`)) return;
    const reason = window.prompt("Record the human review reason.");
    if (!reason?.trim()) return;
    setBusy(true);
    try {
      const response = await fetch(`${api}/projects/${projectId}/findings/${finding.id}/resolve`, { method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify({ state, reason }) });
      if (!response.ok) throw new Error((await response.json() as { detail?: string }).detail ?? "Finding resolution failed");
      const updated = await response.json() as Finding;
      setFindings((current) => current.map((item) => item.id === finding.id ? updated : item));
      setMessage(`Finding recorded as ${state.replaceAll("_", " ")}.`);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Finding resolution failed"); }
    finally { setBusy(false); }
  }

  async function createClarification(finding: Finding) {
    if (!projectId) return;
    const question = window.prompt("Enter the clarification question.");
    if (!question?.trim()) return;
    const rationale = window.prompt("Record the rationale for this question.");
    if (!rationale?.trim()) return;
    setBusy(true);
    try {
      const response = await fetch(`${api}/projects/${projectId}/clarifications`, { method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify({ finding_id: finding.id, question, rationale }) });
      if (!response.ok) throw new Error((await response.json() as { detail?: string }).detail ?? "Clarification creation failed");
      const clarification = await response.json() as Clarification;
      setClarifications((current) => [clarification, ...current]);
      setMessage("Clarification recorded for human follow-up.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Clarification creation failed"); }
    finally { setBusy(false); }
  }

  async function freezeBaseline() {
    if (!projectId || !window.confirm("Freeze an immutable baseline for this project?")) return;
    const reason = window.prompt("Record the approver reason.");
    if (!reason?.trim()) return;
    setBusy(true);
    try {
      const response = await fetch(`${api}/projects/${projectId}/baselines/freeze`, { method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify({ reason }) });
      if (!response.ok) throw new Error((await response.json() as { detail?: string }).detail ?? "Baseline freeze failed");
      const baseline = await response.json() as Baseline;
      setBaselines((current) => [baseline, ...current]);
      setMessage(`Baseline v${baseline.version} frozen with a reproducibility hash.`);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Baseline freeze failed"); }
    finally { setBusy(false); }
  }

  async function loadFormulaConfigs() {
    if (!projectId) return;
    const response = await fetch(`${api}/projects/${projectId}/formula-lab/configurations`, { headers });
    if (!response.ok) throw new Error("Formula Lab configurations could not be loaded");
    const configs = await response.json() as FormulaConfig[];
    setFormulaConfigs(configs);
    setFormulaConfigId((current) => current || configs[0]?.id || "");
  }

  async function saveFormulaConfig() {
    if (!projectId) return;
    setBusy(true);
    try {
      const response = await fetch(`${api}/projects/${projectId}/formula-lab/configurations`, { method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify({ template: "rte_adjusted_capacity_charge", source_clause_text: formulaClauseText || null }) });
      if (!response.ok) throw new Error((await response.json() as { detail?: string }).detail ?? "Formula configuration could not be saved");
      const config = await response.json() as FormulaConfig;
      setFormulaConfigs((current) => [config, ...current]);
      setFormulaConfigId(config.id);
      setMessage(`Formula configuration v${config.version} saved for this project.`);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Formula configuration could not be saved"); }
    finally { setBusy(false); }
  }

  async function runFormulaLab() {
    if (!projectId || !formulaConfigId) {
      setMessage("Save a Formula Lab configuration before running a scenario.");
      return;
    }
    setBusy(true);
    try {
      const response = await fetch(`${api}/projects/${projectId}/formula-lab/configurations/${formulaConfigId}/evaluate`, { method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify({ inputs: { quoted_capacity_charge: Number(formulaInputs.quoted_capacity_charge), baseline_rte_percent: Number(formulaInputs.baseline_rte_percent), guaranteed_rte_percent: Number(formulaInputs.guaranteed_rte_percent) } }) });
      if (!response.ok) throw new Error((await response.json() as { detail?: string }).detail ?? "Formula evaluation failed");
      setFormulaResult(await response.json() as FormulaResult);
      await loadFormulaConfigs();
      setMessage("Formula Lab result generated as an internal scenario, not an official ranking.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Formula evaluation failed"); }
    finally { setBusy(false); }
  }

  async function downloadVerifiedRegister() {
    if (!projectId) return;
    setBusy(true);
    try {
      const response = await fetch(`${api}/projects/${projectId}/requirements/export.csv`, { headers });
      if (!response.ok) throw new Error("Requirement register export failed");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "verified-requirements.csv";
      link.click();
      URL.revokeObjectURL(url);
      setMessage("Verified Requirement Register downloaded.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Requirement register export failed"); }
    finally { setBusy(false); }
  }

  async function openAssuranceReport() {
    if (!projectId) return;
    setBusy(true);
    try {
      const response = await fetch(`${api}/projects/${projectId}/pre-bid-assurance-report`, { headers });
      if (!response.ok) throw new Error("Pre-Bid Assurance Report could not be generated");
      setAssuranceReport(await response.json() as AssuranceReport);
      setMessage("Pre-Bid Assurance Report generated from current project records.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Pre-Bid Assurance Report could not be generated"); }
    finally { setBusy(false); }
  }

  const nextAction = !designBasis ? "Save Design Basis" : designBasis.status === "draft" ? "Approve Design Basis" : !documentReady ? "Upload source documents" : "Inspect pages and capture evidence";
  const nextDescription = !designBasis ? "A validated Design Basis is required before source review can begin." : designBasis.status === "draft" ? "Confirm the engineering assumptions to unlock source-document review." : !documentReady ? "Upload the RFP volumes, schedules, and addenda for this approved Design Basis." : "Review exact source text, select evidence spans, and attach them to atomic requirements.";

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
        <section className="workspace-card" id="projects"><div className="card-heading"><div><p className="eyebrow">PROCUREMENT INTELLIGENCE</p><h3>Create a procurement project</h3></div><span className="step-count">STEP 01 / 03</span></div><div className="setup-grid"><div className="form-panel"><label>Project name<input value={projectName} onChange={(event) => setProjectName(event.target.value)} placeholder="e.g. CEB RFP" /></label><label>Workflow mode<select value={projectMode} onChange={(event) => setProjectMode(event.target.value)}><option value="pre_bid">Pre-Bid Intelligence</option><option value="bid_intelligence">Bid Intelligence</option></select></label><div className="button-row"><button onClick={createTenant} disabled={busy}>{busy ? "Working..." : "Create workspace"}</button><button className="secondary" onClick={createProject} disabled={!tenantId || busy}>Create project <span>→</span></button></div></div><div className="upload-panel"><div className={`upload-icon ${documentReady ? "ready" : ""}`}>↑</div><div><strong>{documentReady ? "Add source documents" : "Upload source documents"}</strong><p>{documentReady ? "Add more PDFs to refresh the project report." : designBasis?.status === "approved" ? "PDF only · Select one or more files · SHA-256 protected" : "Approve the Design Basis to unlock document upload."}</p></div><label className="upload-button">Choose PDFs<input type="file" accept="application/pdf" multiple onChange={upload} disabled={!projectId || designBasis?.status !== "approved" || busy} /></label></div></div></section>
        {projectId && projects.find((project) => project.id === projectId)?.module_mode === "bid_intelligence" && <section className="baseline-card"><div className="card-heading"><div><p className="eyebrow">BID INTELLIGENCE</p><h3>Bidder profile</h3></div></div><div className="button-row"><label>Legal entity<input value={bidderEntity} onChange={(event) => setBidderEntity(event.target.value)} placeholder="Bidder legal entity" /></label><button onClick={createBidderProfile} disabled={busy || !bidderEntity.trim()}>Save bidder profile</button></div></section>}
        {projectId && <section className="basis-card"><div className="card-heading"><div><p className="eyebrow">PROJECT DESIGN BASIS</p><h3>Confirm BESS engineering assumptions</h3></div><span className="step-count">{designBasis ? `VERSION ${designBasis.version} / ${designBasis.status}` : "REQUIRED BEFORE BASELINE"}</span></div><div className="basis-grid">{Object.entries(basisForm).map(([key, value]) => <label key={key}>{key.replaceAll("_", " ")}<input value={value} onChange={(event) => setBasisForm((current) => ({ ...current, [key]: event.target.value }))} /></label>)}</div><div className="button-row"><button onClick={saveDesignBasis} disabled={busy}>Save Design Basis draft</button>{designBasis?.status === "draft" && <button className="secondary" onClick={approveDesignBasis} disabled={busy}>Approve Design Basis</button>}</div></section>}
        {report && <section className="report-card" id="register" aria-labelledby="report-title"><div className="card-heading"><div><p className="eyebrow">PRE-BID INTELLIGENCE REPORT</p><h3 id="report-title">Uploaded source coverage</h3></div><span className="report-state">{report.report_status.replaceAll("_", " ")}</span></div><div className="report-metrics"><div><strong>{report.document_count}</strong><span>source documents</span></div><div><strong>{report.pages_extracted}</strong><span>pages extracted</span></div><div><strong>{report.requirements_created}</strong><span>requirements reviewed</span></div><div><strong>{report.review_progress_percent}%</strong><span>review progress</span></div></div><ul className="source-list">{report.source_documents.map((document) => <li key={document.filename}><span>{document.filename}</span><small>{document.page_count} pages · {document.state.replaceAll("_", " ")}</small></li>)}</ul><p className="report-notice">{report.intelligence_notice}</p></section>}
        {designBasis?.status === "approved" && <section className="findings-card"><div className="card-heading"><div><p className="eyebrow">FINDINGS WORKBENCH</p><h3>Deterministic procurement checks</h3></div><button onClick={runCompletenessAnalysis} disabled={busy}>Run rules</button></div>{findings.length > 0 && <ul className="findings-list">{findings.map((finding) => <li key={finding.id}><strong>{finding.severity} · {finding.state.replaceAll("_", " ")}</strong><p>{finding.title}</p><p>{finding.explanation}</p><small>{finding.suggested_action}</small>{finding.resolution && <small className="finding-resolution">Resolution: {finding.resolution}</small>}{finding.state === "open" && <div className="finding-actions"><button onClick={() => createClarification(finding)} disabled={busy}>Create clarification</button><button onClick={() => resolveFinding(finding, "accepted_risk")} disabled={busy}>Accept risk</button><button className="secondary" onClick={() => resolveFinding(finding, "false_positive")} disabled={busy}>Mark false positive</button></div>}</li>)}</ul>}</section>}
        {projectId && <section className="baseline-card"><div className="card-heading"><div><p className="eyebrow">APPROVAL AND BASELINE</p><h3>Freeze approved procurement baseline</h3></div><button onClick={freezeBaseline} disabled={busy}>Freeze baseline</button></div>{clarifications.length > 0 && <p className="baseline-note">{clarifications.length} clarification{clarifications.length === 1 ? "" : "s"} recorded for review.</p>}{baselines.map((baseline) => <div className="baseline-record" key={baseline.id}><strong>Baseline v{baseline.version}</strong><small>{baseline.content_hash}</small></div>)}</section>}
        {projectId && <section className="baseline-card"><div className="card-heading"><div><p className="eyebrow">FORMULA LAB</p><h3>RTE-adjusted capacity charge</h3></div><button onClick={saveFormulaConfig} disabled={busy}>Save configuration</button></div><div className="basis-grid"><label>Quoted capacity charge (INR/MW/month)<input type="number" min="0" value={formulaInputs.quoted_capacity_charge} onChange={(event) => setFormulaInputs((current) => ({ ...current, quoted_capacity_charge: event.target.value }))} /></label><label>Tender baseline RTE (%)<input type="number" min="0" max="100" value={formulaInputs.baseline_rte_percent} onChange={(event) => setFormulaInputs((current) => ({ ...current, baseline_rte_percent: event.target.value }))} /></label><label>Guaranteed RTE (%)<input type="number" min="0" max="100" value={formulaInputs.guaranteed_rte_percent} onChange={(event) => setFormulaInputs((current) => ({ ...current, guaranteed_rte_percent: event.target.value }))} /></label><label>Source clause text (optional)<input value={formulaClauseText} onChange={(event) => setFormulaClauseText(event.target.value)} placeholder="Tender clause or assumption" /></label></div><div className="button-row"><label>Saved configuration<select value={formulaConfigId} onChange={(event) => setFormulaConfigId(event.target.value)} onFocus={loadFormulaConfigs}><option value="">Save a configuration to evaluate</option>{formulaConfigs.map((config) => <option key={config.id} value={config.id}>v{config.version} · {config.template}</option>)}</select></label><button onClick={runFormulaLab} disabled={busy || !formulaConfigId}>Run scenario</button></div>{formulaResult && <div className="baseline-record"><strong>{formulaResult.output_value} {formulaResult.unit}</strong><small>{formulaResult.formula}</small></div>}{formulaConfigs.map((config) => <div className="baseline-record" key={config.id}><strong>Configuration v{config.version}</strong><small>{config.source_clause_text || "No source clause recorded"}</small>{config.calculations.map((calculation) => <small key={calculation.id}>{calculation.output_value} · {new Date(calculation.created_at).toLocaleString()}</small>)}</div>)}</section>}
        <section className="next-step" id="evidence"><div><span className="next-number">02</span><div><p className="eyebrow">NEXT STEP</p><h3>{nextAction}</h3><p>{nextDescription}</p></div></div><button className="icon-button" onClick={advanceWorkflow} disabled={busy} aria-label={nextAction}>→</button></section>
        {reviewOpen && <section className="evidence-workbench" aria-labelledby="evidence-title"><div className="card-heading"><div><p className="eyebrow">MANUAL EVIDENCE REVIEW</p><h3 id="evidence-title">Create an evidence-backed requirement</h3></div><span className="step-count">STEP 02 / 03</span></div><div className="evidence-grid"><div className="page-panel"><label>Document page<select value={selectedPageId} onChange={(event) => { const page = pages.find((item) => item.id === event.target.value); setSelectedPageId(event.target.value); setEvidenceText(page?.text ?? ""); }}>{pages.map((page) => <option key={page.id} value={page.id}>Page {page.page_number}</option>)}</select></label><pre>{pages.find((page) => page.id === selectedPageId)?.text || "No extractable text was found on this page. Enter an exact transcription from the source."}</pre></div><div className="requirement-panel"><label>Exact source evidence<textarea value={evidenceText} onChange={(event) => setEvidenceText(event.target.value)} placeholder="Paste the exact text from the selected page" /></label><label>Taxonomy<select value={taxonomy} onChange={(event) => { setTaxonomy(event.target.value); setRequirementKey((key) => { const [source, , sequence = "0001"] = key.split("-"); return `${source}-${event.target.value}-${sequence}`; }); }}>{taxonomyCodes.map((code) => <option key={code}>{code}</option>)}</select></label><label>Stable requirement key<input value={requirementKey} onChange={(event) => setRequirementKey(event.target.value)} /><small>Format: three letters, three digits, taxonomy, four digits (for example: CEB160-PER-0042).</small></label><label>Atomic requirement<textarea value={requirementText} onChange={(event) => setRequirementText(event.target.value)} placeholder="State one testable procurement requirement" /></label><button onClick={createEvidenceBackedRequirement} disabled={busy || !evidenceText.trim() || !requirementText.trim()}>Create proposed requirement</button></div></div></section>}
        {requirements.length > 0 && <section className="review-register" aria-labelledby="register-title"><div className="card-heading"><div><p className="eyebrow">REVIEWER REGISTER</p><h3 id="register-title">Evidence-backed requirements</h3></div><span className="step-count">STEP 03 / 03</span></div><div className="requirement-list">{requirements.map((requirement) => <article key={requirement.id}><div className="requirement-heading"><div><strong>{requirement.stable_key}</strong><span>{requirement.taxonomy}</span></div><em className={`state-${requirement.state}`}>{requirement.state.replaceAll("_", " ")}</em></div><p>{requirement.text}</p><ul>{requirement.evidence.map((evidence) => <li key={evidence.id}>Page {evidence.page_number}: {evidence.exact_text}<small>{evidence.verified ? "Evidence verified" : "Evidence pending"}</small></li>)}</ul>{requirement.state === "proposed" && <div className="review-actions"><button onClick={() => reviewRequirement(requirement, "verified")} disabled={busy}>Verify requirement</button><button className="secondary" onClick={() => reviewRequirement(requirement, "rejected")} disabled={busy}>Reject</button></div>}</article>)}</div></section>}
        {report?.ready_for_export && <button className="export-button" onClick={downloadVerifiedRegister} disabled={busy}>Download verified Requirement Register (CSV)</button>}
        {projectId && <section className="baseline-card"><div className="card-heading"><div><p className="eyebrow">REPORTS</p><h3>Pre-Bid Assurance Report</h3></div><button onClick={openAssuranceReport} disabled={busy}>Generate report</button></div>{assuranceReport && <div className="report-preview"><div className="report-metrics"><div><strong>{assuranceReport.requirement_coverage.verified}/{assuranceReport.requirement_coverage.total}</strong><span>verified requirements</span></div><div><strong>{assuranceReport.findings.length}</strong><span>findings recorded</span></div><div><strong>{assuranceReport.clarifications.length}</strong><span>clarifications</span></div><div><strong>{assuranceReport.baseline ? `v${assuranceReport.baseline.version}` : "DRAFT"}</strong><span>baseline state</span></div></div><ul className="source-list">{assuranceReport.limitations.map((limitation) => <li key={limitation}><small>{limitation}</small></li>)}</ul><button className="secondary-report" onClick={() => window.print()}>Print report</button></div>}</section>}
      </section>
    </main>
  );
}
