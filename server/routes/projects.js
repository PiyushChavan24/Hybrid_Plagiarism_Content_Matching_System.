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
    // Clean up temp file
    fs.unlink(filePath, () => {});
    resolve(uploadStream.id);
   });
 });
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
   // Clean up temp file
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

  res.status(201).json({
   message: "Project uploaded successfully",
   project: {
    id: project._id,
    title: project.title,
    filename: project.filename,
    pageCount: project.pageCount,
    wordCount: project.wordCount,
    createdAt: project.createdAt,
   },
  });
 } catch (error) {
  console.error("Upload error:", error.message);
  // Clean up temp file on error
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
   .select("title filename pageCount wordCount createdAt")
   .sort({ createdAt: -1 });

  res.json(projects);
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

  // Build compare_against array for FastAPI
  const compareAgainst = otherProjects.map((p) => ({
   id: p._id.toString(),
   title: p.title,
   text: p.text,
  }));

  const useLayer4 = req.body?.use_layer4 !== false; // default true

  // Call FastAPI /compare endpoint
  console.log(
   `Calling FastAPI: project=${projectId} against ${compareAgainst.length} docs`,
  );

  const fastApiUrl = process.env.FASTAPI_URL || "http://localhost:8000";
  const response = await axios.post(`${fastApiUrl}/compare`, {
   project_id: projectId,
   project_text: sourceProject.text,
   compare_against: compareAgainst,
   use_layer4: useLayer4,
  });

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
   // FastAPI returned an error
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
