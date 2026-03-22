/** @format */

import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import API from "../api";

function MethodComparison({ data, onClose }) {
 if (!data) return null;

 const { hpcm, traditional, projectTitle } = data;

 return (
  <div
   style={{
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: "rgba(0,0,0,0.7)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1000,
    padding: 20,
   }}
   onClick={onClose}>
   <div
    style={{
     background: "var(--bg-card)",
     borderRadius: "var(--radius)",
     border: "1px solid var(--border)",
     maxWidth: 900,
     width: "100%",
     maxHeight: "90vh",
     overflow: "auto",
     padding: 32,
    }}
    onClick={(e) => e.stopPropagation()}>
    <div
     style={{
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      marginBottom: 24,
     }}>
     <div>
      <h2 style={{ fontSize: 20, marginBottom: 4 }}>Method Comparison</h2>
      <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>
       {projectTitle}
      </p>
     </div>
     <button className="btn btn-secondary btn-sm" onClick={onClose}>
      Close
     </button>
    </div>

    {/* Time comparison */}
    <div
     style={{
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: 16,
      marginBottom: 24,
     }}>
     <div className="score-card">
      <div className="score-label">Traditional (TF-IDF)</div>
      <div className="score-value low">
       {traditional?.elapsed_seconds?.toFixed(2) || "—"}s
      </div>
     </div>
     <div className="score-card">
      <div className="score-label">HPCM (Full Pipeline)</div>
      <div className="score-value medium">
       {hpcm?.total_elapsed_seconds?.toFixed(2) ||
        hpcm?.comparisons
         ?.reduce((sum, c) => sum + (c.metadata?.elapsed_seconds || 0), 0)
         .toFixed(2) ||
        "—"}
       s
      </div>
     </div>
    </div>

    {/* Side by side comparison table */}
    <div style={{ overflowX: "auto" }}>
     <table
      style={{
       width: "100%",
       borderCollapse: "collapse",
       fontSize: 14,
      }}>
      <thead>
       <tr
        style={{
         borderBottom: "2px solid var(--border)",
         textAlign: "left",
        }}>
        <th style={{ padding: "10px 12px", color: "var(--text-secondary)" }}>
         Document
        </th>
        <th
         style={{
          padding: "10px 12px",
          color: "var(--text-secondary)",
          textAlign: "center",
         }}>
         Traditional
         <br />
         <span style={{ fontSize: 11, fontWeight: 400 }}>TF-IDF Only</span>
        </th>
        <th
         style={{
          padding: "10px 12px",
          color: "var(--text-secondary)",
          textAlign: "center",
         }}>
         HPCM
         <br />
         <span style={{ fontSize: 11, fontWeight: 400 }}>Lex + Sem + Sty</span>
        </th>
        <th
         style={{
          padding: "10px 12px",
          color: "var(--text-secondary)",
          textAlign: "center",
         }}>
         Difference
        </th>
       </tr>
      </thead>
      <tbody>
       {traditional?.comparisons?.map((trad, i) => {
        const hpcmComp = hpcm?.comparisons?.find(
         (h) => h.suspect_id === trad.suspect_id,
        );
        const tradScore = trad.score || 0;
        const hpcmScore = hpcmComp?.scores?.c_final || 0;
        const diff = hpcmScore - tradScore;
        const diffColor =
         diff > 0.1
          ? "var(--risk-high)"
          : diff < -0.1
            ? "var(--risk-low)"
            : "var(--text-secondary)";

        return (
         <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
          <td style={{ padding: "12px" }}>
           <div style={{ fontWeight: 600 }}>{trad.suspect_title}</div>
          </td>
          <td style={{ padding: "12px", textAlign: "center" }}>
           <div
            style={{
             fontFamily: "var(--font-mono)",
             fontWeight: 700,
             fontSize: 16,
            }}>
            {(tradScore * 100).toFixed(1)}%
           </div>
           <span
            className={`risk-badge ${trad.risk?.toLowerCase()}`}
            style={{ fontSize: 10, padding: "2px 8px" }}>
            {trad.risk}
           </span>
          </td>
          <td style={{ padding: "12px", textAlign: "center" }}>
           <div
            style={{
             fontFamily: "var(--font-mono)",
             fontWeight: 700,
             fontSize: 16,
            }}>
            {(hpcmScore * 100).toFixed(1)}%
           </div>
           <span
            className={`risk-badge ${hpcmComp?.risk?.level?.toLowerCase()}`}
            style={{ fontSize: 10, padding: "2px 8px" }}>
            {hpcmComp?.risk?.level || "—"}
           </span>
          </td>
          <td
           style={{
            padding: "12px",
            textAlign: "center",
            fontFamily: "var(--font-mono)",
            fontWeight: 600,
            color: diffColor,
           }}>
           {diff > 0 ? "+" : ""}
           {(diff * 100).toFixed(1)}%
           {diff > 0.1 && (
            <div
             style={{
              fontSize: 10,
              fontFamily: "var(--font-body)",
              fontWeight: 400,
              marginTop: 2,
             }}>
             HPCM caught more
            </div>
           )}
          </td>
         </tr>
        );
       })}
      </tbody>
     </table>
    </div>

    {/* Summary */}
    <div
     style={{
      marginTop: 20,
      padding: 16,
      background: "var(--bg-secondary)",
      borderRadius: "var(--radius-sm)",
      fontSize: 13,
      color: "var(--text-secondary)",
      lineHeight: 1.6,
     }}>
     <strong style={{ color: "var(--text-primary)" }}>Key Insight:</strong>{" "}
     Traditional TF-IDF only detects word-level overlap (copy-paste). HPCM's
     semantic layer (Sentence-BERT) catches paraphrased content where words are
     different but meaning is preserved. Documents showing a large positive
     difference (+%) are likely paraphrased — caught by HPCM but missed by
     traditional methods.
    </div>
   </div>
  </div>
 );
}

