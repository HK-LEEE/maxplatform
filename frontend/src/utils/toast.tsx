import React from 'react';
import toast, { Toast } from 'react-hot-toast';
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react';

interface CustomToastProps {
  t: Toast;
  message: string;
  type: 'success' | 'error' | 'info' | 'warning';
}

const CustomToast: React.FC<CustomToastProps> = ({ t, message, type }) => {
  const handleDismiss = () => {
    toast.dismiss(t.id);
  };

  const getIcon = () => {
    switch (type) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
      default:
        return <Info className="w-5 h-5 text-blue-500" />;
    }
  };

  const getBackgroundColor = () => {
    switch (type) {
      case 'success':
        return 'bg-green-50 border-green-200';
      case 'error':
        return 'bg-red-50 border-red-200';
      case 'warning':
        return 'bg-yellow-50 border-yellow-200';
      default:
        return 'bg-blue-50 border-blue-200';
    }
  };

  const getTextColor = () => {
    switch (type) {
      case 'success':
        return 'text-green-800';
      case 'error':
        return 'text-red-800';
      case 'warning':
        return 'text-yellow-800';
      default:
        return 'text-blue-800';
    }
  };

  return (
    <div
      className={`
        ${t.visible ? 'animate-toast-enter' : 'animate-toast-leave'}
        max-w-md w-full ${getBackgroundColor()} shadow-lg rounded-lg pointer-events-auto 
        flex ring-1 ring-black ring-opacity-5 border transition-all duration-300 ease-in-out
        toast-container
      `}
    >
      <div className="flex-1 w-0 p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            {getIcon()}
          </div>
          <div className="ml-3 flex-1">
            <p className={`text-sm font-medium ${getTextColor()}`}>
              {message}
            </p>
          </div>
        </div>
      </div>
      <div className="flex border-l border-gray-200">
        <button
          onClick={handleDismiss}
          className={`
            w-full border border-transparent rounded-none rounded-r-lg p-4 
            flex items-center justify-center text-sm font-medium 
            ${getTextColor()} hover:bg-gray-100 focus:outline-none 
            focus:ring-2 focus:ring-indigo-500 transition-colors duration-200
          `}
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

// 전역 Toast 함수들
export const showToast = {
  success: (message: string, options?: { duration?: number }) => {
    toast.custom((t) => (
      <CustomToast t={t} message={message} type="success" />
    ), {
      duration: options?.duration || 3000,
      position: 'top-right',
    });
  },

  error: (message: string, options?: { duration?: number }) => {
    toast.custom((t) => (
      <CustomToast t={t} message={message} type="error" />
    ), {
      duration: options?.duration || 5000,
      position: 'top-right',
    });
  },

  warning: (message: string, options?: { duration?: number }) => {
    toast.custom((t) => (
      <CustomToast t={t} message={message} type="warning" />
    ), {
      duration: options?.duration || 4000,
      position: 'top-right',
    });
  },

  info: (message: string, options?: { duration?: number }) => {
    toast.custom((t) => (
      <CustomToast t={t} message={message} type="info" />
    ), {
      duration: options?.duration || 3000,
      position: 'top-right',
    });
  },

  // 로딩 Toast
  loading: (message: string) => {
    return toast.loading(message, {
      position: 'top-right',
      style: {
        background: '#eff6ff',
        color: '#1e40af',
        border: '1px solid #bfdbfe',
        borderRadius: '8px',
        padding: '16px',
        fontSize: '14px',
        maxWidth: '400px',
      },
    });
  },

  // 로딩 Toast 업데이트
  updateLoading: (toastId: string, message: string, type: 'success' | 'error') => {
    if (type === 'success') {
      toast.success(message, { id: toastId });
    } else {
      toast.error(message, { id: toastId });
    }
  },

  // 모든 Toast 닫기
  dismissAll: () => {
    toast.dismiss();
  }
};

export default showToast; 