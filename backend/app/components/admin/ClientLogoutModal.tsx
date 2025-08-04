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
  Select,
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
  Input,
  Badge
} from '@chakra-ui/react';
import { FiSmartphone, FiInfo } from 'react-icons/fi';

interface ClientLogoutModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: ClientLogoutData) => Promise<void>;
}

interface ClientLogoutData {
  client_id: string;
  revoke_refresh_tokens: boolean;
  reason: string;
  created_before?: string;
  dry_run: boolean;
}

interface OAuthClient {
  client_id: string;
  client_name: string;
  client_type: string;
  active_sessions: number;
  active_tokens: number;
  last_used: string;
}

const ClientLogoutModal: React.FC<ClientLogoutModalProps> = ({
  isOpen,
  onClose,
  onSubmit
}) => {
  const [formData, setFormData] = useState<ClientLogoutData>({
    client_id: '',
    revoke_refresh_tokens: true,
    reason: '',
    created_before: '',
    dry_run: true
  });

  const [clients, setClients] = useState<OAuthClient[]>([]);
  const [isLoadingClients, setIsLoadingClients] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [estimatedImpact, setEstimatedImpact] = useState<any>(null);
  
  const toast = useToast();

  // 클라이언트 목록 로드
  useEffect(() => {
    if (isOpen) {
      loadClients();
    }
  }, [isOpen]);

  // 클라이언트 선택 시 영향 추정
  useEffect(() => {
    if (formData.client_id && isOpen) {
      estimateImpact();
    }
  }, [formData.client_id, formData.revoke_refresh_tokens, formData.created_before]);

  const loadClients = async () => {
    setIsLoadingClients(true);
    try {
      const response = await fetch('/api/admin/oauth/clients', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setClients(data);
      }
    } catch (error) {
      console.error('Failed to load clients:', error);
    } finally {
      setIsLoadingClients(false);
    }
  };

  const estimateImpact = async () => {
    if (!formData.client_id) return;

    try {
      const response = await fetch('/api/admin/oauth/batch-logout/client', {
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
    if (!formData.client_id || !formData.reason.trim()) {
      toast({
        title: '입력 오류',
        description: '클라이언트와 로그아웃 사유를 모두 입력해주세요.',
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
        created_before: formData.created_before || undefined
      };

      await onSubmit(submitData);
      
      toast({
        title: '클라이언트 로그아웃 요청 완료',
        description: formData.dry_run 
          ? '시뮬레이션이 완료되었습니다.' 
          : '클라이언트 로그아웃 작업이 시작되었습니다.',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      
      handleClose();
    } catch (error) {
      toast({
        title: '오류 발생',
        description: error instanceof Error ? error.message : '클라이언트 로그아웃 요청에 실패했습니다.',
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
      client_id: '',
      revoke_refresh_tokens: true,
      reason: '',
      created_before: '',
      dry_run: true
    });
    setEstimatedImpact(null);
    onClose();
  };

  const selectedClient = clients.find(c => c.client_id === formData.client_id);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('ko-KR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>
          <HStack>
            <Icon as={FiSmartphone} />
            <Text>클라이언트 기반 일괄 로그아웃</Text>
          </HStack>
        </ModalHeader>
        <ModalCloseButton />
        
        <ModalBody>
          <VStack spacing={6} align="stretch">
            {/* 클라이언트 선택 */}
            <FormControl isRequired>
              <FormLabel>대상 클라이언트</FormLabel>
              <Select
                placeholder="로그아웃할 클라이언트를 선택하세요"
                value={formData.client_id}
                onChange={(e) => setFormData({ ...formData, client_id: e.target.value })}
                disabled={isLoadingClients}
              >
                {isLoadingClients ? (
                  <option>클라이언트 로딩 중...</option>
                ) : (
                  clients.map((client) => (
                    <option key={client.client_id} value={client.client_id}>
                      {client.client_name} ({client.active_sessions}개 세션)
                    </option>
                  ))
                )}
              </Select>
              
              {selectedClient && (
                <Box mt={3} p={3} bg="gray.50" borderRadius="md">
                  <VStack spacing={2} align="stretch">
                    <HStack justify="space-between">
                      <Text fontSize="sm" fontWeight="medium">클라이언트 정보</Text>
                      <Badge colorScheme="blue">{selectedClient.client_type}</Badge>
                    </HStack>
                    <HStack justify="space-between">
                      <Text fontSize="sm" color="gray.600">활성 세션:</Text>
                      <Text fontSize="sm">{selectedClient.active_sessions}개</Text>
                    </HStack>
                    <HStack justify="space-between">
                      <Text fontSize="sm" color="gray.600">활성 토큰:</Text>
                      <Text fontSize="sm">{selectedClient.active_tokens}개</Text>
                    </HStack>
                    <HStack justify="space-between">
                      <Text fontSize="sm" color="gray.600">마지막 사용:</Text>
                      <Text fontSize="sm">{formatDate(selectedClient.last_used)}</Text>
                    </HStack>
                  </VStack>
                </Box>
              )}
            </FormControl>

            {/* 시간 필터 */}
            <FormControl>
              <FormLabel>
                시간 필터 (선택사항)
                <Text fontSize="sm" color="gray.600" fontWeight="normal" ml={2} as="span">
                  특정 시간 이전에 생성된 토큰만 해지
                </Text>
              </FormLabel>
              <Input
                type="datetime-local"
                value={formData.created_before}
                onChange={(e) => setFormData({ ...formData, created_before: e.target.value })}
              />
              {formData.created_before && (
                <Text fontSize="sm" color="blue.600" mt={1}>
                  {formatDate(formData.created_before)} 이전에 생성된 토큰만 해지됩니다.
                </Text>
              )}
            </FormControl>

            {/* 옵션 설정 */}
            <VStack spacing={4} align="stretch">
              <FormControl display="flex" alignItems="center">
                <FormLabel htmlFor="revoke-refresh" mb="0" flex={1}>
                  리프레시 토큰도 해지
                </FormLabel>
                <Switch
                  id="revoke-refresh"
                  isChecked={formData.revoke_refresh_tokens}
                  onChange={(e) => setFormData({ ...formData, revoke_refresh_tokens: e.target.checked })}
                  colorScheme="blue"
                />
              </FormControl>

              <FormControl display="flex" alignItems="center">
                <FormLabel htmlFor="dry-run" mb="0" flex={1}>
                  시뮬레이션 모드 (실제 로그아웃 안함)
                </FormLabel>
                <Switch
                  id="dry-run"
                  isChecked={formData.dry_run}
                  onChange={(e) => setFormData({ ...formData, dry_run: e.target.checked })}
                  colorScheme={formData.dry_run ? 'green' : 'red'}
                />
              </FormControl>
            </VStack>

            {/* 로그아웃 사유 */}
            <FormControl isRequired>
              <FormLabel>로그아웃 사유</FormLabel>
              <Textarea
                placeholder="클라이언트 로그아웃 사유를 상세히 입력해주세요 (최소 10자)"
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
                      <StatLabel>영향받을 세션</StatLabel>
                      <StatNumber color="blue.500">
                        {estimatedImpact.affected_sessions || 0}개
                      </StatNumber>
                      <StatHelpText>클라이언트 활성 세션</StatHelpText>
                    </Stat>

                    <Stat>
                      <StatLabel>해지될 토큰</StatLabel>
                      <StatNumber color="orange.500">
                        {estimatedImpact.affected_tokens || 0}개
                      </StatNumber>
                      <StatHelpText>
                        {formData.revoke_refresh_tokens ? '액세스 + 리프레시' : '액세스만'}
                      </StatHelpText>
                    </Stat>
                  </HStack>

                  {estimatedImpact.affected_sessions > 100 && (
                    <Alert status="warning" size="sm">
                      <AlertIcon />
                      <Text fontSize="sm">
                        대량 세션이 영향받습니다. 사용자들의 업무 중단을 고려하세요.
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
                  <Text fontWeight="medium">실제 로그아웃 모드</Text>
                  <Text fontSize="sm">
                    선택된 클라이언트의 모든 활성 세션이 즉시 종료됩니다.
                    사용자들은 해당 앱에서 다시 로그인해야 합니다.
                  </Text>
                </VStack>
              </Alert>
            )}

            {/* 사용 사례 안내 */}
            <Box bg="blue.50" p={4} borderRadius="md" borderLeft="4px" borderColor="blue.500">
              <HStack align="start" spacing={3}>
                <Icon as={FiInfo} color="blue.500" mt={1} />
                <VStack align="start" spacing={2}>
                  <Text fontWeight="medium" color="blue.700">클라이언트 로그아웃 사용 사례</Text>
                  <VStack align="start" spacing={1}>
                    <Text fontSize="sm" color="blue.600">
                      • 보안 취약점이 발견된 앱 버전의 강제 업데이트
                    </Text>
                    <Text fontSize="sm" color="blue.600">
                      • 악성 앱이나 무단 클라이언트의 접근 차단
                    </Text>
                    <Text fontSize="sm" color="blue.600">
                      • 특정 플랫폼(iOS/Android/Web)의 일시적 서비스 중단
                    </Text>
                    <Text fontSize="sm" color="blue.600">
                      • 클라이언트 설정 변경 후 강제 재로그인 요구
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
              leftIcon={isSubmitting ? <Spinner size="sm" /> : <Icon as={FiSmartphone} />}
            >
              {formData.dry_run ? '시뮬레이션 실행' : '클라이언트 로그아웃 실행'}
            </Button>
          </HStack>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default ClientLogoutModal;