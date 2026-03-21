/** @format */

const mongoose = require("mongoose");

const ProjectSchema = new mongoose.Schema(
 {
  title: {
   type: String,
   required: true,
   trim: true,
  },
  text: {
   type: String,
   required: true,
  },
  filename: {
   type: String,
   required: true,
  },
  fileId: {
   type: mongoose.Schema.Types.ObjectId,
   ref: "uploads.files",
  },
  pageCount: {
   type: Number,
   default: 0,
  },
  wordCount: {
   type: Number,
   default: 0,
  },
 },
 { timestamps: true },
);

module.exports = mongoose.model("Project", ProjectSchema);
