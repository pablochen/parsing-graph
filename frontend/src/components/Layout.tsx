import { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { 
  FileText, 
  Upload, 
  Activity, 
  Home,
  Menu,
  X
} from 'lucide-react'
import { useState } from 'react'

interface LayoutProps {
  children: ReactNode
}

const Layout = ({ children }: LayoutProps) => {
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const navigation = [
    { name: '대시보드', href: '/', icon: Home },
    { name: '문서 관리', href: '/documents', icon: FileText },
    { name: '시스템 상태', href: '/system', icon: Activity },
  ]

  const isActive = (href: string) => {
    return location.pathname === href
  }

  return (
    <div className="h-screen flex overflow-hidden bg-gray-50">
      {/* 모바일 사이드바 오버레이 */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 z-40 bg-gray-600 bg-opacity-75 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* 사이드바 - 고정 너비, 전체 높이 */}
      <div className={`
        fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg transform transition-transform duration-300 ease-in-out 
        lg:relative lg:translate-x-0 lg:flex lg:flex-col lg:w-64 lg:flex-shrink-0
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        {/* 사이드바 헤더 */}
        <div className="flex items-center justify-between h-16 px-6 bg-white border-b border-gray-200 flex-shrink-0">
          <div className="flex items-center">
            <Upload className="h-8 w-8 text-blue-600" />
            <span className="ml-2 text-lg font-semibold text-gray-900">
              PDF 파싱
            </span>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-1 rounded-md hover:bg-gray-100"
          >
            <X className="h-5 w-5 text-gray-500" />
          </button>
        </div>

        {/* 네비게이션 메뉴 - 스크롤 가능 */}
        <nav className="flex-1 overflow-y-auto px-4 py-6">
          <div className="space-y-2">
            {navigation.map((item) => {
              const Icon = item.icon
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`
                    flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors duration-200
                    ${isActive(item.href)
                      ? 'bg-blue-100 text-blue-700 border-r-4 border-blue-600'
                      : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                    }
                  `}
                  onClick={() => setSidebarOpen(false)}
                >
                  <Icon className="mr-3 h-5 w-5 flex-shrink-0" />
                  {item.name}
                </Link>
              )
            })}
          </div>
        </nav>

        {/* 사이드바 하단 정보 */}
        <div className="flex-shrink-0 border-t border-gray-200 p-4 bg-gray-50">
          <div className="text-xs text-gray-500 space-y-1">
            <div className="font-medium">보험약관 PDF 파싱 시스템</div>
            <div>LangGraph + GPT-5</div>
            <div>v0.1.0</div>
          </div>
        </div>
      </div>

      {/* 메인 콘텐츠 영역 - 사이드바 옆에 배치 */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* 상단 헤더 - 고정 */}
        <header className="flex-shrink-0 bg-white shadow-sm border-b border-gray-200">
          <div className="flex h-16 items-center justify-between px-4 sm:px-6">
            <div className="flex items-center">
              <button
                onClick={() => setSidebarOpen(true)}
                className="lg:hidden p-2 rounded-md hover:bg-gray-100"
              >
                <Menu className="h-5 w-5 text-gray-500" />
              </button>
              
              <div className="ml-4 lg:ml-0">
                <h1 className="text-xl font-semibold text-gray-900">
                  {getPageTitle(location.pathname)}
                </h1>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              {/* 상태 표시기 */}
              <div className="flex items-center space-x-2">
                <div className="h-2 w-2 bg-green-400 rounded-full"></div>
                <span className="text-sm text-gray-500">시스템 정상</span>
              </div>
            </div>
          </div>
        </header>

        {/* 페이지 콘텐츠 - 스크롤 가능 */}
        <main className="flex-1 overflow-auto bg-gray-50">
          <div className="p-4 sm:p-6 lg:p-8 h-full">
            <div className="max-w-7xl mx-auto h-full">
              {children}
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

function getPageTitle(pathname: string): string {
  const titles: Record<string, string> = {
    '/': '대시보드',
    '/documents': '문서 관리',
    '/system': '시스템 상태',
  }

  // 동적 경로 처리
  if (pathname.startsWith('/documents/')) {
    return '문서 상세'
  }
  if (pathname.startsWith('/parse/')) {
    return '파싱 결과'
  }

  return titles[pathname] || '페이지'
}

export default Layout