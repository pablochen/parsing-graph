import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from 'react-query'
import { 
  Upload, 
  FileText, 
  Activity, 
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Plus,
  FolderOpen,
  Zap,
  Download,
  BarChart3
} from 'lucide-react'
import { apiClient, getJobStatusText } from '../lib/api'

const Dashboard = () => {
  const [stats, setStats] = useState({
    totalDocuments: 0,
    completedParsing: 0,
    failedParsing: 0,
    runningJobs: 0
  })

  // 시스템 정보 조회
  const { data: systemInfo } = useQuery(
    'system-info',
    () => apiClient.getSystemInfo(),
    {
      refetchInterval: 30000, // 30초마다 갱신
    }
  )

  // 활성 작업 조회
  const { data: activeJobs, isLoading: jobsLoading } = useQuery(
    'active-jobs',
    () => apiClient.getActiveJobs(),
    {
      refetchInterval: 5000, // 5초마다 갱신
    }
  )

  // 문서 목록 조회 (통계용)
  const { data: documents } = useQuery(
    'documents-stats',
    () => apiClient.getDocuments(0, 1000),
    {
      refetchInterval: 30000,
    }
  )

  useEffect(() => {
    if (documents) {
      const total = documents.total
      const completed = documents.documents.filter((doc: any) => doc.status === 'parsed').length
      const failed = total - completed
      
      setStats({
        totalDocuments: total,
        completedParsing: completed,
        failedParsing: failed,
        runningJobs: activeJobs?.running || 0
      })
    }
  }, [documents, activeJobs])

  const statCards = [
    {
      title: '전체 문서',
      value: stats.totalDocuments,
      icon: FileText,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
      borderColor: 'border-blue-200'
    },
    {
      title: '파싱 완료',
      value: stats.completedParsing,
      icon: CheckCircle,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
      borderColor: 'border-green-200'
    },
    {
      title: '파싱 실패',
      value: stats.failedParsing,
      icon: XCircle,
      color: 'text-red-600',
      bgColor: 'bg-red-100',
      borderColor: 'border-red-200'
    },
    {
      title: '실행 중',
      value: stats.runningJobs,
      icon: Clock,
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-100',
      borderColor: 'border-yellow-200'
    }
  ]

  return (
    <div className="space-y-8">
      {/* 헤더 섹션 */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center">
            <BarChart3 className="h-8 w-8 text-blue-600 mr-3" />
            대시보드
          </h1>
          <p className="text-gray-600 mt-2 text-lg">
            보험약관 PDF 파싱 시스템 현황을 확인하세요
          </p>
        </div>
        
        {/* 예쁜 액션 버튼들 */}
        <div className="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-3">
          <Link
            to="/documents"
            className="group relative overflow-hidden rounded-xl bg-gradient-to-r from-gray-50 to-gray-100 px-6 py-4 font-medium text-gray-700 shadow-lg transition-all duration-300 hover:from-gray-100 hover:to-gray-200 hover:shadow-xl hover:-translate-y-1 border border-gray-200"
          >
            <div className="flex items-center justify-center">
              <FolderOpen className="h-5 w-5 mr-2 group-hover:scale-110 transition-transform duration-300" />
              <span className="text-sm font-semibold">문서 관리</span>
            </div>
            <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 to-purple-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
          </Link>
          
          <button className="group relative overflow-hidden rounded-xl bg-gradient-to-r from-blue-500 to-blue-600 px-6 py-4 font-medium text-white shadow-lg transition-all duration-300 hover:from-blue-600 hover:to-blue-700 hover:shadow-xl hover:-translate-y-1">
            <div className="flex items-center justify-center">
              <Plus className="h-5 w-5 mr-2 group-hover:rotate-90 transition-transform duration-300" />
              <span className="text-sm font-semibold">문서 업로드</span>
            </div>
            <div className="absolute inset-0 bg-gradient-to-r from-white/20 to-white/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
          </button>
        </div>
      </div>

      {/* 통계 카드 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat, index) => {
          const Icon = stat.icon
          return (
            <div key={index} className={`relative overflow-hidden rounded-xl bg-white p-6 shadow-lg border ${stat.borderColor} transition-all duration-300 hover:shadow-xl hover:-translate-y-1`}>
              <div className="flex items-center">
                <div className={`p-4 rounded-xl ${stat.bgColor} ${stat.borderColor} border`}>
                  <Icon className={`h-6 w-6 ${stat.color}`} />
                </div>
                <div className="ml-4 flex-1">
                  <p className="text-sm font-medium text-gray-600 uppercase tracking-wide">{stat.title}</p>
                  <p className="text-3xl font-bold text-gray-900 mt-1">{stat.value}</p>
                </div>
              </div>
              <div className={`absolute bottom-0 left-0 right-0 h-1 ${stat.bgColor}`}></div>
            </div>
          )
        })}
      </div>

      {/* 메인 콘텐츠 그리드 */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
        {/* 실행 중인 작업 */}
        <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                <Activity className="h-5 w-5 text-blue-600 mr-2" />
                실행 중인 작업
              </h3>
              <div className="flex items-center space-x-2">
                <div className="h-2 w-2 bg-green-400 rounded-full animate-pulse"></div>
                <span className="text-sm text-gray-600">실시간</span>
              </div>
            </div>
          </div>

          <div className="p-6">
            {jobsLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                  <span className="text-gray-500 font-medium">로딩 중...</span>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {activeJobs?.active_jobs && Object.keys(activeJobs.active_jobs).length > 0 ? (
                  Object.entries(activeJobs.active_jobs).map(([docId, job]: [string, any]) => (
                    <div key={docId} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200 hover:bg-gray-100 transition-colors duration-200">
                      <div className="flex items-center space-x-3">
                        <div className="p-2 bg-blue-100 rounded-lg">
                          <FileText className="h-4 w-4 text-blue-600" />
                        </div>
                        <div>
                          <p className="font-semibold text-gray-900">{docId}</p>
                          <p className="text-sm text-gray-600">
                            {getJobStatusText(job.status)}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-3">
                        {job.status === 'running' && (
                          <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                        )}
                        <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
                          job.status === 'completed' ? 'bg-green-100 text-green-800' :
                          job.status === 'failed' ? 'bg-red-100 text-red-800' :
                          job.status === 'running' ? 'bg-blue-100 text-blue-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {getJobStatusText(job.status)}
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-12">
                    <Activity className="h-12 w-12 text-gray-300 mx-auto mb-3" />
                    <p className="text-gray-500 font-medium">현재 실행 중인 작업이 없습니다</p>
                    <p className="text-gray-400 text-sm mt-1">새 문서를 업로드하여 파싱을 시작하세요</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* 시스템 상태 */}
        <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
          <div className="bg-gradient-to-r from-green-50 to-emerald-50 px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                <Zap className="h-5 w-5 text-green-600 mr-2" />
                시스템 상태
              </h3>
              <Link 
                to="/system" 
                className="text-green-600 hover:text-green-700 transition-colors duration-200"
              >
                <Activity className="h-5 w-5" />
              </Link>
            </div>
          </div>

          <div className="p-6">
            <div className="space-y-4">
              {systemInfo ? (
                <>
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <span className="text-gray-700 font-medium">환경</span>
                    <span className="font-semibold text-gray-900 bg-blue-100 px-3 py-1 rounded-full text-sm">
                      {systemInfo.environment}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <span className="text-gray-700 font-medium">AI 모델</span>
                    <span className="font-semibold text-gray-900 bg-purple-100 px-3 py-1 rounded-full text-sm">
                      GPT-5-mini
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <span className="text-gray-700 font-medium">MCP 서버</span>
                    <div className="flex items-center space-x-2">
                      <div className="h-2 w-2 bg-green-400 rounded-full animate-pulse"></div>
                      <span className="text-sm font-medium text-green-700">연결됨</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <span className="text-gray-700 font-medium">LangGraph</span>
                    <div className="flex items-center space-x-2">
                      <div className="h-2 w-2 bg-green-400 rounded-full animate-pulse"></div>
                      <span className="text-sm font-medium text-green-700">준비됨</span>
                    </div>
                  </div>
                </>
              ) : (
                <div className="flex items-center justify-center py-12">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 border-4 border-green-500 border-t-transparent rounded-full animate-spin"></div>
                    <span className="text-gray-500 font-medium">시스템 정보 로딩 중...</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 빠른 시작 가이드 */}
      <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
        <div className="bg-gradient-to-r from-purple-50 to-pink-50 px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center">
            <Zap className="h-5 w-5 text-purple-600 mr-2" />
            빠른 시작 가이드
          </h3>
        </div>
        
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="group text-center p-6 border border-gray-200 rounded-xl hover:border-blue-300 hover:shadow-lg transition-all duration-300 hover:-translate-y-1">
              <div className="relative">
                <div className="mx-auto w-16 h-16 bg-gradient-to-r from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                  <Upload className="h-8 w-8 text-white" />
                </div>
                <div className="absolute -top-1 -right-1 w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-xs font-bold">1</span>
                </div>
              </div>
              <h4 className="font-semibold text-gray-900 mt-4 mb-2">문서 업로드</h4>
              <p className="text-sm text-gray-600">보험약관 PDF 파일을 드래그 앤 드롭으로 간편 업로드</p>
            </div>

            <div className="group text-center p-6 border border-gray-200 rounded-xl hover:border-purple-300 hover:shadow-lg transition-all duration-300 hover:-translate-y-1">
              <div className="relative">
                <div className="mx-auto w-16 h-16 bg-gradient-to-r from-purple-500 to-purple-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                  <Activity className="h-8 w-8 text-white" />
                </div>
                <div className="absolute -top-1 -right-1 w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-xs font-bold">2</span>
                </div>
              </div>
              <h4 className="font-semibold text-gray-900 mt-4 mb-2">AI 파싱 실행</h4>
              <p className="text-sm text-gray-600">LangGraph + GPT-5로 목차와 본문을 자동 분석</p>
            </div>

            <div className="group text-center p-6 border border-gray-200 rounded-xl hover:border-green-300 hover:shadow-lg transition-all duration-300 hover:-translate-y-1">
              <div className="relative">
                <div className="mx-auto w-16 h-16 bg-gradient-to-r from-green-500 to-green-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                  <Download className="h-8 w-8 text-white" />
                </div>
                <div className="absolute -top-1 -right-1 w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-xs font-bold">3</span>
                </div>
              </div>
              <h4 className="font-semibold text-gray-900 mt-4 mb-2">결과 확인</h4>
              <p className="text-sm text-gray-600">구조화된 데이터와 CSV 파일을 다운로드</p>
            </div>
          </div>
        </div>
      </div>

      {/* 최근 활동 */}
      <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
        <div className="bg-gradient-to-r from-indigo-50 to-blue-50 px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center">
            <Clock className="h-5 w-5 text-indigo-600 mr-2" />
            최근 활동
          </h3>
        </div>
        
        <div className="p-6">
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-200">
              <div className="flex items-center space-x-3">
                <CheckCircle className="h-5 w-5 text-green-600" />
                <span className="text-sm text-gray-700">시스템이 정상적으로 시작되었습니다</span>
              </div>
              <span className="text-xs text-gray-500">방금 전</span>
            </div>
            
            <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-200">
              <div className="flex items-center space-x-3">
                <Zap className="h-5 w-5 text-blue-600" />
                <span className="text-sm text-gray-700">OpenRouter GPT-5 연결 완료</span>
              </div>
              <span className="text-xs text-gray-500">1분 전</span>
            </div>
            
            <div className="flex items-center justify-between p-3 bg-purple-50 rounded-lg border border-purple-200">
              <div className="flex items-center space-x-3">
                <Activity className="h-5 w-5 text-purple-600" />
                <span className="text-sm text-gray-700">LangGraph 파이프라인 준비 완료</span>
              </div>
              <span className="text-xs text-gray-500">2분 전</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard