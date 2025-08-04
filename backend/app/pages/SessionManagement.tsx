import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Heading,
  VStack,
  HStack,
  Text,
  Button,
  Card,
  CardHeader,
  CardBody,
  Alert,
  AlertIcon,
  Badge,
  IconButton,
  useDisclosure,
  Skeleton,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Icon,
  Divider,
  Tooltip,
  useColorModeValue
} from '@chakra-ui/react';
import {
  FiSmartphone,
  FiMonitor,
  FiTablet,
  FiLogOut,
  FiShield,
  FiRefreshCw,
  FiClock,
  FiMapPin,
  FiTrash2
} from 'react-icons/fi';

import SessionLogoutModal from '../components/SessionLogoutModal';
import useSessionLogout from '../hooks/useSessionLogout';

const SessionManagement: React.FC = () => {
  const {
    isLoading,
    sessionsData,
    fetchActiveSessions,
    executeLogout,
    logoutSpecificSessions
  } = useSessionLogout();

  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedSessions, setSelectedSessions] = useState<string[]>([]);

  // 색상 모드
  const cardBg = useColorModeValue('white', 'gray.700');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const suspiciousBg = useColorModeValue('red.50', 'red.900');
  const suspiciousBorder = useColorModeValue('red.200', 'red.600');

  useEffect(() => {
    fetchActiveSessions();
  }, [fetchActiveSessions]);

  const handleLogoutModal = async (logoutType: 'current' | 'all', reason?: string) => {
    await executeLogout(logoutType, reason);
  };

  const handleRefresh = () => {
    fetchActiveSessions();
  };

  const handleLogoutSpecificSession = async (sessionId: string) => {
    try {
      await logoutSpecificSessions([sessionId], 'User terminated specific session');
    } catch (error) {
      console.error('Failed to logout specific session:', error);
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

  const SessionCard: React.FC<{
    session: any;
    isCurrent?: boolean;
    onLogout?: () => void;
  }> = ({ session, isCurrent = false, onLogout }) => (
    <Card
      bg={session.is_suspicious ? suspiciousBg : cardBg}
      borderColor={session.is_suspicious ? suspiciousBorder : borderColor}
      borderWidth={isCurrent ? 2 : 1}
      borderStyle={isCurrent ? 'solid' : 'solid'}
    >
      <CardBody>
        <VStack align="stretch" spacing={3}>
          <HStack justify="space-between">
            <HStack spacing={3}>
              <Icon as={getDeviceIcon(session.device_info?.device_type)} size="20px" />
              <VStack align="start" spacing={0}>
                <HStack>
                  <Text fontWeight="semibold">{session.client_name}</Text>
                  {isCurrent && (
                    <Badge colorScheme="blue" size="sm">
                      현재 세션
                    </Badge>
                  )}
                  {session.is_suspicious && (
                    <Badge colorScheme="red" size="sm">
                      <Icon as={FiShield} mr={1} />
                      의심스러운 활동
                    </Badge>
                  )}
                </HStack>
                <Text fontSize="sm" color="gray.600">
                  {session.device_info
                    ? `${session.device_info.browser} • ${session.device_info.os}`
                    : '알 수 없는 디바이스'}
                </Text>
              </VStack>
            </HStack>
            {!isCurrent && onLogout && (
              <Tooltip label="이 세션 로그아웃">
                <IconButton
                  aria-label="Logout session"
                  icon={<FiTrash2 />}
                  size="sm"
                  variant="ghost"
                  colorScheme="red"
                  onClick={onLogout}
                />
              </Tooltip>
            )}
          </HStack>

          <Divider />

          <SimpleGrid columns={2} spacing={4}>
            <Box>
              <HStack>
                <Icon as={FiMapPin} size="14px" color="gray.500" />
                <Text fontSize="sm" color="gray.600">
                  위치
                </Text>
              </HStack>
              <Text fontSize="sm" fontWeight="medium">
                {session.location
                  ? `${session.location.city}, ${session.location.country}`
                  : '위치 정보 없음'}
              </Text>
            </Box>

            <Box>
              <HStack>
                <Icon as={FiClock} size="14px" color="gray.500" />
                <Text fontSize="sm" color="gray.600">
                  마지막 사용
                </Text>
              </HStack>
              <Text fontSize="sm" fontWeight="medium">
                {session.last_used_at
                  ? formatDate(session.last_used_at)
                  : formatDate(session.created_at)}
              </Text>
            </Box>
          </SimpleGrid>

          {session.ip_address && (
            <Box>
              <Text fontSize="xs" color="gray.500">
                IP: {session.ip_address}
              </Text>
            </Box>
          )}
        </VStack>
      </CardBody>
    </Card>
  );

  if (isLoading && !sessionsData) {
    return (
      <Container maxW="6xl" py={8}>
        <VStack spacing={6} align="stretch">
          <Skeleton height="40px" />
          <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} height="200px" />
            ))}
          </SimpleGrid>
        </VStack>
      </Container>
    );
  }

  return (
    <>
      <Container maxW="6xl" py={8}>
        <VStack spacing={6} align="stretch">
          {/* 헤더 */}
          <HStack justify="space-between" align="center">
            <Heading size="lg">세션 관리</Heading>
            <HStack>
              <Button
                leftIcon={<FiRefreshCw />}
                variant="outline"
                onClick={handleRefresh}
                isLoading={isLoading}
                size="sm"
              >
                새로고침
              </Button>
              <Button
                leftIcon={<FiLogOut />}
                colorScheme="red"
                onClick={onOpen}
                size="sm"
              >
                로그아웃
              </Button>
            </HStack>
          </HStack>

          {/* 요약 통계 */}
          {sessionsData && (
            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6}>
              <Card>
                <CardBody>
                  <Stat>
                    <StatLabel>총 활성 세션</StatLabel>
                    <StatNumber>{sessionsData.total_sessions}</StatNumber>
                    <StatHelpText>현재 로그인된 세션 수</StatHelpText>
                  </Stat>
                </CardBody>
              </Card>

              <Card>
                <CardBody>
                  <Stat>
                    <StatLabel>다른 디바이스</StatLabel>
                    <StatNumber>{sessionsData.other_sessions.length}</StatNumber>
                    <StatHelpText>현재 디바이스 외 세션</StatHelpText>
                  </Stat>
                </CardBody>
              </Card>

              <Card>
                <CardBody>
                  <Stat>
                    <StatLabel>의심스러운 세션</StatLabel>
                    <StatNumber color={sessionsData.suspicious_sessions > 0 ? 'red.500' : 'green.500'}>
                      {sessionsData.suspicious_sessions}
                    </StatNumber>
                    <StatHelpText>
                      {sessionsData.suspicious_sessions > 0 ? '확인 필요' : '안전'}
                    </StatHelpText>
                  </Stat>
                </CardBody>
              </Card>
            </SimpleGrid>
          )}

          {/* 보안 경고 */}
          {sessionsData && sessionsData.suspicious_sessions > 0 && (
            <Alert status="warning" borderRadius="lg">
              <AlertIcon />
              <VStack align="start" spacing={1}>
                <Text fontWeight="medium">의심스러운 세션이 감지되었습니다</Text>
                <Text fontSize="sm">
                  보안을 위해 인식하지 못하는 세션을 확인하고 필요시 모든 세션에서 로그아웃하세요.
                </Text>
              </VStack>
            </Alert>
          )}

          {/* 현재 세션 */}
          {sessionsData?.current_session && (
            <Box>
              <Heading size="md" mb={4}>
                현재 세션
              </Heading>
              <SessionCard session={sessionsData.current_session} isCurrent={true} />
            </Box>
          )}

          {/* 다른 세션들 */}
          {sessionsData && sessionsData.other_sessions.length > 0 && (
            <Box>
              <Heading size="md" mb={4}>
                다른 활성 세션 ({sessionsData.other_sessions.length}개)
              </Heading>
              <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
                {sessionsData.other_sessions.map((session) => (
                  <SessionCard
                    key={session.session_id}
                    session={session}
                    onLogout={() => handleLogoutSpecificSession(session.session_id)}
                  />
                ))}
              </SimpleGrid>
            </Box>
          )}

          {/* 세션이 없는 경우 */}
          {sessionsData && sessionsData.other_sessions.length === 0 && (
            <Card>
              <CardBody>
                <VStack spacing={4} py={8}>
                  <Icon as={FiMonitor} size="48px" color="gray.400" />
                  <Text color="gray.600">현재 세션 외에 다른 활성 세션이 없습니다.</Text>
                  <Text fontSize="sm" color="gray.500">
                    다른 디바이스에서 로그인하지 않았거나 모든 세션이 만료되었습니다.
                  </Text>
                </VStack>
              </CardBody>
            </Card>
          )}

          {/* 보안 가이드 */}
          <Card>
            <CardHeader>
              <Heading size="sm">보안 권고사항</Heading>
            </CardHeader>
            <CardBody>
              <VStack align="start" spacing={2}>
                <Text fontSize="sm">
                  • 공용 컴퓨터나 신뢰할 수 없는 네트워크에서 로그인한 경우 사용 후 반드시 로그아웃하세요.
                </Text>
                <Text fontSize="sm">
                  • 인식하지 못하는 세션이나 의심스러운 활동이 감지되면 즉시 해당 세션을 종료하세요.
                </Text>
                <Text fontSize="sm">
                  • 정기적으로 활성 세션을 확인하고 필요하지 않은 세션은 제거하세요.
                </Text>
                <Text fontSize="sm">
                  • 패스워드를 변경한 경우 모든 세션에서 로그아웃한 후 다시 로그인하세요.
                </Text>
              </VStack>
            </CardBody>
          </Card>
        </VStack>
      </Container>

      {/* 로그아웃 모달 */}
      <SessionLogoutModal
        isOpen={isOpen}
        onClose={onClose}
        currentSession={sessionsData?.current_session}
        otherSessions={sessionsData?.other_sessions}
        totalSessions={sessionsData?.total_sessions || 0}
        suspiciousSessions={sessionsData?.suspicious_sessions || 0}
        onLogout={handleLogoutModal}
      />
    </>
  );
};

export default SessionManagement;