/**
 * User Switch Security Modal
 * Displays security warnings and handles cleanup when user switches are detected
 */

import React, { useState, useEffect } from 'react';
import { Alert, Button, Modal, Progress, List, Typography, Space, Icon } from 'antd';
import { ExclamationCircleOutlined, SafetyCertificateOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons';
import { userSwitchSecurity, UserSwitchCleanupOptions } from '../utils/userSwitchSecurity';

const { Title, Text, Paragraph } = Typography;

interface UserSwitchSecurityModalProps {
  visible: boolean;
  onClose: () => void;
  newUserId: string;
  newUserEmail?: string;
  onCleanupComplete?: (success: boolean) => void;
  autoCleanup?: boolean;
}

interface SecurityDetectionResult {
  isUserSwitch: boolean;
  previousUserId: string | null;
  riskLevel: 'low' | 'medium' | 'high';
  recommendations: string[];
}

export const UserSwitchSecurityModal: React.FC<UserSwitchSecurityModalProps> = ({
  visible,
  onClose,
  newUserId,
  newUserEmail,
  onCleanupComplete,
  autoCleanup = false
}) => {
  const [detection, setDetection] = useState<SecurityDetectionResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [cleanupProgress, setCleanupProgress] = useState(0);
  const [cleanupStatus, setCleanupStatus] = useState<'idle' | 'running' | 'completed' | 'error'>('idle');
  const [cleanupResult, setCleanupResult] = useState<any>(null);

  useEffect(() => {
    if (visible && newUserId) {
      const result = userSwitchSecurity.detectUserSwitch(newUserId);
      setDetection(result);
      
      if (autoCleanup && result.isUserSwitch) {
        handleCleanup();
      }
    }
  }, [visible, newUserId, autoCleanup]);

  const handleCleanup = async () => {
    if (!detection?.isUserSwitch) return;

    setIsLoading(true);
    setCleanupStatus('running');
    setCleanupProgress(0);

    try {
      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setCleanupProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 15;
        });
      }, 300);

      const options: UserSwitchCleanupOptions = {
        preserveTheme: true,
        preserveLanguage: true,
        clearCookies: detection.riskLevel === 'high',
        clearIndexedDB: detection.riskLevel !== 'low',
        reloadPage: false,
        debugMode: process.env.NODE_ENV === 'development'
      };

      const result = await userSwitchSecurity.performSecurityCleanup(options);
      
      clearInterval(progressInterval);
      setCleanupProgress(100);
      setCleanupResult(result);
      setCleanupStatus(result.success ? 'completed' : 'error');
      
      if (onCleanupComplete) {
        onCleanupComplete(result.success);
      }

    } catch (error) {
      setCleanupStatus('error');
      console.error('Security cleanup failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSkipCleanup = () => {
    if (onCleanupComplete) {
      onCleanupComplete(true); // Continue without cleanup
    }
    onClose();
  };

  const handleReload = () => {
    window.location.reload();
  };

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'high': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'info';
      default: return 'info';
    }
  };

  const getRiskIcon = (level: string) => {
    switch (level) {
      case 'high': return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'medium': return <ExclamationCircleOutlined style={{ color: '#faad14' }} />;
      case 'low': return <SafetyCertificateOutlined style={{ color: '#52c41a' }} />;
      default: return <SafetyCertificateOutlined />;
    }
  };

  if (!detection) {
    return null;
  }

  if (!detection.isUserSwitch) {
    return null; // No security concerns
  }

  return (
    <Modal
      title={
        <Space>
          {getRiskIcon(detection.riskLevel)}
          <Title level={4} style={{ margin: 0 }}>
            사용자 전환 보안 확인
          </Title>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={null}
      width={600}
      closable={false}
      maskClosable={false}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        
        {/* Security Alert */}
        <Alert
          type={getRiskColor(detection.riskLevel) as any}
          showIcon
          message={`${detection.riskLevel.toUpperCase()} 위험도 사용자 전환 감지`}
          description={
            <div>
              <Paragraph>
                이전 사용자 세션이 활성 상태입니다. 보안을 위해 브라우저 상태를 정리하는 것을 권장합니다.
              </Paragraph>
              
              {detection.previousUserId && (
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  이전 사용자 ID: {detection.previousUserId}
                </Text>
              )}
            </div>
          }
        />

        {/* New User Info */}
        {newUserEmail && (
          <Alert
            type="info"
            showIcon
            message="새 사용자 로그인"
            description={`${newUserEmail}로 로그인하려고 합니다.`}
          />
        )}

        {/* Security Recommendations */}
        <div>
          <Title level={5}>
            <SafetyCertificateOutlined /> 보안 권장사항
          </Title>
          <List
            size="small"
            dataSource={detection.recommendations}
            renderItem={(item) => (
              <List.Item>
                <Text>{item}</Text>
              </List.Item>
            )}
          />
        </div>

        {/* Cleanup Progress */}
        {cleanupStatus === 'running' && (
          <div>
            <Title level={5}>보안 정리 진행중...</Title>
            <Progress 
              percent={cleanupProgress} 
              status="active"
              format={(percent) => `${percent}%`}
            />
            <Text type="secondary">브라우저 상태를 안전하게 정리하고 있습니다.</Text>
          </div>
        )}

        {/* Cleanup Result */}
        {cleanupStatus === 'completed' && cleanupResult && (
          <Alert
            type="success"
            showIcon
            message="보안 정리 완료"
            description={
              <div>
                <Text>브라우저 상태가 안전하게 정리되었습니다.</Text>
                <ul style={{ marginTop: 8, marginBottom: 0, fontSize: '12px' }}>
                  <li>로컬 스토리지: {cleanupResult.localStorage}개 항목 정리</li>
                  <li>세션 스토리지: {cleanupResult.sessionStorage}개 항목 정리</li>
                  {cleanupResult.cookies > 0 && <li>쿠키: {cleanupResult.cookies}개 정리</li>}
                  {cleanupResult.indexedDB && <li>IndexedDB 정리 완료</li>}
                </ul>
              </div>
            }
          />
        )}

        {/* Cleanup Error */}
        {cleanupStatus === 'error' && (
          <Alert
            type="error"
            showIcon
            message="보안 정리 중 오류 발생"
            description="일부 브라우저 상태 정리에 실패했습니다. 페이지를 새로고침하는 것을 권장합니다."
          />
        )}

        {/* Action Buttons */}
        <div style={{ textAlign: 'right' }}>
          <Space>
            {cleanupStatus === 'idle' && (
              <>
                <Button onClick={handleSkipCleanup}>
                  정리 건너뛰기
                </Button>
                <Button 
                  type="primary" 
                  icon={<DeleteOutlined />}
                  onClick={handleCleanup}
                  loading={isLoading}
                >
                  보안 정리 실행
                </Button>
              </>
            )}

            {cleanupStatus === 'completed' && (
              <>
                <Button onClick={onClose}>
                  계속 진행
                </Button>
                <Button 
                  type="primary" 
                  icon={<ReloadOutlined />}
                  onClick={handleReload}
                >
                  페이지 새로고침
                </Button>
              </>
            )}

            {cleanupStatus === 'error' && (
              <>
                <Button onClick={handleCleanup}>
                  다시 시도
                </Button>
                <Button 
                  type="primary" 
                  icon={<ReloadOutlined />}
                  onClick={handleReload}
                >
                  페이지 새로고침
                </Button>
              </>
            )}

            {cleanupStatus === 'running' && (
              <Button disabled>
                정리 진행중...
              </Button>
            )}
          </Space>
        </div>

        {/* Debug Info */}
        {process.env.NODE_ENV === 'development' && cleanupResult && (
          <details>
            <summary style={{ cursor: 'pointer', color: '#666' }}>
              디버그 정보 (개발환경에서만 표시)
            </summary>
            <pre style={{ 
              background: '#f5f5f5', 
              padding: '8px', 
              fontSize: '11px',
              overflow: 'auto',
              maxHeight: '200px'
            }}>
              {JSON.stringify(cleanupResult, null, 2)}
            </pre>
          </details>
        )}
      </Space>
    </Modal>
  );
};