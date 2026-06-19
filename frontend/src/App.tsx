import { Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/AppLayout';
import PlanPage from './pages/PlanPage';
import VesselPage from './pages/VesselPage';
import CertificatePage from './pages/CertificatePage';
import PermitPage from './pages/PermitPage';

const App: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<AppLayout />}>
        <Route index element={<Navigate to="/plans" replace />} />
        <Route path="plans" element={<PlanPage />} />
        <Route path="vessels" element={<VesselPage />} />
        <Route path="certificates" element={<CertificatePage />} />
        <Route path="permits" element={<PermitPage />} />
      </Route>
    </Routes>
  );
};

export default App;
