/** @format */

import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import API from "../api";

function Dashboard() {
 const [projects, setProjects] = useState([]);
 const [loading, setLoading] = useState(true);
 const [comparing, setComparing] = useState(null);
 const [error, setError] = useState("");
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
         disabled={comparing === p._id}>
         {comparing === p._id ? "Analyzing..." : "Check Plagiarism"}
        </button>
        <Link to={`/report/${p._id}`} className="btn btn-secondary btn-sm">
         View Report
        </Link>
       </div>
      </div>
     ))}
    </div>
   )}
  </div>
 );
}

export default Dashboard;
