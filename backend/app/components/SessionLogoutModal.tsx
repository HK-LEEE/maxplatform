import React, { useState } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Button,
  VStack,
  HStack,
  Text,
  Radio,
  RadioGroup,
  Box,
  Alert,
  AlertIcon,
  Divider,
  useToast,
  Spinner,
  Icon
} from '@chakra-ui/react';
import { FiSmartphone, FiMonitor, FiTablet, FiLogOut, FiShield } from 'react-icons/fi';

interface SessionInfo {
  session_id: string;
  client_name: string;
  device_info?: {
    device_type: string;
    browser: string;
    os: string;
  };
  location?: {
    country: string;
    city: string;
  };
  created_at: string;
  last_used_at?: string;
  is_current_session: boolean;
  is_suspicious: bool;
}

interface SessionLogoutModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentSession?: SessionInfo;
  otherSessions?: SessionInfo[];
  totalSessions: number;
  suspiciousSessions: number;
  onLogout: (logoutType: 'current' | 'all', reason?: string) => Promise<void>;
}

const SessionLogoutModal: React.FC<SessionLogoutModalProps> = ({
  isOpen,
  onClose,
  currentSession,
  otherSessions = [],
  totalSessions,
  suspiciousSessions,
  onLogout
}) => {
  const [logoutType, setLogoutType] = useState<'current' | 'all'>('current');
  const [isLoading, setIsLoading] = useState(false);
  const toast = useToast();

  const handleLogout = async () => {
    setIsLoading(true);
    try {
      await onLogout(logoutType);
      toast({
        title: 'Logout Successful',
        description: logoutType === 'current' 
          ? 'Current session logged out successfully'
          : 'All sessions logged out successfully',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      onClose();
    } catch (error) {
      toast({
        title: 'Logout Failed',
        description: error instanceof Error ? error.message : 'An error occurred during logout',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const getDeviceIcon = (deviceType?: string) => {
    switch (deviceType?.toLowerCase()) {
      case 'mobile':
        return FiSmartphone;
      case 'tablet':
        return FiTablet;
      case 'desktop':
      default:
        return FiMonitor;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const SessionItem: React.FC<{ session: SessionInfo; isCurrent?: boolean }> = ({ 
    session, 
    isCurrent = false 
  }) => (
    <Box
      p={3}
      borderWidth={1}
      borderRadius="md"
      borderColor={isCurrent ? "blue.200" : "gray.200"}
      bg={isCurrent ? "blue.50" : "white"}
      position="relative"
    >
      <HStack spacing={3}>
        <Icon as={getDeviceIcon(session.device_info?.device_type)} size="20px" />
        <VStack align="start" spacing={1} flex={1}>
          <HStack>
            <Text fontWeight="semibold" fontSize="sm">
              {session.client_name}
            </Text>
            {isCurrent && (
              <Text fontSize="xs" color="blue.600" fontWeight="medium">
                (현재 세션)
              </Text>
            )}
            {session.is_suspicious && (
              <HStack spacing={1}>
                <Icon as={FiShield} color="red.500" size="12px" />
                <Text fontSize="xs" color="red.600">
                  의심스러운 활동
                </Text>
              </HStack>
            )}
          </HStack>
          <Text fontSize="xs" color="gray.600">
            {session.device_info ? 
              `${session.device_info.browser} • ${session.device_info.os}` : 
              '알 수 없는 디바이스'
            }
          </Text>
          <Text fontSize="xs" color="gray.500">
            {session.location ? 
              `${session.location.city}, ${session.location.country}` : 
              '위치 정보 없음'
            }
          </Text>
          <Text fontSize="xs" color="gray.500">
            마지막 사용: {session.last_used_at ? 
              formatDate(session.last_used_at) : 
              formatDate(session.created_at)
            }
          </Text>
        </VStack>
      </HStack>
    </Box>
  );

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>
          <HStack>
            <Icon as={FiLogOut} />
            <Text>로그아웃 옵션 선택</Text>
          </HStack>
        </ModalHeader>
        <ModalCloseButton />
        
        <ModalBody>
          <VStack spacing={4} align="stretch">
            {/* 세션 요약 정보 */}
            <Box>
              <Text fontSize="sm" color="gray.600" mb={2}>
                총 {totalSessions}개의 활성 세션이 있습니다.
                {suspiciousSessions > 0 && (
                  <Text as="span" color="red.600" fontWeight="medium">
                    {' '}({suspiciousSessions}개의 의심스러운 세션 포함)
                  </Text>
                )}
              </Text>
              
              {suspiciousSessions > 0 && (
                <Alert status="warning" size="sm" borderRadius="md">
                  <AlertIcon />
                  <Text fontSize="sm">
                    의심스러운 세션이 감지되었습니다. 보안을 위해 모든 세션에서 로그아웃하는 것을 권장합니다.
                  </Text>
                </Alert>
              )}
            </Box>

            {/* 로그아웃 옵션 선택 */}
            <Box>
              <Text fontWeight="semibold" mb={3}>로그아웃 옵션:</Text>
              <RadioGroup onChange={(value) => setLogoutType(value as 'current' | 'all')} value={logoutType}>
                <VStack align="start" spacing={3}>
                  <Radio value="current" size="md">
                    <VStack align="start" spacing={1} ml={2}>
                      <Text fontWeight="medium">현재 세션만 로그아웃</Text>
                      <Text fontSize="sm" color="gray.600">
                        이 디바이스/브라우저에서만 로그아웃됩니다. 다른 디바이스의 세션은 유지됩니다.
                      </Text>
                    </VStack>
                  </Radio>
                  
                  <Radio value="all" size="md">
                    <VStack align="start" spacing={1} ml={2}>
                      <Text fontWeight="medium">모든 세션에서 로그아웃</Text>
                      <Text fontSize="sm" color="gray.600">
                        모든 디바이스와 브라우저에서 로그아웃됩니다. 다시 로그인해야 합니다.
                      </Text>
                    </VStack>
                  </Radio>
                </VStack>
              </RadioGroup>
            </Box>

            <Divider />

            {/* 현재 세션 정보 */}
            {currentSession && (
              <Box>
                <Text fontWeight="semibold" mb={2}>현재 세션:</Text>
                <SessionItem session={currentSession} isCurrent={true} />
              </Box>
            )}

            {/* 다른 세션 목록 */}
            {otherSessions.length > 0 && (
              <Box>
                <Text fontWeight="semibold" mb={2}>
                  다른 활성 세션 ({otherSessions.length}개):
                </Text>
                <VStack spacing={2} maxH="200px" overflowY="auto">
                  {otherSessions.map((session) => (
                    <SessionItem key={session.session_id} session={session} />
                  ))}
                </VStack>
              </Box>
            )}

            {/* 보안 권고사항 */}
            <Alert status="info" borderRadius="md">
              <AlertIcon />
              <VStack align="start" spacing={1}>
                <Text fontSize="sm" fontWeight="medium">보안 권고사항:</Text>
                <Text fontSize="sm">
                  • 공용 컴퓨터나 의심스러운 디바이스에서 로그인한 경우 모든 세션에서 로그아웃하세요.
                </Text>
                <Text fontSize="sm">
                  • 정기적으로 활성 세션을 확인하고 인식하지 못하는 세션을 제거하세요.
                </Text>
              </VStack>
            </Alert>
          </VStack>
        </ModalBody>

        <ModalFooter>
          <HStack spacing={3}>
            <Button variant="ghost" onClick={onClose} disabled={isLoading}>
              취소
            </Button>
            <Button
              colorScheme={logoutType === 'all' ? 'red' : 'blue'}
              onClick={handleLogout}
              isLoading={isLoading}
              loadingText="로그아웃 중..."
              leftIcon={isLoading ? <Spinner size="sm" /> : <Icon as={FiLogOut} />}
            >
              {logoutType === 'current' ? '현재 세션 로그아웃' : '모든 세션 로그아웃'}
            </Button>
          </HStack>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default SessionLogoutModal;