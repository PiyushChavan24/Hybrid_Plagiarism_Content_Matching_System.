/** @format */

import React, { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import API from "../api";

function Upload() {
 const [file, setFile] = useState(null);
 const [title, setTitle] = useState("");
 const [uploading, setUploading] = useState(false);
 const [dragOver, setDragOver] = useState(false);
 const [error, setError] = useState("");
 const [success, setSuccess] = useState("");
 const fileRef = useRef();
 const navigate = useNavigate();

 const handleFile = (f) => {
  if (f && f.type === "application/pdf") {
   setFile(f);
   setError("");
   if (!title) {
    setTitle(f.name.replace(".pdf", ""));
   }
  } else {
   setError("Only PDF files are accepted.");
  }
 };

 const handleDrop = (e) => {
  e.preventDefault();
  setDragOver(false);
  const f = e.dataTransfer.files[0];
  handleFile(f);
 };

 const handleSubmit = async () => {
  if (!file) return setError("Please select a PDF file.");
  setUploading(true);
  setError("");
  setSuccess("");

  const formData = new FormData();
  formData.append("pdf", file);
  formData.append("title", title || file.name.replace(".pdf", ""));

  try {
   const res = await API.post("/projects/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
   });
   setSuccess(`"${res.data.project.title}" uploaded successfully!`);
   setFile(null);
   setTitle("");
   setTimeout(() => navigate("/"), 1500);
  } catch (err) {
   const msg = err.response?.data?.error || "Upload failed";
   setError(msg);
  } finally {
   setUploading(false);
  }
 };

 const formatSize = (bytes) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
 };

 return (
  <div>
   <div className="page-header">
    <h1>Upload Document</h1>
    <p>
     Upload a PDF to add it to your project library for plagiarism checking.
    </p>
   </div>

   {error && <div className="alert alert-error">{error}</div>}
   {success && <div className="alert alert-success">{success}</div>}

   <div
    className={`upload-zone ${dragOver ? "drag-over" : ""}`}
    onClick={() => fileRef.current?.click()}
    onDragOver={(e) => {
     e.preventDefault();
     setDragOver(true);
    }}
    onDragLeave={() => setDragOver(false)}
    onDrop={handleDrop}>
    <div className="upload-icon">⬆</div>
    <h3>Drop your PDF here</h3>
    <p>or click to browse files (max 20 MB)</p>
    <input
     ref={fileRef}
     type="file"
     accept=".pdf"
     style={{ display: "none" }}
     onChange={(e) => handleFile(e.target.files[0])}
    />
   </div>

   {file && (
    <div className="upload-form">
     <div className="file-info">
      <span>📄</span>
      <span className="file-name">{file.name}</span>
      <span className="file-size">{formatSize(file.size)}</span>
     </div>

     <div className="form-group">
      <label>Project Title</label>
      <input
       type="text"
       value={title}
       onChange={(e) => setTitle(e.target.value)}
       placeholder="Enter a title for this document"
      />
     </div>

     <button
      className="btn btn-primary"
      onClick={handleSubmit}
      disabled={uploading}>
      {uploading ? "Uploading..." : "Upload & Save"}
     </button>
    </div>
   )}
  </div>
 );
}

export default Upload;
