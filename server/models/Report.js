/** @format */

const mongoose = require("mongoose");

const ComparisonSchema = new mongoose.Schema(
 {
  suspect_id: String,
  suspect_title: String,
  scores: {
   s_lex: Number,
   s_sem: Number,
   s_sty: Number,
   c_final: Number,
  },
  threshold: {
   t_cal: Number,
   t_base: Number,
   factors: {
    f_len: Number,
    f_vocab: Number,
    f_topic: Number,
   },
  },
  risk: {
   level: { type: String, enum: ["HIGH", "MEDIUM", "LOW"] },
   confidence: String,
  },
  snippets: [
   {
    source_sentence: String,
    suspect_sentence: String,
    similarity: Number,
    source_index: Number,
    suspect_index: Number,
   },
  ],
  metadata: {
   elapsed_seconds: Number,
   snippet_count: Number,
   source_sentences: Number,
   suspect_sentences: Number,
   source_tokens: Number,
   suspect_tokens: Number,
  },
 },
 { _id: false },
);

const ReportSchema = new mongoose.Schema(
 {
  projectId: {
   type: mongoose.Schema.Types.ObjectId,
   ref: "Project",
   required: true,
  },
  comparisons: [ComparisonSchema],
  highestRisk: {
   type: String,
   enum: ["HIGH", "MEDIUM", "LOW"],
   default: "LOW",
  },
  highestScore: {
   type: Number,
   default: 0,
  },
  totalComparisons: {
   type: Number,
   default: 0,
  },
 },
 { timestamps: true },
);

module.exports = mongoose.model("Report", ReportSchema);
