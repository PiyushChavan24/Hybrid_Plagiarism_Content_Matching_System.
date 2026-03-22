/** @format */

const express = require("express");
const multer = require("multer");
const mongoose = require("mongoose");
const { GridFSBucket } = require("mongodb");
const pdfParse = require("pdf-parse");
const axios = require("axios");
const fs = require("fs");
const path = require("path");

const Project = require("../models/Project");
const Report = require("../models/Report");

const router = express.Router();

// ---------------------------------------------------------------------------
// Multer — store PDF temporarily on disk, then push to GridFS
// ---------------------------------------------------------------------------
const upload = multer({
 dest: path.join(__dirname, "..", "uploads_temp"),
 limits: { fileSize: 20 * 1024 * 1024 }, // 20 MB
 fileFilter: (req, file, cb) => {
  if (file.mimetype === "application/pdf") {
   cb(null, true);
  } else {
   cb(new Error("Only PDF files are allowed"), false);
  }
 },
});

// ---------------------------------------------------------------------------
// Helper: upload file buffer to GridFS
// ---------------------------------------------------------------------------
async function uploadToGridFS(filePath, filename) {
 const db = mongoose.connection.db;
 const bucket = new GridFSBucket(db, { bucketName: "uploads" });

 return new Promise((resolve, reject) => {
  const readStream = fs.createReadStream(filePath);
  const uploadStream = bucket.openUploadStream(filename, {
   contentType: "application/pdf",
  });

  readStream
   .pipe(uploadStream)
   .on("error", reject)
   .on("finish", () => {
    fs.unlink(filePath, () => {});
    resolve(uploadStream.id);
   });
 });
}

// ---------------------------------------------------------------------------
// Helper: get FastAPI headers (with HF token if available)
// ---------------------------------------------------------------------------
function getMLHeaders() {
 const headers = {};
 if (process.env.HF_TOKEN) {
  headers["Authorization"] = `Bearer ${process.env.HF_TOKEN}`;
 }
 return headers;
}

// ===========================================================================
// POST /api/projects/upload — Upload PDF, extract text, save to MongoDB
// ===========================================================================
router.post("/upload", upload.single("pdf"), async (req, res) => {
 try {
  if (!req.file) {
   return res.status(400).json({ error: "No PDF file uploaded" });
  }

  const title = req.body.title || req.file.originalname.replace(".pdf", "");

  // Extract text from PDF
  const pdfBuffer = fs.readFileSync(req.file.path);
  const pdfData = await pdfParse(pdfBuffer);
  const extractedText = pdfData.text;

  if (!extractedText || extractedText.trim().length === 0) {
   fs.unlink(req.file.path, () => {});
   return res.status(400).json({ error: "Could not extract text from PDF" });
  }

  // Upload PDF to GridFS
  const fileId = await uploadToGridFS(req.file.path, req.file.originalname);

  // Save project to MongoDB
  const project = await Project.create({
   title,
   text: extractedText,
   filename: req.file.originalname,
   fileId,
   pageCount: pdfData.numpages || 0,
   wordCount: extractedText.split(/\s+/).length,
  });

  console.log(`Project uploaded: ${project._id} — "${title}"`);

  // Pre-compute SBERT embeddings for faster future comparisons
  try {
   const fastApiUrl = process.env.FASTAPI_URL || "http://localhost:8000";
   const embedRes = await axios.post(
    `${fastApiUrl}/embed`,
    { text: extractedText },
    { headers: getMLHeaders(), timeout: 60000 },
   );

   project.embeddings = embedRes.data.embedding;
   project.embeddingVersion = embedRes.data.model;
   await project.save();
   console.log(
    `Embeddings computed for: ${project._id} (${embedRes.data.num_sentences} sentences)`,
   );
  } catch (err) {
   console.warn("Embedding pre-computation failed:", err.message);
   // Non-blocking — comparison still works without pre-computed embeddings
  }

  res.status(201).json({
   message: "Project uploaded successfully",
   project: {
    id: project._id,
    title: project.title,
    filename: project.filename,
    pageCount: project.pageCount,
    wordCount: project.wordCount,
    hasEmbeddings: project.embeddings.length > 0,
    createdAt: project.createdAt,
   },
  });
 } catch (error) {
  console.error("Upload error:", error.message);
  if (req.file && req.file.path) {
   fs.unlink(req.file.path, () => {});
  }
  res.status(500).json({ error: error.message });
 }
});

