import React, { useState, useEffect } from 'react'
import { X, Users, Search } from 'lucide-react'
import config from '../config/environment'

const GroupSelectionModal = ({ isOpen, onClose, onSelect }) => {
  const [groups, setGroups] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    if (isOpen) {
      fetchGroups()
    }
  }, [isOpen])

  const fetchGroups = async () => {
    setLoading(true)
    setError('')
    
    try {
      const response = await fetch(`/api/auth/available-groups`)
      if (response.ok) {
        const data = await response.json()
        setGroups(data)
      } else {
        setError('그룹 목록을 불러오지 못했습니다.')
      }
    } catch (err) {
      setError('서버 연결에 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const filteredGroups = groups.filter(group =>
    group.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (group.description && group.description.toLowerCase().includes(searchTerm.toLowerCase()))
  )

  const handleGroupSelect = (group) => {
    onSelect(group)
    onClose()
  }

  const handleSkip = () => {
    onSelect(null)
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full mx-4 max-h-[80vh] overflow-hidden">
        {/* 헤더 */}
        <div className="flex items-center justify-between p-6 border-b border-neutral-100">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-neutral-100 rounded-lg flex items-center justify-center">
              <Users className="w-4 h-4 text-neutral-600" />
            </div>
            <h2 className="text-lg font-semibold text-neutral-900">그룹 선택</h2>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 검색 */}
        <div className="p-4 border-b border-neutral-100">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-neutral-400 w-4 h-4" />
            <input
              type="text"
              placeholder="그룹 검색..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-neutral-200 rounded-lg focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
          </div>
        </div>

        {/* 콘텐츠 */}
        <div className="p-4">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
            </div>
          ) : error ? (
            <div className="text-center py-8">
              <p className="text-red-600 text-sm">{error}</p>
              <button
                onClick={fetchGroups}
                className="mt-2 text-neutral-600 hover:text-neutral-900 text-sm font-medium"
              >
                다시 시도
              </button>
            </div>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {/* 임시 그룹 옵션 */}
              <button
                onClick={() => handleGroupSelect({ id: 'temp', name: '임시', description: '그룹을 모르는 경우 선택 (관리자가 나중에 배정)' })}
                className="w-full text-left p-3 rounded-lg border border-orange-200 bg-orange-50 hover:bg-orange-100 transition-colors"
              >
                <div className="font-medium text-orange-900">임시</div>
                <div className="text-sm text-orange-700 mt-1">
                  그룹을 모르는 경우 선택하세요. 관리자가 나중에 적절한 그룹으로 배정해드립니다.
                </div>
              </button>

              {/* 그룹 목록 */}
              {filteredGroups.map((group) => (
                <button
                  key={group.id}
                  onClick={() => handleGroupSelect(group)}
                  className="w-full text-left p-3 rounded-lg border border-neutral-200 hover:bg-neutral-50 hover:border-neutral-300 transition-colors"
                >
                  <div className="font-medium text-neutral-900">{group.name}</div>
                  {group.description && (
                    <div className="text-sm text-neutral-600 mt-1">{group.description}</div>
                  )}
                </button>
              ))}

              {filteredGroups.length === 0 && !loading && searchTerm && (
                <div className="text-center py-4 text-neutral-500 text-sm">
                  검색 결과가 없습니다
                </div>
              )}
            </div>
          )}
        </div>

        {/* 안내 메시지 */}
        <div className="px-4 pb-4">
          <div className="bg-neutral-50 rounded-lg p-3">
            <p className="text-xs text-neutral-600">
              그룹을 선택하면 해당 그룹의 권한과 기능을 사용할 수 있습니다.
              선택하지 않아도 회원가입이 가능합니다.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default GroupSelectionModal