/** @format */

import axios from "axios";

const API = axios.create({
 baseURL: import.meta.env.PROD
  ? "https://hpcm-backend.onrender.com/api"
  : "http://localhost:5011/api",
});

export default API;
