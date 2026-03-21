/** @format */

require("dotenv").config();
const express = require("express");
const cors = require("cors");
const connectDB = require("./config/db");
const projectRoutes = require("./routes/projects");

const app = express();
const PORT = process.env.PORT || 5000;

// ---------------------------------------------------------------------------
// Middleware
// ---------------------------------------------------------------------------
app.use(
 cors({
  origin: [
   "http://localhost:3000",
   "http://localhost:5173",
   "https://hpcm-plagiarism-detection.vercel.app", // add this
  ],
  credentials: true,
 }),
);
app.use(express.json({ limit: "10mb" }));

// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------
app.use("/api/projects", projectRoutes);

// Health check
app.get("/health", (req, res) => {
 res.json({
  status: "ok",
  service: "HPCM Node Backend",
  port: PORT,
 });
});

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------
connectDB().then(() => {
 app.listen(PORT, () => {
  console.log(`\n===========================================`);
  console.log(`  HPCM Node Backend running on port ${PORT}`);
  console.log(`  FastAPI URL: ${process.env.FASTAPI_URL}`);
  console.log(`  MongoDB: ${process.env.MONGO_URI}`);
  console.log(`===========================================\n`);
 });
});