function Dashboard() {
 const [projects, setProjects] = useState([]);
 const [loading, setLoading] = useState(true);
 const [comparing, setComparing] = useState(null);
 const [benchmarking, setBenchmarking] = useState(null);
 const [error, setError] = useState("");
 const [comparisonData, setComparisonData] = useState(null);
 const navigate = useNavigate();

 useEffect(() => {
  fetchProjects();
 }, []);

 const fetchProjects = async () => {
  try {
   const res = await API.get("/projects");
   setProjects(res.data);
  } catch (err) {
   setError("Failed to load projects");
  } finally {
   setLoading(false);
  }
 };

 const handleCompare = async (id) => {
  setComparing(id);
  setError("");
  try {
   await API.post(`/projects/${id}/compare`);
   navigate(`/report/${id}`);
  } catch (err) {
   const msg = err.response?.data?.error || "Comparison failed";
   setError(msg);
  } finally {
   setComparing(null);
  }
 };

 const handleBenchmark = async (id, title) => {
  setBenchmarking(id);
  setError("");
  try {
   // Run both methods
   const [hpcmRes, tradRes] = await Promise.all([
    API.post(`/projects/${id}/compare`),
    API.post(`/projects/${id}/compare_traditional`),
   ]);

   setComparisonData({
    hpcm: hpcmRes.data.report || hpcmRes.data,
    traditional: tradRes.data,
    projectTitle: title,
   });
  } catch (err) {
   const msg = err.response?.data?.error || "Benchmark failed";
   setError(msg);
  } finally {
   setBenchmarking(null);
  }
 };

 if (loading) {
  return (
   <div className="loading">
    <div className="spinner" />
    <span>Loading projects...</span>
   </div>
  );
 }

 return (
  <div>
   <div className="page-header">
    <h1>Projects</h1>
    <p>Upload PDFs and run plagiarism checks across your document library.</p>
   </div>

   {error && <div className="alert alert-error">{error}</div>}

   {projects.length === 0 ? (
    <div className="empty-state card">
     <div className="empty-icon">📄</div>
     <h3>No projects yet</h3>
     <p>Upload your first PDF to get started.</p>
     <Link to="/upload" className="btn btn-primary">
      Upload PDF
     </Link>
    </div>
   ) : (
    <div className="project-grid">
     {projects.map((p) => (
      <div key={p._id} className="card project-card">
       <div className="project-title">
        <span>📄</span>
        {p.title}
       </div>
       <div className="project-meta">
        <span>{p.filename}</span>
        <span>{p.pageCount} pages</span>
        <span>{p.wordCount?.toLocaleString()} words</span>
       </div>
       <div className="project-actions">
        <button
         className="btn btn-primary btn-sm"
         onClick={() => handleCompare(p._id)}
         disabled={comparing === p._id || benchmarking === p._id}>
         {comparing === p._id ? "Analyzing..." : "Check Plagiarism"}
        </button>
        <button
         className="btn btn-secondary btn-sm"
         onClick={() => handleBenchmark(p._id, p.title)}
         disabled={comparing === p._id || benchmarking === p._id}
         style={{
          borderColor: "var(--accent)",
          color: "var(--accent)",
         }}>
         {benchmarking === p._id ? "Benchmarking..." : "Compare Methods"}
        </button>
        <Link to={`/report/${p._id}`} className="btn btn-secondary btn-sm">
         View Report
        </Link>
       </div>
      </div>
     ))}
    </div>
   )}

   {comparisonData && (
    <MethodComparison
     data={comparisonData}
     onClose={() => setComparisonData(null)}
    />
   )}
  </div>
 );
}

export default Dashboard;
