/** @format */

import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import API from "../api";

function ThresholdBar({ score, threshold }) {
 const pct = Math.min(score * 100, 100);
 const tPct = Math.min(threshold * 100, 100);
 const color =
  score >= 0.8
   ? "var(--risk-high)"
   : score >= threshold
     ? "var(--risk-medium)"
     : "var(--risk-low)";

 return (
  <div className="threshold-bar">
   <div className="bar-fill" style={{ width: `${pct}%`, background: color }} />
   <div
    className="threshold-marker"
    style={{ left: `${tPct}%` }}
    title={`Threshold: ${tPct.toFixed(1)}%`}
   />
  </div>
 );
}

function SnippetCard({ snippet, index }) {
 const simPct = (snippet.similarity * 100).toFixed(1);
 const level =
  snippet.similarity >= 0.9
   ? "high"
   : snippet.similarity >= 0.8
     ? "medium"
     : "low";

 return (
  <div className="snippet-card">
   <div className="snippet-header">
    <span className="snippet-num">Match #{index + 1}</span>
    <span
     className={`risk-badge ${level}`}
     style={{ fontSize: 11, padding: "3px 10px" }}>
     {simPct}% similar
    </span>
   </div>
   <div className="snippet-body">
    <div className="snippet-side source">
     <div className="snippet-label">Source Document</div>
     <div className="snippet-text">{snippet.source_sentence}</div>
    </div>
    <div className="snippet-divider">↔</div>
    <div className="snippet-side suspect">
     <div className="snippet-label">Matched Document</div>
     <div className="snippet-text">{snippet.suspect_sentence}</div>
    </div>
   </div>
  </div>
 );
}

