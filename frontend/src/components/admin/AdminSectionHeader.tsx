import React from 'react';
import { LucideIcon } from 'lucide-react';

interface AdminSectionHeaderProps {
  title: string;
  description?: string;
  icon?: LucideIcon;
  actions?: React.ReactNode;
  searchable?: boolean;
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
  searchPlaceholder?: string;
}

/**
 * 관리자 섹션 헤더 컴포넌트
 * 일관된 제목, 설명, 검색 및 액션 버튼 레이아웃을 제공합니다.
 */
const AdminSectionHeader: React.FC<AdminSectionHeaderProps> = ({
  title,
  description,
  icon: Icon,
  actions,
  searchable = false,
  searchQuery = '',
  onSearchChange,
  searchPlaceholder = '검색...'
}) => {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
        <div className="flex items-center space-x-3">
          {Icon && (
            <div className="p-2 bg-blue-50 rounded-lg">
              <Icon className="h-6 w-6 text-blue-600" />
            </div>
          )}
          <div>
            <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
            {description && (
              <p className="text-sm text-gray-600 mt-1">{description}</p>
            )}
          </div>
        </div>
        
        <div className="flex items-center space-x-3">
          {searchable && (
            <div className="relative">
              <input
                type="text"
                placeholder={searchPlaceholder}
                value={searchQuery}
                onChange={(e) => onSearchChange?.(e.target.value)}
                className="w-64 pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
            </div>
          )}
          {actions}
        </div>
      </div>
    </div>
  );
};

export default AdminSectionHeader;