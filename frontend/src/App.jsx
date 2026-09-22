import { NavLink, Route, Routes } from "react-router-dom";
import Demo from "./pages/Demo.jsx";
import Explorer from "./pages/Explorer.jsx";
import ImportWizard from "./pages/ImportWizard.jsx";
import Landing from "./pages/Landing.jsx";
import Workbench from "./pages/Workbench.jsx";
import "./App.css";

function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-title">TS Forecast Benchmark</div>
        <nav className="app-nav">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            Dashboard
          </NavLink>
          <NavLink to="/explorer" className={({ isActive }) => (isActive ? "active" : "")}>
            Explorer
          </NavLink>
          <NavLink to="/workbench" className={({ isActive }) => (isActive ? "active" : "")}>
            Workbench
          </NavLink>
          <NavLink to="/import" className={({ isActive }) => (isActive ? "active" : "")}>
            Import
          </NavLink>
        </nav>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/demo" element={<Demo />} />
          <Route path="/explorer" element={<Explorer />} />
          <Route path="/workbench" element={<Workbench />} />
          <Route path="/import" element={<ImportWizard />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
