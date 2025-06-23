import React from 'react';

interface FeatureLogoProps {
  displayName: string;
  size?: 'small' | 'medium' | 'large';
  className?: string;
}

const FeatureLogo: React.FC<FeatureLogoProps> = ({ 
  displayName, 
  size = 'medium', 
  className = '' 
}) => {
  // 영어 단어의 첫 글자들을 추출하여 약어 생성
  const generateAbbreviation = (name: string): string => {
    // 공백이나 특수문자로 단어 분리
    const words = name
      .split(/[\s\-_\.]+/)
      .filter(word => word.length > 0);
    
    let abbreviation = '';
    
    // 영어 단어들의 첫 글자만 추출
    for (const word of words) {
      const firstChar = word.charAt(0).toUpperCase();
      // 영어 알파벳인지 확인
      if (/[A-Z]/.test(firstChar)) {
        abbreviation += firstChar;
        // 최대 3글자까지만
        if (abbreviation.length >= 3) break;
      }
    }
    
    // 약어가 없으면 첫 번째 영어 문자 사용
    if (abbreviation.length === 0) {
      for (const char of name) {
        if (/[A-Za-z]/.test(char)) {
          abbreviation = char.toUpperCase();
          break;
        }
      }
    }
    
    // 여전히 없으면 기본값
    return abbreviation || 'F';
  };

  const abbreviation = generateAbbreviation(displayName);

  // 크기별 스타일 설정 - 2025 트렌드 반영
  const sizeStyles = {
    small: {
      container: 'w-10 h-10',
      text: 'text-sm',
      borderRadius: 'rounded-2xl'
    },
    medium: {
      container: 'w-12 h-12',
      text: 'text-base',
      borderRadius: 'rounded-2xl'
    },
    large: {
      container: 'w-16 h-16',
      text: 'text-xl',
      borderRadius: 'rounded-3xl'
    }
  };

  const currentSize = sizeStyles[size];

  return (
    <div className={`${className}`}>
      {/* 메인 로고 - 2025 모던 디자인 */}
      <div className={`
        ${currentSize.container}
        ${currentSize.borderRadius}
        bg-gradient-to-br from-slate-800 via-slate-900 to-slate-950
        flex items-center justify-center
        shadow-lg shadow-slate-900/25
        border border-slate-700/50
        backdrop-blur-sm
        transition-all duration-300 ease-out
        hover:shadow-xl hover:shadow-slate-900/40
        hover:scale-105
        hover:border-slate-600/60
        relative
        overflow-hidden
        group
      `}>
        {/* 내부 글로우 효과 */}
        <div className="absolute inset-0 bg-gradient-to-br from-white/5 via-transparent to-transparent opacity-60 group-hover:opacity-80 transition-opacity duration-300" />
        
        {/* 텍스트 */}
        <span className={`
          ${currentSize.text}
          font-bold
          text-white
          tracking-tight
          relative z-10
          drop-shadow-sm
          select-none
          font-inter
        `}
        style={{
          fontFamily: '"Inter", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          fontWeight: '700',
          letterSpacing: '-0.025em'
        }}>
          {abbreviation}
        </span>
        
        {/* 미묘한 하이라이트 */}
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />
      </div>
    </div>
  );
};

export default FeatureLogo; 