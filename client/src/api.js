/** @format */

import axios from "axios";

const API = axios.create({
 baseURL: "http://localhost:5011/api",
});

export default API;
