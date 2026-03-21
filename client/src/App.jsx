/** @format */

import React from "react";
import {
 BrowserRouter as Router,
 Routes,
 Route,
 Link,
 useLocation,
} from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Upload from "./pages/Upload";
import Report from "./pages/Report";
import "./App.css";

function NavBar() {
 const location = useLocation();
 const isActive = (path) =>
  location.pathname === path ? "nav-link active" : "nav-link";

 return (
  <nav className="navbar">
   <Link to="/" className="nav-brand">
    <span className="brand-icon">◆</span>
    <span className="brand-text">HPCM</span>
    <span className="brand-sub">Plagiarism Engine</span>
   </Link>
   <div className="nav-links">
    <Link to="/" className={isActive("/")}>
     Dashboard
    </Link>
    <Link to="/upload" className={isActive("/upload")}>
     Upload
    </Link>
   </div>
  </nav>
 );
}

function App() {
 return (
  <Router>
   <div className="app">
    <NavBar />
    <main className="main-content">
     <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/upload" element={<Upload />} />
      <Route path="/report/:id" element={<Report />} />
     </Routes>
    </main>
   </div>
  </Router>
 );
}

export default App;
