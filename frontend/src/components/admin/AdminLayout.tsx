import React from 'react';

interface AdminLayoutProps {
  children: React.ReactNode;
  maxWidth?: 'standard' | 'wide' | 'full';
}

/**
 * 관리자 페이지를 위한 표준화된 레이아웃 컴포넌트
 * 모든 관리 섹션에서 일관된 폭과 spacing을 제공합니다.
 */
const AdminLayout: React.FC<AdminLayoutProps> = ({ 
  children, 
  maxWidth = 'standard' 
}) => {
  const getMaxWidthClass = () => {
    switch (maxWidth) {
      case 'standard':
        return 'max-w-4xl'; // 사용자 관리, 기능 관리와 동일한 폭
      case 'wide':
        return 'max-w-6xl'; // 중간 폭
      case 'full':
        return 'max-w-7xl'; // 전체 폭 (기존 대시보드와 동일)
      default:
        return 'max-w-4xl';
    }
  };

  return (
    <div className={`${getMaxWidthClass()} mx-auto px-4 sm:px-6 lg:px-8 py-6`}>
      {children}
    </div>
  );
};

export default AdminLayout;