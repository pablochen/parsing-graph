import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import DocumentList from './pages/DocumentList'
import DocumentDetail from './pages/DocumentDetail'
import ParseResult from './pages/ParseResult'
import SystemStatus from './pages/SystemStatus'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/documents" element={<DocumentList />} />
        <Route path="/documents/:docId" element={<DocumentDetail />} />
        <Route path="/parse/:docId" element={<ParseResult />} />
        <Route path="/system" element={<SystemStatus />} />
      </Routes>
    </Layout>
  )
}

export default App