// ===========================================================================
// GET /api/projects — List all projects
// ===========================================================================
router.get("/", async (req, res) => {
 try {
  const projects = await Project.find()
   .select("title filename pageCount wordCount createdAt embeddings")
   .sort({ createdAt: -1 });

  // Add hasEmbeddings flag without sending the full embedding array
  const result = projects.map((p) => ({
   _id: p._id,
   title: p.title,
   filename: p.filename,
   pageCount: p.pageCount,
   wordCount: p.wordCount,
   hasEmbeddings: p.embeddings && p.embeddings.length > 0,
   createdAt: p.createdAt,
  }));

  res.json(result);
 } catch (error) {
  console.error("List error:", error.message);
  res.status(500).json({ error: error.message });
 }
});

// ===========================================================================
// POST /api/projects/:id/compare — Run plagiarism check against all others
// ===========================================================================
router.post("/:id/compare", async (req, res) => {
 try {
  const projectId = req.params.id;

  // Fetch the source project
  const sourceProject = await Project.findById(projectId);
  if (!sourceProject) {
   return res.status(404).json({ error: "Project not found" });
  }

  // Fetch all other projects to compare against
  const otherProjects = await Project.find({ _id: { $ne: projectId } });
  if (otherProjects.length === 0) {
   return res.status(400).json({
    error: "No other projects to compare against. Upload more documents.",
   });
  }

  // Build compare_against array — include pre-computed embeddings if available
  const compareAgainst = otherProjects.map((p) => ({
   id: p._id.toString(),
   title: p.title,
   text: p.text,
   embedding: p.embeddings && p.embeddings.length > 0 ? p.embeddings : null,
  }));

  const useLayer4 = req.body?.use_layer4 !== false;

  console.log(
   `Calling FastAPI: project=${projectId} against ${compareAgainst.length} docs ` +
    `(${compareAgainst.filter((c) => c.embedding).length} with pre-computed embeddings)`,
  );

  const fastApiUrl = process.env.FASTAPI_URL || "http://localhost:8000";
  const response = await axios.post(
   `${fastApiUrl}/compare`,
   {
    project_id: projectId,
    project_text: sourceProject.text,
    compare_against: compareAgainst,
    use_layer4: useLayer4,
   },
   { headers: getMLHeaders(), timeout: 120000 },
  );

  const pipelineResult = response.data;

  // Save report to MongoDB
  const report = await Report.findOneAndUpdate(
   { projectId },
   {
    projectId,
    comparisons: pipelineResult.comparisons,
    highestRisk: pipelineResult.highest_risk,
    highestScore: pipelineResult.highest_score,
    totalComparisons: pipelineResult.total_comparisons,
   },
   { upsert: true, new: true },
  );

  console.log(
   `Report saved: project=${projectId} → ${report.highestRisk} (${report.highestScore})`,
  );

  res.json({
   message: "Plagiarism check complete",
   report: {
    id: report._id,
    projectId: report.projectId,
    highestRisk: report.highestRisk,
    highestScore: report.highestScore,
    totalComparisons: report.totalComparisons,
    comparisons: report.comparisons,
    createdAt: report.createdAt,
    updatedAt: report.updatedAt,
   },
  });
 } catch (error) {
  console.error("Compare error:", error.message);

  if (error.response) {
   return res.status(502).json({
    error: "ML engine error",
    detail: error.response.data?.detail || error.message,
   });
  }

  if (error.code === "ECONNREFUSED") {
   return res.status(503).json({
    error: "ML engine unavailable. Make sure FastAPI is running on port 8000.",
   });
  }

  res.status(500).json({ error: error.message });
 }
});

// ===========================================================================
// GET /api/projects/:id/report — Get plagiarism report for a project
// ===========================================================================
router.get("/:id/report", async (req, res) => {
 try {
  const report = await Report.findOne({ projectId: req.params.id });

  if (!report) {
   return res
    .status(404)
    .json({ error: "No report found. Run a plagiarism check first." });
  }

  res.json(report);
 } catch (error) {
  console.error("Report fetch error:", error.message);
  res.status(500).json({ error: error.message });
 }
});

module.exports = router;
