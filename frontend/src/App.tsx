import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider } from 'antd';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { ForgotPassword } from './pages/ForgotPassword';
import { Dashboard } from './pages/Dashboard';
import { Agents } from './pages/Agents';
import { AgentBuilder } from './pages/AgentBuilder';
import { AgentTest } from './pages/AgentTest';
import { Tools } from './pages/Tools';
import { Templates } from './pages/Templates';
import { Deployments } from './pages/Deployments';
import { Analytics } from './pages/Analytics';
import { Users } from './pages/Users';
import { MainLayout } from './components/Common/MainLayout';
import { ProtectedRoute } from './components/Common/ProtectedRoute';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider
        theme={{
          token: {
            colorPrimary: '#1890ff',
            borderRadius: 6,
          },
        }}
      >
        <BrowserRouter>
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />

            {/* Protected routes */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <MainLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="agents" element={<Agents />} />
              <Route path="agents/new" element={<AgentBuilder />} />
              <Route path="agents/:id/edit" element={<AgentBuilder />} />
              <Route path="agents/:id/test" element={<AgentTest />} />
              <Route path="tools" element={<Tools />} />
              <Route path="templates" element={<Templates />} />
              <Route path="deployments" element={<Deployments />} />
              <Route path="analytics" element={<Analytics />} />
              <Route path="users" element={<Users />} />
            </Route>

            {/* Catch all */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </ConfigProvider>
    </QueryClientProvider>
  );
}

export default App;
