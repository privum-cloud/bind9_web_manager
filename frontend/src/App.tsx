import { Routes, Route } from 'react-router-dom'
import { Layout } from '@/components/layout/Layout'
import Login from '@/pages/Login'
import SSOCallback from '@/pages/SSOCallback'
import Dashboard from '@/pages/Dashboard'
import Zones from '@/pages/Zones'
import ZoneDetail from '@/pages/ZoneDetail'
import Users from '@/pages/Users'
import Audit from '@/pages/Audit'
import Backup from '@/pages/Backup'
import Settings from '@/pages/Settings'
import Profile from '@/pages/Profile'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/login/callback" element={<SSOCallback />} />

      <Route
        path="/"
        element={
          <Layout>
            <Dashboard />
          </Layout>
        }
      />

      <Route
        path="/zones"
        element={
          <Layout>
            <Zones />
          </Layout>
        }
      />

      <Route
        path="/zones/:zoneName"
        element={
          <Layout>
            <ZoneDetail />
          </Layout>
        }
      />

      <Route
        path="/users"
        element={
          <Layout>
            <Users />
          </Layout>
        }
      />

      <Route
        path="/audit"
        element={
          <Layout>
            <Audit />
          </Layout>
        }
      />

      <Route
        path="/backup"
        element={
          <Layout>
            <Backup />
          </Layout>
        }
      />

      <Route
        path="/settings"
        element={
          <Layout>
            <Settings />
          </Layout>
        }
      />

      <Route
        path="/profile"
        element={
          <Layout>
            <Profile />
          </Layout>
        }
      />
    </Routes>
  )
}
