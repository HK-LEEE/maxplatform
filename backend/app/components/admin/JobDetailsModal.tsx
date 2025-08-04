import React, { useState, useEffect } from 'react';
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
  Box,
  Badge,
  Icon,
  Divider,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Progress,
  Alert,
  AlertIcon,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Code,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Skeleton,
  useToast,
  useColorModeValue
} from '@chakra-ui/react';
import { 
  FiUsers, 
  FiSmartphone, 
  FiClock, 
  FiFilter, 
  FiAlertTriangle, 
  FiSettings,
  FiUser,
  FiCalendar,
  FiTrendingUp,
  FiInfo,
  FiAlertCircle,
  FiCheckCircle,
  FiXCircle,
  FiRefreshCw
} from 'react-icons/fi';

interface JobDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  jobId: string;
}

interface BatchLogoutJob {
  job_id: string;
  type: string;
  status: string;
  priority: string;
  dry_run: boolean;
  progress: number;
  initiated_by: {
    id: string;
    email: string;
    name: string;
  };
  reason: string;
  conditions: any;
  statistics?: any;
  error_details?: any;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  cancelled_at?: string;
}

const JobDetailsModal: React.FC<JobDetailsModalProps> = ({
  isOpen,
  onClose,
  jobId
}) => {
  const [job, setJob] = useState<BatchLogoutJob | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const toast = useToast();

  // 색상 모드
  const cardBg = useColorModeValue('gray.50', 'gray.700');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  useEffect(() => {
    if (isOpen && jobId) {
      fetchJobDetails();
    }
  }, [isOpen, jobId]);

  const fetchJobDetails = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/admin/oauth/batch-logout/jobs/${jobId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setJob(data);
      } else {
        throw new Error('작업 정보를 가져올 수 없습니다.');
      }
    } catch (error) {
      console.error('Failed to fetch job details:', error);
      toast({
        title: '오류 발생',
        description: error instanceof Error ? error.message : '작업 상세 정보 조회에 실패했습니다.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
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

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return FiCheckCircle;
      case 'processing':
        return FiRefreshCw;
      case 'failed':
        return FiXCircle;
      case 'cancelled':
        return FiXCircle;
      case 'pending':
        return FiClock;
      default:
        return FiInfo;
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

  const formatDuration = (startTime: string, endTime?: string) => {
    const start = new Date(startTime);
    const end = endTime ? new Date(endTime) : new Date();
    const diffMs = end.getTime() - start.getTime();
    
    const minutes = Math.floor(diffMs / 60000);
    const seconds = Math.floor((diffMs % 60000) / 1000);
    
    if (minutes > 0) {
      return `${minutes}분 ${seconds}초`;
    }
    return `${seconds}초`;
  };

  const renderOverviewTab = () => (
    <VStack spacing={6} align="stretch">
      {/* 기본 정보 */}
      <Box bg={cardBg} p={4} borderRadius="md" borderWidth="1px" borderColor={borderColor}>
        <VStack spacing={4} align="stretch">
          <HStack justify="space-between">
            <HStack spacing={3}>
              <Icon as={getJobTypeIcon(job?.type || '')} size="24px" />
              <VStack align="start" spacing={0}>
                <Text fontWeight="semibold">
                  {formatJobType(job?.type || '')} 로그아웃
                </Text>
                <Text fontSize="sm" color="gray.600" fontFamily="mono">
                  {job?.job_id}
                </Text>
              </VStack>
            </HStack>
            <HStack spacing={2}>
              <Badge colorScheme={getStatusColor(job?.status || '')}>
                {job?.status}
              </Badge>
              {job?.dry_run && (
                <Badge colorScheme="green" variant="outline">
                  시뮬레이션
                </Badge>
              )}
              <Badge colorScheme="purple" variant="outline">
                {job?.priority} 우선순위
              </Badge>
            </HStack>
          </HStack>

          <Progress
            value={job?.progress || 0}
            colorScheme={getStatusColor(job?.status || '')}
            size="lg"
            borderRadius="md"
          />
          <Text fontSize="sm" color="gray.600" textAlign="center">
            진행률: {job?.progress || 0}%
          </Text>
        </VStack>
      </Box>

      {/* 실행자 정보 */}
      <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
        <Box bg={cardBg} p={4} borderRadius="md" borderWidth="1px" borderColor={borderColor}>
          <VStack spacing={3} align="start">
            <HStack>
              <Icon as={FiUser} />
              <Text fontWeight="semibold">실행자 정보</Text>
            </HStack>
            <VStack spacing={2} align="start">
              <Text fontSize="sm">
                <Text as="span" fontWeight="medium">이름:</Text> {job?.initiated_by.name || '알 수 없음'}
              </Text>
              <Text fontSize="sm">
                <Text as="span" fontWeight="medium">이메일:</Text> {job?.initiated_by.email}
              </Text>
              <Text fontSize="sm">
                <Text as="span" fontWeight="medium">ID:</Text> 
                <Code fontSize="xs" ml={2}>{job?.initiated_by.id}</Code>
              </Text>
            </VStack>
          </VStack>
        </Box>

        <Box bg={cardBg} p={4} borderRadius="md" borderWidth="1px" borderColor={borderColor}>
          <VStack spacing={3} align="start">
            <HStack>
              <Icon as={FiCalendar} />
              <Text fontWeight="semibold">시간 정보</Text>
            </HStack>
            <VStack spacing={2} align="start">
              <Text fontSize="sm">
                <Text as="span" fontWeight="medium">생성:</Text> {job ? formatDateTime(job.created_at) : '-'}
              </Text>
              {job?.started_at && (
                <Text fontSize="sm">
                  <Text as="span" fontWeight="medium">시작:</Text> {formatDateTime(job.started_at)}
                </Text>
              )}
              {job?.completed_at && (
                <Text fontSize="sm">
                  <Text as="span" fontWeight="medium">완료:</Text> {formatDateTime(job.completed_at)}
                </Text>
              )}
              {job?.cancelled_at && (
                <Text fontSize="sm">
                  <Text as="span" fontWeight="medium">취소:</Text> {formatDateTime(job.cancelled_at)}
                </Text>
              )}
              {job?.started_at && (
                <Text fontSize="sm">
                  <Text as="span" fontWeight="medium">소요시간:</Text> 
                  {formatDuration(job.started_at, job.completed_at || job.cancelled_at)}
                </Text>
              )}
            </VStack>
          </VStack>
        </Box>
      </SimpleGrid>

      {/* 로그아웃 사유 */}
      <Box bg={cardBg} p={4} borderRadius="md" borderWidth="1px" borderColor={borderColor}>
        <VStack spacing={3} align="start">
          <Text fontWeight="semibold">로그아웃 사유</Text>
          <Text fontSize="sm" whiteSpace="pre-wrap">
            {job?.reason || '사유가 기록되지 않았습니다.'}
          </Text>
        </VStack>
      </Box>
    </VStack>
  );

  const renderConditionsTab = () => (
    <VStack spacing={6} align="stretch">
      <Box bg={cardBg} p={4} borderRadius="md" borderWidth="1px" borderColor={borderColor}>
        <VStack spacing={3} align="start">
          <Text fontWeight="semibold">작업 조건</Text>
          {job?.conditions ? (
            <Box as="pre" fontSize="sm" overflow="auto" maxH="400px" w="full">
              <Code p={4} borderRadius="md" display="block" whiteSpace="pre-wrap">
                {JSON.stringify(job.conditions, null, 2)}
              </Code>
            </Box>
          ) : (
            <Text fontSize="sm" color="gray.600">
              조건 정보가 없습니다.
            </Text>
          )}
        </VStack>
      </Box>
    </VStack>
  );

  const renderStatisticsTab = () => (
    <VStack spacing={6} align="stretch">
      {job?.statistics ? (
        <>
          {/* 주요 통계 */}
          <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
            <Stat bg={cardBg} p={4} borderRadius="md" borderWidth="1px" borderColor={borderColor}>
              <StatLabel>영향받은 사용자</StatLabel>
              <StatNumber color="blue.500">
                {job.statistics.total_users_affected || 0}명
              </StatNumber>
              <StatHelpText>로그아웃된 사용자 수</StatHelpText>
            </Stat>

            <Stat bg={cardBg} p={4} borderRadius="md" borderWidth="1px" borderColor={borderColor}>
              <StatLabel>해지된 액세스 토큰</StatLabel>
              <StatNumber color="orange.500">
                {job.statistics.total_access_tokens_revoked || 0}개
              </StatNumber>
              <StatHelpText>무효화된 액세스 토큰</StatHelpText>
            </Stat>

            <Stat bg={cardBg} p={4} borderRadius="md" borderWidth="1px" borderColor={borderColor}>
              <StatLabel>해지된 리프레시 토큰</StatLabel>
              <StatNumber color="red.500">
                {job.statistics.total_refresh_tokens_revoked || 0}개
              </StatNumber>
              <StatHelpText>무효화된 리프레시 토큰</StatHelpText>
            </Stat>
          </SimpleGrid>

          {/* 상세 통계 */}
          <Box bg={cardBg} p={4} borderRadius="md" borderWidth="1px" borderColor={borderColor}>
            <VStack spacing={3} align="start">
              <Text fontWeight="semibold">상세 통계</Text>
              <Box as="pre" fontSize="sm" overflow="auto" maxH="300px" w="full">
                <Code p={4} borderRadius="md" display="block" whiteSpace="pre-wrap">
                  {JSON.stringify(job.statistics, null, 2)}
                </Code>
              </Box>
            </VStack>
          </Box>
        </>
      ) : (
        <Box bg={cardBg} p={8} borderRadius="md" borderWidth="1px" borderColor={borderColor} textAlign="center">
          <Icon as={FiTrendingUp} size="48px" color="gray.400" mb={4} />
          <Text color="gray.600">통계 정보가 아직 없습니다.</Text>
          <Text fontSize="sm" color="gray.500" mt={2}>
            작업이 완료되면 상세한 통계가 표시됩니다.
          </Text>
        </Box>
      )}
    </VStack>
  );

  const renderErrorsTab = () => (
    <VStack spacing={6} align="stretch">
      {job?.error_details ? (
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          <VStack align="start" spacing={3} flex={1}>
            <Text fontWeight="medium">오류 발생</Text>
            <Box w="full">
              <Text fontSize="sm" fontWeight="medium" mb={2}>오류 상세:</Text>
              <Box as="pre" fontSize="sm" overflow="auto" maxH="300px" w="full">
                <Code p={4} borderRadius="md" display="block" whiteSpace="pre-wrap" colorScheme="red">
                  {typeof job.error_details === 'string' 
                    ? job.error_details 
                    : JSON.stringify(job.error_details, null, 2)
                  }
                </Code>
              </Box>
            </Box>
          </VStack>
        </Alert>
      ) : job?.status === 'failed' ? (
        <Box bg={cardBg} p={8} borderRadius="md" borderWidth="1px" borderColor={borderColor} textAlign="center">
          <Icon as={FiAlertCircle} size="48px" color="red.400" mb={4} />
          <Text color="gray.600">오류 정보가 기록되지 않았습니다.</Text>
        </Box>
      ) : (
        <Box bg={cardBg} p={8} borderRadius="md" borderWidth="1px" borderColor={borderColor} textAlign="center">
          <Icon as={FiCheckCircle} size="48px" color="green.400" mb={4} />
          <Text color="gray.600">오류가 발생하지 않았습니다.</Text>
        </Box>
      )}
    </VStack>
  );

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="4xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>
          <HStack>
            <Icon as={getStatusIcon(job?.status || '')} />
            <Text>작업 상세 정보</Text>
            {job && (
              <Badge colorScheme={getStatusColor(job.status)}>
                {job.status}
              </Badge>
            )}
          </HStack>
        </ModalHeader>
        <ModalCloseButton />
        
        <ModalBody>
          {isLoading ? (
            <VStack spacing={4}>
              <Skeleton height="120px" />
              <Skeleton height="200px" />
              <Skeleton height="160px" />
            </VStack>
          ) : job ? (
            <Tabs variant="enclosed" colorScheme="blue">
              <TabList>
                <Tab>개요</Tab>
                <Tab>조건</Tab>
                <Tab>통계</Tab>
                <Tab>오류</Tab>
              </TabList>

              <TabPanels>
                <TabPanel>
                  {renderOverviewTab()}
                </TabPanel>
                <TabPanel>
                  {renderConditionsTab()}
                </TabPanel>
                <TabPanel>
                  {renderStatisticsTab()}
                </TabPanel>
                <TabPanel>
                  {renderErrorsTab()}
                </TabPanel>
              </TabPanels>
            </Tabs>
          ) : (
            <Box textAlign="center" py={8}>
              <Icon as={FiAlertCircle} size="48px" color="red.400" mb={4} />
              <Text color="gray.600">작업 정보를 불러올 수 없습니다.</Text>
            </Box>
          )}
        </ModalBody>

        <ModalFooter>
          <HStack spacing={3}>
            <Button variant="ghost" onClick={onClose}>
              닫기
            </Button>
            <Button
              leftIcon={<Icon as={FiRefreshCw} />}
              onClick={fetchJobDetails}
              isLoading={isLoading}
              size="sm"
            >
              새로고침
            </Button>
          </HStack>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default JobDetailsModal;