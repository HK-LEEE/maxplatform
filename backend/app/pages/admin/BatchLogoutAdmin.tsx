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
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Icon,
  Divider,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Skeleton,
  useToast,
  useColorModeValue,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Progress,
  Tooltip
} from '@chakra-ui/react';
import {
  FiUsers,
  FiSmartphone,
  FiClock,
  FiFilter,
  FiAlertTriangle,
  FiRefreshCw,
  FiPlay,
  FiPause,
  FiTrash2,
  FiEye,
  FiSettings,
  FiShield,
  FiMoreVertical
} from 'react-icons/fi';

import GroupLogoutModal from '../../components/admin/GroupLogoutModal';
import ClientLogoutModal from '../../components/admin/ClientLogoutModal';
import TimeBasedLogoutModal from '../../components/admin/TimeBasedLogoutModal';
import EmergencyLogoutModal from '../../components/admin/EmergencyLogoutModal';
import JobDetailsModal from '../../components/admin/JobDetailsModal';
import { useBatchLogoutAdmin } from '../../hooks/useBatchLogoutAdmin';

const BatchLogoutAdmin: React.FC = () => {
  const {
    jobs,
    statistics,
    isLoading,
    fetchJobs,
    fetchStatistics,
    cancelJob,
    createGroupLogout,
    createClientLogout,
    createTimeBasedLogout,
    createEmergencyLogout
  } = useBatchLogoutAdmin();

  const toast = useToast();
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [refreshInterval, setRefreshInterval] = useState<NodeJS.Timeout | null>(null);

  // Modal controls
  const groupModal = useDisclosure();
  const clientModal = useDisclosure();
  const timeModal = useDisclosure();
  const emergencyModal = useDisclosure();
  const jobDetailsModal = useDisclosure();

  // 색상 모드
  const cardBg = useColorModeValue('white', 'gray.700');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  useEffect(() => {
    fetchJobs();
    fetchStatistics();
    
    // 자동 새로고침 설정
    const interval = setInterval(() => {
      fetchJobs();
      fetchStatistics();
    }, 30000); // 30초마다
    
    setRefreshInterval(interval);
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [fetchJobs, fetchStatistics]);

  const handleJobAction = async (jobId: string, action: 'cancel' | 'view') => {
    if (action === 'cancel') {
      try {
        await cancelJob(jobId, 'Cancelled by admin');
        toast({
          title: 'Job Cancelled',
          description: 'Batch logout job has been cancelled successfully',
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
        fetchJobs();
      } catch (error) {
        toast({
          title: 'Error',
          description: 'Failed to cancel job',
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
      }
    } else if (action === 'view') {
      setSelectedJobId(jobId);
      jobDetailsModal.onOpen();
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'green';
      case 'processing':
        return 'blue';
      case 'failed':
        return 'red';
      case 'cancelled':
        return 'gray';
      case 'pending':
        return 'orange';
      default:
        return 'gray';
    }
  };

  const getJobTypeIcon = (jobType: string) => {
    switch (jobType) {
      case 'group_based':
        return FiUsers;
      case 'client_based':
        return FiSmartphone;
      case 'time_based':
        return FiClock;
      case 'conditional':
        return FiFilter;
      case 'emergency':
        return FiAlertTriangle;
      default:
        return FiSettings;
    }
  };

  const formatJobType = (jobType: string) => {
    const types = {
      'group_based': '그룹 기반',
      'client_based': '클라이언트 기반',
      'time_based': '시간 기반',
      'conditional': '조건부',
      'emergency': '긴급'
    };
    return types[jobType as keyof typeof types] || jobType;
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString('ko-KR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  if (isLoading && !jobs.length) {
    return (
      <Container maxW="8xl" py={8}>
        <VStack spacing={6} align="stretch">
          <Skeleton height="60px" />
          <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={6}>
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} height="120px" />
            ))}
          </SimpleGrid>
          <Skeleton height="400px" />
        </VStack>
      </Container>
    );
  }

  return (
    <>
      <Container maxW="8xl" py={8}>
        <VStack spacing={6} align="stretch">
          {/* 헤더 */}
          <HStack justify="space-between" align="center">
            <VStack align="start" spacing={1}>
              <Heading size="lg">일괄 로그아웃 관리</Heading>
              <Text color="gray.600">
                시스템 보안을 위한 일괄 로그아웃 작업을 관리합니다
              </Text>
            </VStack>
            <HStack>
              <Button
                leftIcon={<FiRefreshCw />}
                variant="outline"
                onClick={() => {
                  fetchJobs();
                  fetchStatistics();
                }}
                isLoading={isLoading}
                size="sm"
              >
                새로고침
              </Button>
            </HStack>
          </HStack>

          {/* 통계 카드 */}
          <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={6}>
            <Card bg={cardBg} borderColor={borderColor}>
              <CardBody>
                <Stat>
                  <StatLabel>총 작업 수</StatLabel>
                  <StatNumber>{statistics?.total_jobs || 0}</StatNumber>
                  <StatHelpText>전체 일괄 로그아웃 작업</StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card bg={cardBg} borderColor={borderColor}>
              <CardBody>
                <Stat>
                  <StatLabel>처리 중인 작업</StatLabel>
                  <StatNumber color="blue.500">
                    {statistics?.processing_jobs || 0}
                  </StatNumber>
                  <StatHelpText>현재 실행 중</StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card bg={cardBg} borderColor={borderColor}>
              <CardBody>
                <Stat>
                  <StatLabel>완료된 작업</StatLabel>
                  <StatNumber color="green.500">
                    {statistics?.completed_jobs || 0}
                  </StatNumber>
                  <StatHelpText>성공적으로 완료</StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card bg={cardBg} borderColor={borderColor}>
              <CardBody>
                <Stat>
                  <StatLabel>실패한 작업</StatLabel>
                  <StatNumber color="red.500">
                    {statistics?.failed_jobs || 0}
                  </StatNumber>
                  <StatHelpText>오류로 인한 실패</StatHelpText>
                </Stat>
              </CardBody>
            </Card>
          </SimpleGrid>

          {/* 경고 알림 */}
          {statistics?.emergency_jobs && statistics.emergency_jobs > 0 && (
            <Alert status="warning" borderRadius="lg">
              <AlertIcon />
              <VStack align="start" spacing={1}>
                <Text fontWeight="medium">
                  최근 {statistics.emergency_jobs}개의 긴급 로그아웃이 실행되었습니다
                </Text>
                <Text fontSize="sm">
                  보안 상황을 확인하고 필요한 조치를 취하세요.
                </Text>
              </VStack>
            </Alert>
          )}

          {/* 작업 생성 및 관리 */}
          <Tabs variant="enclosed" colorScheme="blue">
            <TabList>
              <Tab>작업 생성</Tab>
              <Tab>작업 관리</Tab>
              <Tab>감사 로그</Tab>
            </TabList>

            <TabPanels>
              {/* 작업 생성 탭 */}
              <TabPanel>
                <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
                  <Card bg={cardBg} borderColor={borderColor}>
                    <CardBody>
                      <VStack spacing={4}>
                        <Icon as={FiUsers} size="40px" color="blue.500" />
                        <VStack spacing={2}>
                          <Text fontWeight="semibold">그룹 기반 로그아웃</Text>
                          <Text fontSize="sm" color="gray.600" textAlign="center">
                            특정 그룹의 모든 사용자 세션을 일괄 종료합니다
                          </Text>
                        </VStack>
                        <Button
                          colorScheme="blue"
                          size="sm"
                          onClick={groupModal.onOpen}
                          leftIcon={<FiUsers />}
                        >
                          그룹 로그아웃 실행
                        </Button>
                      </VStack>
                    </CardBody>
                  </Card>

                  <Card bg={cardBg} borderColor={borderColor}>
                    <CardBody>
                      <VStack spacing={4}>
                        <Icon as={FiSmartphone} size="40px" color="green.500" />
                        <VStack spacing={2}>
                          <Text fontWeight="semibold">클라이언트 기반 로그아웃</Text>
                          <Text fontSize="sm" color="gray.600" textAlign="center">
                            특정 앱/클라이언트의 모든 세션을 일괄 종료합니다
                          </Text>
                        </VStack>
                        <Button
                          colorScheme="green"
                          size="sm"
                          onClick={clientModal.onOpen}
                          leftIcon={<FiSmartphone />}
                        >
                          클라이언트 로그아웃 실행
                        </Button>
                      </VStack>
                    </CardBody>
                  </Card>

                  <Card bg={cardBg} borderColor={borderColor}>
                    <CardBody>
                      <VStack spacing={4}>
                        <Icon as={FiClock} size="40px" color="orange.500" />
                        <VStack spacing={2}>
                          <Text fontWeight="semibold">시간 기반 로그아웃</Text>
                          <Text fontSize="sm" color="gray.600" textAlign="center">
                            특정 시간 이전의 오래된 세션을 정리합니다
                          </Text>
                        </VStack>
                        <Button
                          colorScheme="orange"
                          size="sm"
                          onClick={timeModal.onOpen}
                          leftIcon={<FiClock />}
                        >
                          시간 기반 로그아웃 실행
                        </Button>
                      </VStack>
                    </CardBody>
                  </Card>

                  <Card bg="red.50" borderColor="red.200" gridColumn={{ base: 'span 1', lg: 'span 3' }}>
                    <CardBody>
                      <HStack spacing={6} justify="center">
                        <Icon as={FiAlertTriangle} size="40px" color="red.500" />
                        <VStack spacing={2} flex={1}>
                          <Text fontWeight="semibold" color="red.700">
                            긴급 전체 로그아웃
                          </Text>
                          <Text fontSize="sm" color="red.600" textAlign="center">
                            보안 사고 시 모든 사용자의 모든 세션을 즉시 종료합니다.
                            이 작업은 되돌릴 수 없으며 추가 인증이 필요합니다.
                          </Text>
                        </VStack>
                        <Button
                          colorScheme="red"
                          variant="outline"
                          size="sm"
                          onClick={emergencyModal.onOpen}
                          leftIcon={<FiShield />}
                        >
                          긴급 로그아웃 실행
                        </Button>
                      </HStack>
                    </CardBody>
                  </Card>
                </SimpleGrid>
              </TabPanel>

              {/* 작업 관리 탭 */}
              <TabPanel>
                <Card bg={cardBg} borderColor={borderColor}>
                  <CardHeader>
                    <HStack justify="space-between">
                      <Text fontWeight="semibold">진행 중인 작업</Text>
                      <Badge colorScheme="blue">
                        {jobs.filter(job => ['pending', 'processing'].includes(job.status)).length}개
                      </Badge>
                    </HStack>
                  </CardHeader>
                  <CardBody>
                    {jobs.length === 0 ? (
                      <VStack spacing={4} py={8}>
                        <Icon as={FiSettings} size="48px" color="gray.400" />
                        <Text color="gray.600">진행 중인 일괄 로그아웃 작업이 없습니다.</Text>
                      </VStack>
                    ) : (
                      <Table variant="simple">
                        <Thead>
                          <Tr>
                            <Th>작업 ID</Th>
                            <Th>유형</Th>
                            <Th>상태</Th>
                            <Th>진행률</Th>
                            <Th>실행자</Th>
                            <Th>생성 시간</Th>
                            <Th>작업</Th>
                          </Tr>
                        </Thead>
                        <Tbody>
                          {jobs.map((job) => (
                            <Tr key={job.job_id}>
                              <Td>
                                <Text fontFamily="mono" fontSize="sm">
                                  {job.job_id.slice(0, 8)}...
                                </Text>
                              </Td>
                              <Td>
                                <HStack spacing={2}>
                                  <Icon as={getJobTypeIcon(job.type)} />
                                  <Text>{formatJobType(job.type)}</Text>
                                </HStack>
                              </Td>
                              <Td>
                                <Badge colorScheme={getStatusColor(job.status)}>
                                  {job.status}
                                </Badge>
                              </Td>
                              <Td>
                                <VStack spacing={1} align="start">
                                  <Progress
                                    value={job.progress}
                                    size="sm"
                                    colorScheme={getStatusColor(job.status)}
                                    width="60px"
                                  />
                                  <Text fontSize="xs" color="gray.600">
                                    {job.progress}%
                                  </Text>
                                </VStack>
                              </Td>
                              <Td>
                                <VStack spacing={0} align="start">
                                  <Text fontSize="sm">
                                    {job.initiated_by.name || job.initiated_by.email}
                                  </Text>
                                  <Text fontSize="xs" color="gray.600">
                                    {job.initiated_by.email}
                                  </Text>
                                </VStack>
                              </Td>
                              <Td>
                                <Text fontSize="sm">
                                  {formatDateTime(job.created_at)}
                                </Text>
                              </Td>
                              <Td>
                                <Menu>
                                  <MenuButton
                                    as={IconButton}
                                    icon={<FiMoreVertical />}
                                    variant="ghost"
                                    size="sm"
                                  />
                                  <MenuList>
                                    <MenuItem
                                      icon={<FiEye />}
                                      onClick={() => handleJobAction(job.job_id, 'view')}
                                    >
                                      상세 보기
                                    </MenuItem>
                                    {['pending', 'processing'].includes(job.status) && (
                                      <MenuItem
                                        icon={<FiTrash2 />}
                                        color="red.600"
                                        onClick={() => handleJobAction(job.job_id, 'cancel')}
                                      >
                                        작업 취소
                                      </MenuItem>
                                    )}
                                  </MenuList>
                                </Menu>
                              </Td>
                            </Tr>
                          ))}
                        </Tbody>
                      </Table>
                    )}
                  </CardBody>
                </Card>
              </TabPanel>

              {/* 감사 로그 탭 */}
              <TabPanel>
                <Card bg={cardBg} borderColor={borderColor}>
                  <CardHeader>
                    <Text fontWeight="semibold">보안 감사 로그</Text>
                  </CardHeader>
                  <CardBody>
                    <VStack spacing={4} py={8}>
                      <Icon as={FiShield} size="48px" color="gray.400" />
                      <Text color="gray.600">감사 로그 기능은 곧 추가될 예정입니다.</Text>
                    </VStack>
                  </CardBody>
                </Card>
              </TabPanel>
            </TabPanels>
          </Tabs>
        </VStack>
      </Container>

      {/* 모달들 */}
      <GroupLogoutModal
        isOpen={groupModal.isOpen}
        onClose={groupModal.onClose}
        onSubmit={createGroupLogout}
      />
      
      <ClientLogoutModal
        isOpen={clientModal.isOpen}
        onClose={clientModal.onClose}
        onSubmit={createClientLogout}
      />
      
      <TimeBasedLogoutModal
        isOpen={timeModal.isOpen}
        onClose={timeModal.onClose}
        onSubmit={createTimeBasedLogout}
      />
      
      <EmergencyLogoutModal
        isOpen={emergencyModal.isOpen}
        onClose={emergencyModal.onClose}
        onSubmit={createEmergencyLogout}
      />
      
      {selectedJobId && (
        <JobDetailsModal
          isOpen={jobDetailsModal.isOpen}
          onClose={() => {
            jobDetailsModal.onClose();
            setSelectedJobId(null);
          }}
          jobId={selectedJobId}
        />
      )}
    </>
  );
};

export default BatchLogoutAdmin;