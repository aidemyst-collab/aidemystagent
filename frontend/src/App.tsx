import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider, App as AntApp } from 'antd';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { ForgotPassword } from './pages/ForgotPassword';
import { Dashboard } from './pages/Dashboard';
import { Agents } from './pages/Agents';
import { WorkflowBuilder } from './pages/WorkflowBuilder';
import { AgentTest } from './pages/AgentTest';
import { Tools } from './pages/Tools';
import { MCPServers } from './pages/MCPServers';
import { DynamicMCPTools } from './pages/DynamicMCPTools';
import { HostedMCPServers } from './pages/HostedMCPServers';
import { Credentials } from './pages/Credentials';
import { Templates } from './pages/Templates';
import { Deployments } from './pages/Deployments';
import { Analytics } from './pages/Analytics';
import { Users } from './pages/Users';
import AdminDashboard from './pages/AdminDashboard';
import Invitations from './pages/Invitations';
import AuditLogs from './pages/AuditLogs';
import ExecutionLogs from './pages/ExecutionLogs';
import AcceptInvitation from './pages/AcceptInvitation';
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
            colorPrimary: '#6366f1',
            colorInfo: '#6366f1',
            borderRadius: 8,
            fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
          },
          components: {
            Button: {
              primaryShadow: '0 2px 8px rgba(99, 102, 241, 0.35)',
            },
          },
        }}
      >
        <AntApp>
          <BrowserRouter>
            <Routes>
              {/* Public routes */}
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
              <Route path="/invitations/accept/:token" element={<AcceptInvitation />} />

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
                <Route path="agents/new" element={<WorkflowBuilder />} />
                <Route path="agents/:id/edit" element={<WorkflowBuilder />} />
                <Route path="agents/:id/test" element={<AgentTest />} />
                <Route path="tools" element={<Tools />} />
                <Route path="mcp-servers" element={<MCPServers />} />
                <Route path="mcp-tools" element={<DynamicMCPTools />} />
                <Route path="hosted-mcp-servers" element={<HostedMCPServers />} />
                <Route path="credentials" element={<Credentials />} />
                <Route path="templates" element={<Templates />} />
                <Route path="deployments" element={<Deployments />} />
                <Route path="analytics" element={<Analytics />} />
                <Route path="users" element={<Users />} />
                <Route path="users/create" element={<Register />} />
                <Route path="invitations" element={<Invitations />} />
                <Route path="audit-logs" element={<AuditLogs />} />
                <Route path="execution-logs" element={<ExecutionLogs />} />
                <Route path="admin" element={<AdminDashboard />} />
              </Route>

              {/* Catch all */}
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </BrowserRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>
  );
}

export default App;