function Report() {
 const { id } = useParams();
 const [report, setReport] = useState(null);
 const [loading, setLoading] = useState(true);
 const [error, setError] = useState("");
 const [expandedComp, setExpandedComp] = useState(null);

 useEffect(() => {
  fetchReport();
 }, [id]);

 const fetchReport = async () => {
  try {
   const res = await API.get(`/projects/${id}/report`);
   setReport(res.data);
  } catch (err) {
   setError(err.response?.data?.error || "Failed to load report");
  } finally {
   setLoading(false);
  }
 };

 if (loading) {
  return (
   <div className="loading">
    <div className="spinner" />
    <span>Loading report...</span>
   </div>
  );
 }

 if (error) {
  return (
   <div>
    <div className="alert alert-error">{error}</div>
    <Link to="/" className="btn btn-secondary">
     Back to Dashboard
    </Link>
   </div>
  );
 }

 if (!report || !report.comparisons?.length) {
  return (
   <div className="empty-state card">
    <div className="empty-icon">📊</div>
    <h3>No report available</h3>
    <p>Run a plagiarism check first from the dashboard.</p>
    <Link to="/" className="btn btn-primary">
     Go to Dashboard
    </Link>
   </div>
  );
 }

 const totalSnippets = report.comparisons.reduce(
  (sum, c) => sum + (c.snippets?.length || 0),
  0,
 );

 const totalTime = report.comparisons.reduce(
  (sum, c) => sum + (c.metadata?.elapsed_seconds || 0),
  0,
 );

 return (
  <div>
   <div className="report-header">
    <div>
     <h1>Plagiarism Report</h1>
     <p style={{ color: "var(--text-secondary)", marginTop: 4 }}>
      {report.totalComparisons} document
      {report.totalComparisons !== 1 ? "s" : ""} compared &nbsp;·&nbsp;Total
      time: {totalTime.toFixed(2)}s
     </p>
    </div>
    <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
     <span className={`risk-badge ${report.highestRisk?.toLowerCase()}`}>
      {report.highestRisk} RISK
     </span>
     <Link to="/" className="btn btn-secondary btn-sm">
      Back
     </Link>
    </div>
   </div>

   <div className="score-grid">
    <div className="score-card">
     <div className="score-label">Highest Score</div>
     <div
      className={`score-value ${
       report.highestScore >= 0.8
        ? "high"
        : report.highestScore >= 0.65
          ? "medium"
          : "low"
      }`}>
      {(report.highestScore * 100).toFixed(1)}%
     </div>
    </div>
    <div className="score-card">
     <div className="score-label">Comparisons</div>
     <div className="score-value">{report.totalComparisons}</div>
    </div>
    <div className="score-card">
     <div className="score-label">Total Matches</div>
     <div className="score-value">{totalSnippets}</div>
    </div>
    <div className="score-card">
     <div className="score-label">Pipeline Time</div>
     <div className="score-value" style={{ fontSize: 22 }}>
      {totalTime.toFixed(2)}s
     </div>
    </div>
   </div>

   <div style={{ marginBottom: 12 }}>
    <h2 style={{ fontSize: 18, marginBottom: 16 }}>Comparison Details</h2>
    <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 16 }}>
     Click on a comparison to expand and view matching passages.
    </p>
   </div>

   <div className="comparison-list">
    {report.comparisons.map((comp, i) => (
     <div key={i} className="card" style={{ padding: 0, overflow: "hidden" }}>
      <div
       className="comparison-item"
       style={{ cursor: "pointer" }}
       onClick={() => setExpandedComp(expandedComp === i ? null : i)}>
       <div>
        <div className="comp-title">
         {comp.suspect_title}
         <span
          style={{
           fontSize: 12,
           color: "var(--text-muted)",
           fontWeight: 400,
           marginLeft: 8,
          }}>
          {expandedComp === i ? "▲" : "▼"}
         </span>
        </div>
        <ThresholdBar
         score={comp.scores.c_final}
         threshold={comp.threshold.t_cal}
        />
        <div
         style={{
          fontSize: 12,
          color: "var(--text-muted)",
          marginTop: 4,
          display: "flex",
          flexWrap: "wrap",
          gap: "4px 0",
         }}>
         <span>Lex: {(comp.scores.s_lex * 100).toFixed(1)}%</span>
         <span>&nbsp;·&nbsp;</span>
         <span>Sem: {(comp.scores.s_sem * 100).toFixed(1)}%</span>
         <span>&nbsp;·&nbsp;</span>
         <span>Sty: {(comp.scores.s_sty * 100).toFixed(1)}%</span>
         <span>&nbsp;·&nbsp;</span>
         <span>T_cal: {(comp.threshold.t_cal * 100).toFixed(1)}%</span>
         <span>&nbsp;·&nbsp;</span>
         <span>Snippets: {comp.snippets?.length || 0}</span>
         <span>&nbsp;·&nbsp;</span>
         <span>Time: {comp.metadata?.elapsed_seconds?.toFixed(2) || "—"}s</span>
        </div>
       </div>
       <div className="comp-score">
        {(comp.scores.c_final * 100).toFixed(1)}%
       </div>
       <span className={`risk-badge ${comp.risk.level.toLowerCase()}`}>
        {comp.risk.level}
       </span>
      </div>

      {expandedComp === i && (
       <div className="snippets-section">
        {/* Metadata summary */}
        <div
         style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
          gap: 8,
          marginBottom: 16,
          padding: "12px 16px",
          background: "var(--bg-card)",
          borderRadius: "var(--radius-sm)",
          fontSize: 12,
         }}>
         <div>
          <span style={{ color: "var(--text-muted)" }}>Source sentences: </span>
          <strong>{comp.metadata?.source_sentences || "—"}</strong>
         </div>
         <div>
          <span style={{ color: "var(--text-muted)" }}>
           Suspect sentences:{" "}
          </span>
          <strong>{comp.metadata?.suspect_sentences || "—"}</strong>
         </div>
         <div>
          <span style={{ color: "var(--text-muted)" }}>Source tokens: </span>
          <strong>{comp.metadata?.source_tokens || "—"}</strong>
         </div>
         <div>
          <span style={{ color: "var(--text-muted)" }}>Suspect tokens: </span>
          <strong>{comp.metadata?.suspect_tokens || "—"}</strong>
         </div>
         <div>
          <span style={{ color: "var(--text-muted)" }}>Pipeline time: </span>
          <strong>{comp.metadata?.elapsed_seconds?.toFixed(3) || "—"}s</strong>
         </div>
         <div>
          <span style={{ color: "var(--text-muted)" }}>Confidence: </span>
          <strong>{comp.risk.confidence}</strong>
         </div>
        </div>

        {/* Snippets */}
        {comp.snippets?.length > 0 ? (
         <>
          <div className="snippets-title">
           Matching Passages ({comp.snippets.length} found)
          </div>
          {comp.snippets.map((snippet, j) => (
           <SnippetCard key={j} snippet={snippet} index={j} />
          ))}
         </>
        ) : (
         <div
          style={{
           textAlign: "center",
           color: "var(--text-muted)",
           padding: "20px 0",
          }}>
          No specific matching passages found above threshold.
         </div>
        )}
       </div>
      )}
     </div>
    ))}
   </div>
  </div>
 );
}

export default Report;
