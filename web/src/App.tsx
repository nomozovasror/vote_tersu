import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import EventManage from './pages/EventManage';
import CandidatesManage from './pages/CandidatesManage';
import VotePage from './pages/VotePage';
import DisplayPage from './pages/DisplayPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/admin/login" />} />
        <Route path="/admin/login" element={<Login />} />
        <Route path="/admin/dashboard" element={<Dashboard />} />
        <Route path="/admin/candidates" element={<CandidatesManage />} />
        <Route path="/admin/event/:id" element={<EventManage />} />
        <Route path="/vote/:link" element={<VotePage />} />
        <Route path="/display/:link" element={<DisplayPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
