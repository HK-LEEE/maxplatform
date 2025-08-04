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
  FormControl,
  FormLabel,
  Input,
  Textarea,
  Switch,
  Alert,
  AlertIcon,
  Box,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  useToast,
  Spinner,
  Icon,
  Checkbox,
  CheckboxGroup,
  Stack,
  Badge,
  Divider
} from '@chakra-ui/react';
import { FiClock, FiInfo, FiTrash2 } from 'react-icons/fi';

interface TimeBasedLogoutModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: TimeBasedLogoutData) => Promise<void>;
}

interface TimeBasedLogoutData {
  created_before?: string;
  last_used_before?: string;
  token_types: string[];
  reason: string;
  dry_run: boolean;
}

const TimeBasedLogoutModal: React.FC<TimeBasedLogoutModalProps> = ({
  isOpen,
  onClose,
  onSubmit
}) => {
  const [formData, setFormData] = useState<TimeBasedLogoutData>({
    created_before: '',
    last_used_before: '',
    token_types: ['access_token', 'refresh_token'],
    reason: '',
    dry_run: true
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [estimatedImpact, setEstimatedImpact] = useState<any>(null);
  
  const toast = useToast();

  // 모달이 열릴 때 영향 추정
  useEffect(() => {
    if (isOpen && (formData.created_before || formData.last_used_before)) {
      estimateImpact();
    }
  }, [isOpen, formData.created_before, formData.last_used_before, formData.token_types]);

  const estimateImpact = async () => {
    if (!formData.created_before && !formData.last_used_before) return;

    try {
      const response = await fetch('/api/admin/oauth/batch-logout/time-based', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...formData,
          dry_run: true
        }),
      });

      if (response.ok) {
        const result = await response.json();
        setEstimatedImpact(result);
      }
    } catch (error) {
      console.error('Failed to estimate impact:', error);
    }
  };

  const handleSubmit = async () => {
    if (!formData.reason.trim()) {
      toast({
        title: '입력 오류',
        description: '시간 기반 로그아웃 사유를 입력해주세요.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    if (!formData.created_before && !formData.last_used_before) {
      toast({
        title: '입력 오류',
        description: '생성 시간 또는 마지막 사용 시간 중 하나는 반드시 설정해야 합니다.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    if (formData.token_types.length === 0) {
      toast({
        title: '입력 오류',
        description: '삭제할 토큰 유형을 최소 하나는 선택해야 합니다.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    setIsSubmitting(true);
    try {
      const submitData = {
        ...formData,
        created_before: formData.created_before || undefined,
        last_used_before: formData.last_used_before || undefined
      };

      await onSubmit(submitData);
      
      toast({
        title: '시간 기반 로그아웃 요청 완료',
        description: formData.dry_run 
          ? '시뮬레이션이 완료되었습니다.' 
          : '시간 기반 로그아웃 작업이 시작되었습니다.',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      
      handleClose();
    } catch (error) {
      toast({
        title: '오류 발생',
        description: error instanceof Error ? error.message : '시간 기반 로그아웃 요청에 실패했습니다.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setFormData({
      created_before: '',
      last_used_before: '',
      token_types: ['access_token', 'refresh_token'],
      reason: '',
      dry_run: true
    });
    setEstimatedImpact(null);
    onClose();
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('ko-KR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getRelativeTime = (dateString: string) => {
    const now = new Date();
    const targetDate = new Date(dateString);
    const diffMs = now.getTime() - targetDate.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return '오늘';
    if (diffDays === 1) return '1일 전';
    if (diffDays < 30) return `${diffDays}일 전`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)}개월 전`;
    return `${Math.floor(diffDays / 365)}년 전`;
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>
          <HStack>
            <Icon as={FiClock} />
            <Text>시간 기반 일괄 로그아웃</Text>
          </HStack>
        </ModalHeader>
        <ModalCloseButton />
        
        <ModalBody>
          <VStack spacing={6} align="stretch">
            {/* 시간 조건 설정 */}
            <VStack spacing={4} align="stretch">
              <Text fontWeight="semibold">시간 조건 설정</Text>
              
              <FormControl>
                <FormLabel>
                  토큰 생성 시간 기준
                  <Text fontSize="sm" color="gray.600" fontWeight="normal" ml={2} as="span">
                    이 시간 이전에 생성된 토큰을 삭제
                  </Text>
                </FormLabel>
                <Input
                  type="datetime-local"
                  value={formData.created_before}
                  onChange={(e) => setFormData({ ...formData, created_before: e.target.value })}
                />
                {formData.created_before && (
                  <Text fontSize="sm" color="blue.600" mt={1}>
                    {formatDate(formData.created_before)} ({getRelativeTime(formData.created_before)}) 이전 생성 토큰 대상
                  </Text>
                )}
              </FormControl>

              <FormControl>
                <FormLabel>
                  마지막 사용 시간 기준
                  <Text fontSize="sm" color="gray.600" fontWeight="normal" ml={2} as="span">
                    이 시간 이전에 마지막 사용된 토큰을 삭제
                  </Text>
                </FormLabel>
                <Input
                  type="datetime-local"
                  value={formData.last_used_before}
                  onChange={(e) => setFormData({ ...formData, last_used_before: e.target.value })}
                />
                {formData.last_used_before && (
                  <Text fontSize="sm" color="blue.600" mt={1}>
                    {formatDate(formData.last_used_before)} ({getRelativeTime(formData.last_used_before)}) 이전 사용 토큰 대상
                  </Text>
                )}
              </FormControl>

              {!formData.created_before && !formData.last_used_before && (
                <Alert status="info" size="sm">
                  <AlertIcon />
                  <Text fontSize="sm">
                    생성 시간 또는 마지막 사용 시간 중 하나는 반드시 설정해야 합니다.
                  </Text>
                </Alert>
              )}
            </VStack>

            <Divider />

            {/* 토큰 유형 선택 */}
            <FormControl>
              <FormLabel>삭제할 토큰 유형</FormLabel>
              <CheckboxGroup
                value={formData.token_types}
                onChange={(values) => setFormData({ ...formData, token_types: values as string[] })}
              >
                <Stack spacing={3}>
                  <Checkbox value="access_token" colorScheme="blue">
                    <VStack align="start" spacing={0}>
                      <Text>액세스 토큰</Text>
                      <Text fontSize="sm" color="gray.600">
                        API 접근용 단기 토큰 (일반적으로 1시간 유효)
                      </Text>
                    </VStack>
                  </Checkbox>
                  <Checkbox value="refresh_token" colorScheme="blue">
                    <VStack align="start" spacing={0}>
                      <Text>리프레시 토큰</Text>
                      <Text fontSize="sm" color="gray.600">
                        액세스 토큰 갱신용 장기 토큰 (일반적으로 30일 유효)
                      </Text>
                    </VStack>
                  </Checkbox>
                </Stack>
              </CheckboxGroup>
            </FormControl>

            {/* 시뮬레이션 모드 */}
            <FormControl display="flex" alignItems="center">
              <FormLabel htmlFor="dry-run" mb="0" flex={1}>
                시뮬레이션 모드 (실제 삭제 안함)
              </FormLabel>
              <Switch
                id="dry-run"
                isChecked={formData.dry_run}
                onChange={(e) => setFormData({ ...formData, dry_run: e.target.checked })}
                colorScheme={formData.dry_run ? 'green' : 'red'}
              />
            </FormControl>

            {/* 로그아웃 사유 */}
            <FormControl isRequired>
              <FormLabel>로그아웃 사유</FormLabel>
              <Textarea
                placeholder="시간 기반 로그아웃 사유를 상세히 입력해주세요 (최소 10자)"
                value={formData.reason}
                onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                minLength={10}
                rows={3}
              />
              <Text fontSize="sm" color="gray.600" mt={1}>
                입력된 글자 수: {formData.reason.length}/10 (최소)
              </Text>
            </FormControl>

            {/* 영향 추정 */}
            {estimatedImpact && (
              <Box>
                <Text fontWeight="semibold" mb={3}>예상 영향 범위</Text>
                <VStack spacing={3}>
                  <HStack spacing={6} width="full">
                    <Stat>
                      <StatLabel>삭제될 토큰</StatLabel>
                      <StatNumber color="orange.500">
                        {estimatedImpact.estimated_affected_tokens || 0}개
                      </StatNumber>
                      <StatHelpText>
                        {formData.token_types.join(' + ')}
                      </StatHelpText>
                    </Stat>

                    <Stat>
                      <StatLabel>영향받을 세션</StatLabel>
                      <StatNumber color="red.500">
                        {estimatedImpact.estimated_affected_sessions || 0}개
                      </StatNumber>
                      <StatHelpText>종료될 활성 세션</StatHelpText>
                    </Stat>
                  </HStack>

                  {estimatedImpact.estimated_affected_tokens > 1000 && (
                    <Alert status="warning" size="sm">
                      <AlertIcon />
                      <Text fontSize="sm">
                        대량의 토큰이 삭제됩니다. 신중히 검토 후 실행하세요.
                      </Text>
                    </Alert>
                  )}
                </VStack>
              </Box>
            )}

            {/* 경고 메시지 */}
            {!formData.dry_run && (
              <Alert status="warning">
                <AlertIcon />
                <VStack align="start" spacing={1}>
                  <Text fontWeight="medium">실제 삭제 모드</Text>
                  <Text fontSize="sm">
                    조건에 맞는 토큰들이 영구적으로 삭제됩니다. 
                    해당 토큰을 사용하는 세션들은 즉시 무효화됩니다.
                  </Text>
                </VStack>
              </Alert>
            )}

            {/* 사용 사례 안내 */}
            <Box bg="blue.50" p={4} borderRadius="md" borderLeft="4px" borderColor="blue.500">
              <HStack align="start" spacing={3}>
                <Icon as={FiInfo} color="blue.500" mt={1} />
                <VStack align="start" spacing={2}>
                  <Text fontWeight="medium" color="blue.700">시간 기반 로그아웃 사용 사례</Text>
                  <VStack align="start" spacing={1}>
                    <Text fontSize="sm" color="blue.600">
                      • 장기간 미사용 토큰의 정기적인 정리 (보안 강화)
                    </Text>
                    <Text fontSize="sm" color="blue.600">
                      • 토큰 유효기간 정책 변경 후 기존 토큰 정리
                    </Text>
                    <Text fontSize="sm" color="blue.600">
                      • 보안 사고 이후 특정 시점 이전 토큰 일괄 무효화
                    </Text>
                    <Text fontSize="sm" color="blue.600">
                      • 데이터베이스 용량 최적화를 위한 오래된 토큰 정리
                    </Text>
                  </VStack>
                </VStack>
              </HStack>
            </Box>
          </VStack>
        </ModalBody>

        <ModalFooter>
          <HStack spacing={3}>
            <Button variant="ghost" onClick={handleClose} disabled={isSubmitting}>
              취소
            </Button>
            <Button
              colorScheme={formData.dry_run ? 'blue' : 'orange'}
              onClick={handleSubmit}
              isLoading={isSubmitting}
              loadingText={formData.dry_run ? '시뮬레이션 중...' : '로그아웃 실행 중...'}
              leftIcon={isSubmitting ? <Spinner size="sm" /> : <Icon as={formData.dry_run ? FiClock : FiTrash2} />}
            >
              {formData.dry_run ? '시뮬레이션 실행' : '시간 기반 로그아웃 실행'}
            </Button>
          </HStack>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default TimeBasedLogoutModal;