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
  PinInput,
  PinInputField,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  useToast,
  Spinner,
  Icon,
  Divider,
  Progress,
  Badge,
  Checkbox
} from '@chakra-ui/react';
import { FiAlertTriangle, FiShield, FiLock, FiKey } from 'react-icons/fi';

interface EmergencyLogoutModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: EmergencyLogoutData) => Promise<void>;
}

interface EmergencyLogoutData {
  confirm: string;
  exclude_admin_sessions: boolean;
  preserve_service_tokens: boolean;
  reason: string;
  authorized_by: string;
}

const EmergencyLogoutModal: React.FC<EmergencyLogoutModalProps> = ({
  isOpen,
  onClose,
  onSubmit
}) => {
  const [formData, setFormData] = useState<EmergencyLogoutData>({
    confirm: '',
    exclude_admin_sessions: true,
    preserve_service_tokens: true,
    reason: '',
    authorized_by: ''
  });

  const [step, setStep] = useState<number>(1); // 1: 정보입력, 2: 확인, 3: 2차인증, 4: 실행
  const [emergencyKey, setEmergencyKey] = useState<string>('');
  const [emergencyKeyRequested, setEmergencyKeyRequested] = useState<boolean>(false);
  const [confirmationCode, setConfirmationCode] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [estimatedImpact, setEstimatedImpact] = useState<any>(null);
  const [countdown, setCountdown] = useState<number>(0);
  const [hasAgreedToRisks, setHasAgreedToRisks] = useState<boolean>(false);
  
  const toast = useToast();
  const REQUIRED_CONFIRMATION = 'LOGOUT_ALL_USERS';

  // 카운트다운 타이머
  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [countdown]);

  // 모달이 열릴 때 초기화
  useEffect(() => {
    if (isOpen) {
      resetForm();
      estimateSystemImpact();
    }
  }, [isOpen]);

  const resetForm = () => {
    setFormData({
      confirm: '',
      exclude_admin_sessions: true,
      preserve_service_tokens: true,
      reason: '',
      authorized_by: ''
    });
    setStep(1);
    setEmergencyKey('');
    setEmergencyKeyRequested(false);
    setConfirmationCode('');
    setIsSubmitting(false);
    setEstimatedImpact(null);
    setCountdown(0);
    setHasAgreedToRisks(false);
  };

  const estimateSystemImpact = async () => {
    try {
      // 시스템 전체 통계 조회
      const response = await fetch('/api/admin/oauth/system-stats', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setEstimatedImpact(data);
      }
    } catch (error) {
      console.error('Failed to estimate system impact:', error);
      // 기본값 설정
      setEstimatedImpact({
        total_active_users: '추정 불가',
        total_active_sessions: '추정 불가',
        total_active_tokens: '추정 불가'
      });
    }
  };

  const requestEmergencyKey = async () => {
    try {
      const response = await fetch('/api/admin/oauth/batch-logout/request-emergency-key', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const result = await response.json();
        setEmergencyKeyRequested(true);
        setCountdown(300); // 5분 카운트다운
        
        toast({
          title: '긴급 키 전송됨',
          description: result.message || '등록된 연락처로 긴급 키를 전송했습니다.',
          status: 'success',
          duration: 5000,
          isClosable: true,
        });
      } else {
        throw new Error('긴급 키 요청에 실패했습니다.');
      }
    } catch (error) {
      toast({
        title: '오류 발생',
        description: error instanceof Error ? error.message : '긴급 키 요청에 실패했습니다.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const validateStep1 = () => {
    if (!formData.reason.trim() || formData.reason.length < 20) {
      toast({
        title: '입력 오류',
        description: '긴급 로그아웃 사유를 20자 이상 상세히 입력해주세요.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return false;
    }

    if (!formData.authorized_by.trim()) {
      toast({
        title: '입력 오류',
        description: '승인 권한자를 입력해주세요.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return false;
    }

    return true;
  };

  const validateStep2 = () => {
    if (!hasAgreedToRisks) {
      toast({
        title: '확인 필요',
        description: '긴급 로그아웃의 위험성에 대해 이해했음을 확인해주세요.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return false;
    }

    return true;
  };

  const validateStep3 = () => {
    if (!emergencyKey.trim()) {
      toast({
        title: '인증 오류',
        description: '긴급 키를 입력해주세요.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return false;
    }

    if (confirmationCode !== REQUIRED_CONFIRMATION) {
      toast({
        title: '확인 코드 오류',
        description: `정확한 확인 코드를 입력해주세요: ${REQUIRED_CONFIRMATION}`,
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return false;
    }

    return true;
  };

  const handleNext = () => {
    switch (step) {
      case 1:
        if (validateStep1()) setStep(2);
        break;
      case 2:
        if (validateStep2()) setStep(3);
        break;
      case 3:
        if (validateStep3()) setStep(4);
        break;
    }
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      // 최종 데이터 준비
      const submitData = {
        ...formData,
        confirm: REQUIRED_CONFIRMATION
      };

      // 긴급 키를 헤더에 추가해야 함 (실제 구현에서)
      const response = await fetch('/api/admin/oauth/batch-logout/emergency', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
          'Content-Type': 'application/json',
          'X-Emergency-Key': emergencyKey
        },
        body: JSON.stringify(submitData),
      });

      if (response.ok) {
        toast({
          title: '긴급 로그아웃 실행됨',
          description: '모든 사용자 세션이 종료되었습니다. 시스템 보안 팀에 알림이 전송되었습니다.',
          status: 'success',
          duration: 10000,
          isClosable: true,
        });
        
        handleClose();
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || '긴급 로그아웃 실행에 실패했습니다.');
      }
    } catch (error) {
      toast({
        title: '실행 실패',
        description: error instanceof Error ? error.message : '긴급 로그아웃 실행에 실패했습니다.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const renderStep1 = () => (
    <VStack spacing={6} align="stretch">
      <Alert status="error">
        <AlertIcon />
        <VStack align="start" spacing={1}>
          <Text fontWeight="medium">긴급 로그아웃 경고</Text>
          <Text fontSize="sm">
            이 작업은 시스템 내 모든 사용자의 모든 세션을 즉시 종료합니다. 
            보안 사고나 긴급 상황에서만 사용하세요.
          </Text>
        </VStack>
      </Alert>

      {/* 예상 영향 범위 */}
      {estimatedImpact && (
        <Box bg="red.50" p={4} borderRadius="md" borderLeft="4px" borderColor="red.500">
          <Text fontWeight="medium" color="red.700" mb={3}>
            예상 영향 범위
          </Text>
          <HStack spacing={6}>
            <Stat size="sm">
              <StatLabel color="red.600">활성 사용자</StatLabel>
              <StatNumber color="red.700">
                {estimatedImpact.total_active_users}명
              </StatNumber>
              <StatHelpText color="red.600">즉시 로그아웃됨</StatHelpText>
            </Stat>

            <Stat size="sm">
              <StatLabel color="red.600">활성 세션</StatLabel>
              <StatNumber color="red.700">
                {estimatedImpact.total_active_sessions}개
              </StatNumber>
              <StatHelpText color="red.600">모두 종료됨</StatHelpText>
            </Stat>

            <Stat size="sm">
              <StatLabel color="red.600">활성 토큰</StatLabel>
              <StatNumber color="red.700">
                {estimatedImpact.total_active_tokens}개
              </StatNumber>
              <StatHelpText color="red.600">모두 해지됨</StatHelpText>
            </Stat>
          </HStack>
        </Box>
      )}

      {/* 긴급 로그아웃 사유 */}
      <FormControl isRequired>
        <FormLabel>긴급 로그아웃 사유</FormLabel>
        <Textarea
          placeholder="보안 사고의 상세한 내용과 긴급 로그아웃이 필요한 이유를 구체적으로 입력해주세요 (최소 20자)"
          value={formData.reason}
          onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
          minLength={20}
          rows={4}
        />
        <Text fontSize="sm" color="gray.600" mt={1}>
          입력된 글자 수: {formData.reason.length}/20 (최소)
        </Text>
      </FormControl>

      {/* 승인 권한자 */}
      <FormControl isRequired>
        <FormLabel>승인 권한자</FormLabel>
        <Input
          placeholder="보안팀, CISO, 또는 승인 권한이 있는 부서/담당자명"
          value={formData.authorized_by}
          onChange={(e) => setFormData({ ...formData, authorized_by: e.target.value })}
        />
      </FormControl>

      {/* 옵션 설정 */}
      <VStack spacing={4} align="stretch">
        <FormControl display="flex" alignItems="center">
          <FormLabel htmlFor="exclude-admin" mb="0" flex={1}>
            관리자 세션 보호 (권장)
          </FormLabel>
          <Switch
            id="exclude-admin"
            isChecked={formData.exclude_admin_sessions}
            onChange={(e) => setFormData({ ...formData, exclude_admin_sessions: e.target.checked })}
            colorScheme="green"
          />
        </FormControl>

        <FormControl display="flex" alignItems="center">
          <FormLabel htmlFor="preserve-service" mb="0" flex={1}>
            서비스 토큰 보호 (권장)
          </FormLabel>
          <Switch
            id="preserve-service"
            isChecked={formData.preserve_service_tokens}
            onChange={(e) => setFormData({ ...formData, preserve_service_tokens: e.target.checked })}
            colorScheme="green"
          />
        </FormControl>
      </VStack>
    </VStack>
  );

  const renderStep2 = () => (
    <VStack spacing={6} align="stretch">
      <Alert status="warning">
        <AlertIcon />
        <Text fontWeight="medium">긴급 로그아웃 실행 전 최종 확인</Text>
      </Alert>

      {/* 입력된 정보 확인 */}
      <Box bg="gray.50" p={4} borderRadius="md">
        <VStack spacing={3} align="stretch">
          <HStack>
            <Text fontWeight="medium" minW="100px">사유:</Text>
            <Text fontSize="sm">{formData.reason}</Text>
          </HStack>
          <HStack>
            <Text fontWeight="medium" minW="100px">승인자:</Text>
            <Text fontSize="sm">{formData.authorized_by}</Text>
          </HStack>
          <HStack>
            <Text fontWeight="medium" minW="100px">옵션:</Text>
            <VStack align="start" spacing={1}>
              <HStack>
                <Badge colorScheme={formData.exclude_admin_sessions ? 'green' : 'red'}>
                  {formData.exclude_admin_sessions ? '관리자 세션 보호' : '관리자 세션 포함'}
                </Badge>
                <Badge colorScheme={formData.preserve_service_tokens ? 'green' : 'red'}>
                  {formData.preserve_service_tokens ? '서비스 토큰 보호' : '서비스 토큰 포함'}
                </Badge>
              </HStack>
            </VStack>
          </HStack>
        </VStack>
      </Box>

      {/* 위험성 고지 및 동의 */}
      <Box bg="red.50" p={4} borderRadius="md" borderLeft="4px" borderColor="red.500">
        <Text fontWeight="medium" color="red.700" mb={3}>
          긴급 로그아웃 위험성 고지
        </Text>
        <VStack align="start" spacing={2}>
          <Text fontSize="sm" color="red.600">
            • 모든 사용자가 강제로 로그아웃되어 업무 중단이 발생할 수 있습니다
          </Text>
          <Text fontSize="sm" color="red.600">
            • 진행 중인 작업이 저장되지 않고 손실될 수 있습니다
          </Text>
          <Text fontSize="sm" color="red.600">
            • 시스템 서비스의 일시적 중단이 발생할 수 있습니다
          </Text>
          <Text fontSize="sm" color="red.600">
            • 이 작업은 되돌릴 수 없으며 감사 로그에 영구 기록됩니다
          </Text>
        </VStack>
      </Box>

      <Checkbox
        isChecked={hasAgreedToRisks}
        onChange={(e) => setHasAgreedToRisks(e.target.checked)}
        colorScheme="red"
      >
        <Text fontSize="sm">
          위의 위험성을 충분히 이해했으며, 긴급한 보안 상황으로 인해 
          이러한 위험을 감수하고 긴급 로그아웃을 실행하는 것에 동의합니다.
        </Text>
      </Checkbox>
    </VStack>
  );

  const renderStep3 = () => (
    <VStack spacing={6} align="stretch">
      <Alert status="info">
        <AlertIcon />
        <Text>2차 인증이 필요합니다. 긴급 키를 요청하고 확인 코드를 입력하세요.</Text>
      </Alert>

      {/* 긴급 키 요청 */}
      <Box>
        <Text fontWeight="medium" mb={3}>1. 긴급 키 요청</Text>
        <HStack spacing={3}>
          <Button
            leftIcon={<Icon as={FiKey} />}
            onClick={requestEmergencyKey}
            isDisabled={emergencyKeyRequested || countdown > 0}
            colorScheme="blue"
            size="sm"
          >
            {emergencyKeyRequested ? '긴급 키 전송됨' : '긴급 키 요청'}
          </Button>
          {countdown > 0 && (
            <Badge colorScheme="blue">
              {formatTime(countdown)} 후 만료
            </Badge>
          )}
        </HStack>
        {emergencyKeyRequested && (
          <Text fontSize="sm" color="blue.600" mt={2}>
            등록된 이메일/SMS로 6자리 긴급 키를 전송했습니다.
          </Text>
        )}
      </Box>

      {/* 긴급 키 입력 */}
      <FormControl isRequired>
        <FormLabel>2. 긴급 키 입력</FormLabel>
        <Input
          placeholder="받은 6자리 긴급 키를 입력하세요"
          value={emergencyKey}
          onChange={(e) => setEmergencyKey(e.target.value)}
          maxLength={6}
          disabled={!emergencyKeyRequested}
        />
      </FormControl>

      {/* 확인 코드 입력 */}
      <FormControl isRequired>
        <FormLabel>3. 확인 코드 입력</FormLabel>
        <Input
          placeholder={`확인을 위해 다음을 정확히 입력하세요: ${REQUIRED_CONFIRMATION}`}
          value={confirmationCode}
          onChange={(e) => setConfirmationCode(e.target.value)}
          fontFamily="mono"
        />
        <Text fontSize="sm" color="gray.600" mt={1}>
          입력해야 할 확인 코드: <Text as="span" fontFamily="mono" fontWeight="bold">{REQUIRED_CONFIRMATION}</Text>
        </Text>
      </FormControl>
    </VStack>
  );

  const renderStep4 = () => (
    <VStack spacing={6} align="stretch">
      <Alert status="error">
        <AlertIcon />
        <VStack align="start" spacing={1}>
          <Text fontWeight="medium">긴급 로그아웃 실행 준비 완료</Text>
          <Text fontSize="sm">
            모든 인증이 완료되었습니다. 아래 버튼을 클릭하면 즉시 긴급 로그아웃이 실행됩니다.
          </Text>
        </VStack>
      </Alert>

      <Box bg="red.100" p={4} borderRadius="md" textAlign="center">
        <Icon as={FiAlertTriangle} color="red.500" boxSize="40px" mb={3} />
        <Text fontWeight="bold" color="red.700" fontSize="lg" mb={2}>
          최종 경고
        </Text>
        <Text color="red.600" fontSize="sm">
          이 작업을 실행하면 시스템 내 모든 사용자가 즉시 로그아웃됩니다.
          <br />
          정말로 계속하시겠습니까?
        </Text>
      </Box>
    </VStack>
  );

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="xl" closeOnOverlayClick={false}>
      <ModalOverlay />
      <ModalContent>
        <ModalHeader bg="red.500" color="white">
          <HStack>
            <Icon as={FiShield} />
            <Text>긴급 전체 로그아웃</Text>
            <Badge colorScheme="red" variant="solid">
              CRITICAL
            </Badge>
          </HStack>
        </ModalHeader>
        <ModalCloseButton color="white" />
        
        <ModalBody>
          <VStack spacing={4} align="stretch">
            {/* 진행 상태 */}
            <Box>
              <HStack justify="space-between" mb={2}>
                <Text fontSize="sm" fontWeight="medium">진행 단계</Text>
                <Text fontSize="sm" color="gray.600">{step}/4</Text>
              </HStack>
              <Progress value={(step / 4) * 100} colorScheme="red" size="sm" />
              <HStack justify="space-between" mt={1}>
                <Text fontSize="xs" color={step >= 1 ? 'red.600' : 'gray.400'}>정보입력</Text>
                <Text fontSize="xs" color={step >= 2 ? 'red.600' : 'gray.400'}>확인</Text>
                <Text fontSize="xs" color={step >= 3 ? 'red.600' : 'gray.400'}>2차인증</Text>
                <Text fontSize="xs" color={step >= 4 ? 'red.600' : 'gray.400'}>실행</Text>
              </HStack>
            </Box>

            <Divider />

            {/* 단계별 내용 */}
            {step === 1 && renderStep1()}
            {step === 2 && renderStep2()}
            {step === 3 && renderStep3()}
            {step === 4 && renderStep4()}
          </VStack>
        </ModalBody>

        <ModalFooter>
          <HStack spacing={3}>
            <Button
              variant="ghost"
              onClick={step > 1 ? () => setStep(step - 1) : handleClose}
              disabled={isSubmitting}
            >
              {step > 1 ? '이전' : '취소'}
            </Button>
            
            {step < 4 ? (
              <Button
                colorScheme="red"
                onClick={handleNext}
                disabled={isSubmitting}
              >
                다음
              </Button>
            ) : (
              <Button
                colorScheme="red"
                onClick={handleSubmit}
                isLoading={isSubmitting}
                loadingText="긴급 로그아웃 실행 중..."
                leftIcon={<Icon as={FiAlertTriangle} />}
              >
                긴급 로그아웃 실행
              </Button>
            )}
          </HStack>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default EmergencyLogoutModal;