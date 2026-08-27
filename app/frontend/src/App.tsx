import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import { SessionProvider } from '@/hooks/useSession';
import AuthCallback from './pages/AuthCallback';
import Index from './pages/Index';
import AccessLogs from './pages/AccessLogs';
import DailyAttendance from './pages/DailyAttendance';
import Approvals from './pages/Approvals';
import LeaveManagement from './pages/LeaveManagement';
import OvertimeBank from './pages/OvertimeBank';
import Payroll from './pages/Payroll';
import MasterSettings from './pages/MasterSettings';

export default function App() {
  return (
    <SessionProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/logs" element={<AccessLogs />} />
          <Route path="/daily" element={<DailyAttendance />} />
          <Route path="/approvals" element={<Approvals />} />
          <Route path="/leave" element={<LeaveManagement />} />
          <Route path="/overtime" element={<OvertimeBank />} />
          <Route path="/payroll" element={<Payroll />} />
          <Route path="/settings" element={<MasterSettings />} />
          <Route path="/auth/callback" element={<AuthCallback />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </SessionProvider>
  );
}