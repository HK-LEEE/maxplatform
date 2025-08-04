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
  Divider
} from '@chakra-ui/react';
import { FiUsers, FiAlertTriangle } from 'react-icons/fi';

interface GroupLogoutModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: GroupLogoutData) => Promise<void>;
}

interface GroupLogoutData {
  group_id: string;
  include_subgroups: boolean;
  exclude_admin_users: boolean;
  reason: string;
  notify_users: boolean;
  dry_run: boolean;
}

interface Group {
  id: string;
  name: string;
  description?: string;
  user_count: number;
  subgroup_count: number;
}

const GroupLogoutModal: React.FC<GroupLogoutModalProps> = ({
  isOpen,
  onClose,
  onSubmit
}) => {
  const [formData, setFormData] = useState<GroupLogoutData>({
    group_id: '',
    include_subgroups: false,
    exclude_admin_users: true,
    reason: '',
    notify_users: true,
    dry_run: true
  });

  const [groups, setGroups] = useState<Group[]>([]);
  const [isLoadingGroups, setIsLoadingGroups] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [estimatedImpact, setEstimatedImpact] = useState<any>(null);
  
  const toast = useToast();

  // 그룹 목록 로드
  useEffect(() => {
    if (isOpen) {
      loadGroups();
    }
  }, [isOpen]);

  // 그룹 선택 시 영향 추정
  useEffect(() => {
    if (formData.group_id && isOpen) {
      estimateImpact();
    }
  }, [formData.group_id, formData.include_subgroups, formData.exclude_admin_users]);

  const loadGroups = async () => {
    setIsLoadingGroups(true);
    try {
      const response = await fetch('/api/admin/groups', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setGroups(data);
      }
    } catch (error) {
      console.error('Failed to load groups:', error);
    } finally {
      setIsLoadingGroups(false);
    }
  };

  const estimateImpact = async () => {
    if (!formData.group_id) return;

    try {
      const response = await fetch('/api/admin/oauth/batch-logout/group', {
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
    if (!formData.group_id || !formData.reason.trim()) {
      toast({
        title: '입력 오류',
        description: '그룹과 로그아웃 사유를 모두 입력해주세요.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    setIsSubmitting(true);
    try {
      await onSubmit(formData);
      
      toast({
        title: '그룹 로그아웃 요청 완료',
        description: formData.dry_run 
          ? '시뮬레이션이 완료되었습니다.' 
          : '그룹 로그아웃 작업이 시작되었습니다.',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      
      handleClose();
    } catch (error) {
      toast({
        title: '오류 발생',
        description: error instanceof Error ? error.message : '그룹 로그아웃 요청에 실패했습니다.',
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
      group_id: '',
      include_subgroups: false,
      exclude_admin_users: true,
      reason: '',
      notify_users: true,
      dry_run: true
    });
    setEstimatedImpact(null);
    onClose();
  };

  const selectedGroup = groups.find(g => g.id === formData.group_id);

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>
          <HStack>
            <Icon as={FiUsers} />
            <Text>그룹 기반 일괄 로그아웃</Text>
          </HStack>
        </ModalHeader>
        <ModalCloseButton />
        
        <ModalBody>
          <VStack spacing={6} align="stretch">
            {/* 그룹 선택 */}
            <FormControl isRequired>
              <FormLabel>대상 그룹</FormLabel>
              <Select
                placeholder="로그아웃할 그룹을 선택하세요"
                value={formData.group_id}
                onChange={(e) => setFormData({ ...formData, group_id: e.target.value })}
                disabled={isLoadingGroups}
              >
                {isLoadingGroups ? (
                  <option>그룹 로딩 중...</option>
                ) : (
                  groups.map((group) => (
                    <option key={group.id} value={group.id}>
                      {group.name} ({group.user_count}명)
                    </option>
                  ))
                )}
              </Select>
              {selectedGroup && (
                <Text fontSize="sm" color="gray.600" mt={2}>
                  {selectedGroup.description || '설명 없음'}
                </Text>
              )}
            </FormControl>

            {/* 옵션 설정 */}
            <VStack spacing={4} align="stretch">
              <FormControl display="flex" alignItems="center">
                <FormLabel htmlFor="include-subgroups" mb="0" flex={1}>
                  하위 그룹 포함
                </FormLabel>
                <Switch
                  id="include-subgroups"
                  isChecked={formData.include_subgroups}
                  onChange={(e) => setFormData({ ...formData, include_subgroups: e.target.checked })}
                />
              </FormControl>

              <FormControl display="flex" alignItems="center">
                <FormLabel htmlFor="exclude-admin" mb="0" flex={1}>
                  관리자 계정 제외
                </FormLabel>
                <Switch
                  id="exclude-admin"
                  isChecked={formData.exclude_admin_users}
                  onChange={(e) => setFormData({ ...formData, exclude_admin_users: e.target.checked })}
                />
              </FormControl>

              <FormControl display="flex" alignItems="center">
                <FormLabel htmlFor="notify-users" mb="0" flex={1}>
                  사용자에게 알림 전송
                </FormLabel>
                <Switch
                  id="notify-users"
                  isChecked={formData.notify_users}
                  onChange={(e) => setFormData({ ...formData, notify_users: e.target.checked })}
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
                placeholder="그룹 로그아웃 사유를 상세히 입력해주세요 (최소 10자)"
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
                      <StatLabel>영향받을 사용자</StatLabel>
                      <StatNumber color="blue.500">
                        {estimatedImpact.estimated_affected_users || 0}명
                      </StatNumber>
                      <StatHelpText>선택된 그룹 내 사용자</StatHelpText>
                    </Stat>

                    <Stat>
                      <StatLabel>해지될 토큰</StatLabel>
                      <StatNumber color="orange.500">
                        {estimatedImpact.estimated_affected_tokens || 0}개
                      </StatNumber>
                      <StatHelpText>액세스 + 리프레시 토큰</StatHelpText>
                    </Stat>
                  </HStack>

                  {estimatedImpact.estimated_affected_users > 50 && (
                    <Alert status="warning" size="sm">
                      <AlertIcon />
                      <Text fontSize="sm">
                        대량 로그아웃 작업입니다. 신중히 검토 후 실행하세요.
                      </Text>
                    </Alert>
                  )}
                </VStack>
              </Box>
            )}

            {/* 경고 메시지 */}
            {!formData.dry_run && (
              <Alert status="error">
                <AlertIcon />
                <VStack align="start" spacing={1}>
                  <Text fontWeight="medium">실제 로그아웃 모드</Text>
                  <Text fontSize="sm">
                    이 작업은 되돌릴 수 없습니다. 선택된 그룹의 모든 사용자가 강제로 로그아웃됩니다.
                  </Text>
                </VStack>
              </Alert>
            )}

            <Divider />

            {/* 보안 권고사항 */}
            <Box bg="blue.50" p={4} borderRadius="md" borderLeft="4px" borderColor="blue.500">
              <Text fontWeight="medium" color="blue.700" mb={2}>
                보안 권고사항
              </Text>
              <VStack align="start" spacing={1}>
                <Text fontSize="sm" color="blue.600">
                  • 그룹 로그아웃은 보안 정책 위반이나 보안 사고 대응 시에만 사용하세요
                </Text>
                <Text fontSize="sm" color="blue.600">
                  • 실행 전 반드시 시뮬레이션으로 영향 범위를 확인하세요
                </Text>
                <Text fontSize="sm" color="blue.600">
                  • 대량 로그아웃 시 사용자들에게 사전 공지를 권장합니다
                </Text>
              </VStack>
            </Box>
          </VStack>
        </ModalBody>

        <ModalFooter>
          <HStack spacing={3}>
            <Button variant="ghost" onClick={handleClose} disabled={isSubmitting}>
              취소
            </Button>
            <Button
              colorScheme={formData.dry_run ? 'blue' : 'red'}
              onClick={handleSubmit}
              isLoading={isSubmitting}
              loadingText={formData.dry_run ? '시뮬레이션 중...' : '로그아웃 실행 중...'}
              leftIcon={isSubmitting ? <Spinner size="sm" /> : <Icon as={formData.dry_run ? FiUsers : FiAlertTriangle} />}
            >
              {formData.dry_run ? '시뮬레이션 실행' : '그룹 로그아웃 실행'}
            </Button>
          </HStack>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default GroupLogoutModal;