import React, { useState, useEffect, Fragment } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Plus, 
  Folder, 
  File, 
  Play, 
  Square, 
  Trash2, 
  Settings, 
  FolderOpen,
  FileText,
  Upload,
  Search,
  Filter,
  X,
  MoreHorizontal,
  Code,
  Terminal,
  RefreshCw,
  ExternalLink,
  Bell,
  Sparkles
} from 'lucide-react';
import { workspaceAPI } from '../services/api';
import { checkAuthAndRedirect, getAuthHeader, getAuthHeaderForUpload } from '../utils/auth';

interface Workspace {
  id: number;
  name: string;
  description?: string;
  path: string;
  is_active: boolean;
  jupyter_port?: number;
  jupyter_token?: string;
  owner_id: string;
  created_at: string;
  status?: 'running' | 'stopped' | 'starting' | 'error';
  jupyter_url?: string;
}

interface FileItem {
  name: string;
  is_directory: boolean;
  size?: number;
  modified_at?: string;
  path: string;
}

const WorkspacesPage: React.FC = () => {
  const navigate = useNavigate();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState<Workspace | null>(null);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [currentPath, setCurrentPath] = useState('');
  const [loading, setLoading] = useState(true);
  const [filesLoading, setFilesLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newWorkspace, setNewWorkspace] = useState({
    name: '',
    description: ''
  });


  useEffect(() => {
    loadWorkspaces();
  }, []);

  useEffect(() => {
    if (selectedWorkspace) {
      loadFiles(selectedWorkspace.id, currentPath);
    }
  }, [selectedWorkspace, currentPath]);

    const loadWorkspaces = async () => {
    try {
      setLoading(true);
      const response = await workspaceAPI.getWorkspaces();
      const workspacesData = response.data;
      
      // 각 워크스페이스의 Jupyter 상태 확인 및 상태 정보 추가
      const workspacesWithStatus = await Promise.all(
        workspacesData.map(async (workspace: any) => {
          try {
            // Jupyter 상태 확인 API 호출
            const statusResponse = await fetch(`/api/workspaces/${workspace.id}/status`, {
              headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
              }
            });
            
            if (statusResponse.ok) {
              const statusData = await statusResponse.json();
              return {
                ...workspace,
                status: statusData.is_running ? 'running' : 'stopped',
                jupyter_url: statusData.url
              };
            }
          } catch (error) {
            console.error(`워크스페이스 ${workspace.id} 상태 확인 실패:`, error);
          }
          
          // 상태 확인 실패 시 기본 상태
          return {
            ...workspace,
            status: workspace.jupyter_port ? 'stopped' : 'stopped'
          };
        })
      );
      
      setWorkspaces(workspacesWithStatus);
      if (workspacesWithStatus.length > 0 && !selectedWorkspace) {
        setSelectedWorkspace(workspacesWithStatus[0]);
      }
    } catch (error) {
      console.error('워크스페이스 로드 실패:', error);
      // 에러 발생 시 빈 배열로 설정
      setWorkspaces([]);
    } finally {
      setLoading(false);
    }
  };

  const loadFiles = async (workspaceId: number, path: string = '') => {
    try {
      setFilesLoading(true);
      const response = await fetch(`/api/files/${workspaceId}/list?path=${encodeURIComponent(path)}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setFiles(data.files);
        setCurrentPath(data.current_path || path);
      } else {
        console.error('파일 목록 로드 실패:', response.statusText);
        setFiles([]);
      }
    } catch (error) {
      console.error('파일 로드 실패:', error);
      setFiles([]);
    } finally {
      setFilesLoading(false);
    }
  };

  const createWorkspace = async () => {
    try {
      if (!newWorkspace.name.trim()) {
        alert('워크스페이스 이름을 입력해주세요.');
        return;
      }

      const response = await workspaceAPI.createWorkspace({
        name: newWorkspace.name,
        description: newWorkspace.description
      });
      
      // 생성된 워크스페이스에 상태 정보 추가
      const newWorkspaceWithStatus = {
        ...response.data,
        status: 'stopped' as const
      };
      
      setWorkspaces(prev => [...prev, newWorkspaceWithStatus]);
      setNewWorkspace({ name: '', description: '' });
      setShowCreateModal(false);
      
      // 새로 생성된 워크스페이스 선택
      setSelectedWorkspace(newWorkspaceWithStatus);
    } catch (error) {
      console.error('워크스페이스 생성 실패:', error);
      alert('워크스페이스 생성에 실패했습니다.');
    }
  };

  const startWorkspace = async (workspace: Workspace) => {
    try {
      // 상태를 즉시 'starting'으로 변경
      setWorkspaces(prev => prev.map(w => 
        w.id === workspace.id ? { ...w, status: 'starting' as const } : w
      ));
      
      const response = await fetch(`/api/workspaces/${workspace.id}/start`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        // 시작 성공 후 상태 업데이트
        setWorkspaces(prev => prev.map(w => 
          w.id === workspace.id ? { 
            ...w, 
            status: 'running' as const,
            jupyter_port: data.port,
            jupyter_url: data.url
          } : w
        ));
        
        // 선택된 워크스페이스도 업데이트
        if (selectedWorkspace?.id === workspace.id) {
          setSelectedWorkspace({
            ...selectedWorkspace,
            status: 'running',
            jupyter_port: data.port,
            jupyter_url: data.url
          });
        }
        
        // 자동으로 Jupyter Lab 새 창에서 열기
        if (data.url) {
          setTimeout(() => {
            window.open(data.url, '_blank', 'noopener,noreferrer');
          }, 1000); // 1초 후 열기 (서버가 완전히 시작될 시간을 주기 위해)
        }
      } else {
        // 시작 실패 시 상태를 다시 'stopped'로 변경
        setWorkspaces(prev => prev.map(w => 
          w.id === workspace.id ? { ...w, status: 'stopped' as const } : w
        ));
        const errorData = await response.json();
        alert(`Jupyter Lab 시작 실패: ${errorData.detail}`);
      }
    } catch (error) {
      console.error('워크스페이스 시작 실패:', error);
      // 에러 발생 시 상태를 다시 'stopped'로 변경
      setWorkspaces(prev => prev.map(w => 
        w.id === workspace.id ? { ...w, status: 'stopped' as const } : w
      ));
      alert('Jupyter Lab 시작에 실패했습니다.');
    }
  };

  const stopWorkspace = async (workspace: Workspace) => {
    try {
      const response = await fetch(`/api/workspaces/${workspace.id}/stop`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        // 중지 성공 후 상태 업데이트
        setWorkspaces(prev => prev.map(w => 
          w.id === workspace.id ? { 
            ...w, 
            status: 'stopped' as const,
            jupyter_port: undefined,
            jupyter_url: undefined
          } : w
        ));
        
        // 선택된 워크스페이스도 업데이트
        if (selectedWorkspace?.id === workspace.id) {
          setSelectedWorkspace({
            ...selectedWorkspace,
            status: 'stopped',
            jupyter_port: undefined,
            jupyter_url: undefined
          });
        }
      } else {
        const errorData = await response.json();
        alert(`Jupyter Lab 중지 실패: ${errorData.detail}`);
      }
    } catch (error) {
      console.error('워크스페이스 중지 실패:', error);
      alert('Jupyter Lab 중지에 실패했습니다.');
    }
  };

  const deleteWorkspace = async (workspace: Workspace) => {
    if (!window.confirm(`정말로 워크스페이스 "${workspace.name}"를 삭제하시겠습니까?`)) {
      return;
    }

    try {
      const response = await workspaceAPI.deleteWorkspace(workspace.id);
      
      if (response.status === 200) {
        setWorkspaces(prev => prev.filter(w => w.id !== workspace.id));
        if (selectedWorkspace?.id === workspace.id) {
          const remainingWorkspaces = workspaces.filter(w => w.id !== workspace.id);
          setSelectedWorkspace(remainingWorkspaces[0] || null);
        }
        alert('워크스페이스가 성공적으로 삭제되었습니다.');
      }
    } catch (error) {
      console.error('워크스페이스 삭제 실패:', error);
      alert('워크스페이스 삭제에 실패했습니다.');
    }
  };

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'running':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'starting':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'stopped':
        return 'bg-gray-100 text-gray-800 border-gray-200';
      case 'error':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusText = (status?: string) => {
    switch (status) {
      case 'running': return '실행 중';
      case 'starting': return '시작 중';
      case 'stopped': return '중지됨';
      case 'error': return '오류';
      default: return '중지됨';
    }
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes || bytes === 0) return '-';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const filteredWorkspaces = workspaces.filter(workspace =>
    workspace.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    workspace.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleFileClick = (file: FileItem) => {
    if (file.is_directory) {
      // 폴더 클릭 시 해당 폴더로 이동
      if (selectedWorkspace) {
        const newPath = currentPath ? `${currentPath}/${file.name}` : file.name;
        setCurrentPath(newPath);
        loadFiles(selectedWorkspace.id, newPath);
      }
    } else if (file.name.endsWith('.ipynb') && selectedWorkspace?.jupyter_url) {
      // Jupyter 노트북 파일 열기
      window.open(`${selectedWorkspace.jupyter_url}/notebooks/${file.path}`, '_blank');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-2 border-gray-200 border-t-gray-900 mx-auto mb-4"></div>
          <p className="text-gray-600">워크스페이스를 로딩하는 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* 액션 버튼 */}
        <div className="flex items-center justify-end mb-6">
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center space-x-2 px-4 py-2 bg-gray-900 text-white rounded-xl hover:bg-gray-800 transition-colors duration-200 shadow-sm hover:shadow-md"
          >
            <Plus className="w-4 h-4" />
            <span>새 워크스페이스</span>
          </button>
        </div>

        <div className="grid grid-cols-12 gap-6 h-[calc(100vh-200px)]">
          {/* 왼쪽: 워크스페이스 목록 */}
          <div className="col-span-4 bg-gray-50 rounded-2xl border border-gray-100 overflow-hidden">
            <div className="p-4 border-b border-gray-200 bg-white">
              <div className="flex items-center justify-between mb-3">
                <h2 className="font-semibold text-gray-900">워크스페이스 목록</h2>
                <button
                  onClick={loadWorkspaces}
                  className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <RefreshCw className="w-4 h-4 text-gray-500" />
                </button>
              </div>
              
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="워크스페이스 검색..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                />
              </div>
            </div>

            <div className="overflow-y-auto h-full">
              {filteredWorkspaces.length === 0 ? (
                <div className="p-6 text-center">
                  <Code className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                  <p className="text-gray-500 text-sm">워크스페이스가 없습니다</p>
                  <p className="text-gray-400 text-xs mt-1">새 워크스페이스를 생성해보세요</p>
                </div>
              ) : (
                <div className="p-3 space-y-2">
                  {filteredWorkspaces.map((workspace) => (
                    <div
                      key={workspace.id}
                      onClick={() => setSelectedWorkspace(workspace)}
                      className={`group p-3 rounded-xl cursor-pointer transition-all duration-200 ${
                        selectedWorkspace?.id === workspace.id
                          ? 'bg-white shadow-sm border border-gray-200'
                          : 'hover:bg-white/50'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2 mb-1">
                            <h3 className="font-medium text-gray-900 truncate text-sm">
                              {workspace.name}
                            </h3>
                            <span className={`px-2 py-0.5 text-xs font-medium rounded-full border ${getStatusColor(workspace.status)}`}>
                              {getStatusText(workspace.status)}
                            </span>
                          </div>
                          {workspace.description && (
                            <p className="text-xs text-gray-500 line-clamp-2 mb-2">
                              {workspace.description}
                            </p>
                          )}
                                                     <div className="flex items-center space-x-3 text-xs text-gray-400">
                             <span>생성: {new Date(workspace.created_at).toLocaleDateString()}</span>
                             {workspace.jupyter_port && (
                               <span>포트: {workspace.jupyter_port}</span>
                             )}
                           </div>
                        </div>
                        
                        <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          {workspace.status === 'running' ? (
                            <>
                              {workspace.jupyter_url && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    window.open(workspace.jupyter_url, '_blank');
                                  }}
                                  className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
                                  title="Jupyter 열기"
                                >
                                  <ExternalLink className="w-3.5 h-3.5 text-gray-500" />
                                </button>
                              )}
                                                             <button
                                 onClick={(e) => {
                                   e.stopPropagation();
                                   stopWorkspace(workspace);
                                 }}
                                 className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
                                 title="중지"
                               >
                                 <Square className="w-3.5 h-3.5 text-gray-500" />
                               </button>
                            </>
                          ) : (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                startWorkspace(workspace);
                              }}
                              className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
                              title="시작"
                            >
                              <Play className="w-3.5 h-3.5 text-gray-500" />
                            </button>
                          )}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteWorkspace(workspace);
                            }}
                            className="p-1.5 hover:bg-red-50 rounded-lg transition-colors"
                            title="삭제"
                          >
                            <Trash2 className="w-3.5 h-3.5 text-red-500" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* 오른쪽: 폴더 구조 */}
          <div className="col-span-8 bg-white rounded-2xl border border-gray-100 overflow-hidden">
            {selectedWorkspace ? (
              <>
                                 <div className="p-4 border-b border-gray-200 bg-gray-50">
                   <div className="flex items-center justify-between mb-3">
                     <div className="flex-1">
                       <h2 className="font-semibold text-gray-900">
                         {selectedWorkspace.name}
                       </h2>
                       <div className="flex items-center space-x-2 mt-1">
                         <button
                           onClick={() => {
                             setCurrentPath('');
                             if (selectedWorkspace) {
                               loadFiles(selectedWorkspace.id, '');
                             }
                           }}
                           className="text-sm text-blue-600 hover:text-blue-800 transition-colors"
                         >
                           루트
                         </button>
                         {currentPath && currentPath.split('/').map((part, index, arr) => {
                           const pathUpToHere = arr.slice(0, index + 1).join('/');
                           return (
                             <Fragment key={index}>
                               <span className="text-gray-400">/</span>
                               <button
                                 onClick={() => {
                                   setCurrentPath(pathUpToHere);
                                   if (selectedWorkspace) {
                                     loadFiles(selectedWorkspace.id, pathUpToHere);
                                   }
                                 }}
                                 className="text-sm text-blue-600 hover:text-blue-800 transition-colors"
                               >
                                 {part}
                               </button>
                                                            </Fragment>
                           );
                         })}
                       </div>
                     </div>
                    
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => loadFiles(selectedWorkspace.id, currentPath)}
                        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                        title="새로고침"
                      >
                        <RefreshCw className="w-4 h-4 text-gray-500" />
                      </button>
                                             <label className="flex items-center space-x-1 px-3 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer text-sm">
                         <Upload className="w-4 h-4 text-gray-500" />
                         <span className="text-gray-700">업로드</span>
                         <input 
                           type="file" 
                           className="hidden" 
                           multiple 
                           onChange={async (e) => {
                             if (e.target.files && selectedWorkspace) {
                               try {
                                 const formData = new FormData();
                                 Array.from(e.target.files).forEach(file => {
                                   formData.append('files', file);
                                 });
                                 
                                 const response = await fetch(`/api/files/${selectedWorkspace.id}/upload?path=${encodeURIComponent(currentPath)}`, {
                                   method: 'POST',
                                   headers: {
                                     'Authorization': `Bearer ${localStorage.getItem('token')}`
                                   },
                                   body: formData
                                 });
                                 
                                 if (response.ok) {
                                   // 파일 목록 새로고침
                                   loadFiles(selectedWorkspace.id, currentPath);
                                   alert('파일이 성공적으로 업로드되었습니다.');
                                 } else {
                                   const errorData = await response.json();
                                   alert(`파일 업로드 실패: ${errorData.detail}`);
                                 }
                               } catch (error) {
                                 console.error('파일 업로드 실패:', error);
                                 alert('파일 업로드에 실패했습니다.');
                               }
                               // 파일 입력 초기화
                               e.target.value = '';
                             }
                           }}
                         />
                       </label>
                    </div>
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto">
                  {filesLoading ? (
                    <div className="flex items-center justify-center h-64">
                      <div className="animate-spin rounded-full h-8 w-8 border-2 border-gray-200 border-t-gray-900"></div>
                    </div>
                  ) : files.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-64">
                      <Folder className="w-12 h-12 text-gray-300 mb-3" />
                      <p className="text-gray-500">폴더가 비어있습니다</p>
                      <p className="text-gray-400 text-sm mt-1">파일을 업로드하거나 새 노트북을 생성해보세요</p>
                    </div>
                  ) : (
                    <div className="p-4">
                      <div className="space-y-1">
                        {files.map((file, index) => (
                          <div
                            key={index}
                            onClick={() => handleFileClick(file)}
                            className="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg cursor-pointer transition-colors group"
                          >
                            <div className="flex items-center space-x-3">
                                                             <div className="flex items-center space-x-3">
                                 {file.is_directory ? (
                                   <FolderOpen className="w-5 h-5 text-blue-500" />
                                 ) : (
                                   <>
                                     {file.name.endsWith('.ipynb') ? (
                                       <Code className="w-5 h-5 text-orange-500" />
                                     ) : file.name.endsWith('.py') ? (
                                       <Code className="w-5 h-5 text-green-500" />
                                     ) : (
                                       <FileText className="w-5 h-5 text-gray-500" />
                                     )}
                                   </>
                                 )}
                               </div>
                              
                              <div>
                                <p className="font-medium text-gray-900 text-sm">
                                  {file.name}
                                </p>
                                <div className="flex items-center space-x-2 text-xs text-gray-500">
                                  {!file.is_directory && (
                                    <span>{formatFileSize(file.size)}</span>
                                  )}
                                  {file.modified_at && (
                                    <span>{new Date(file.modified_at).toLocaleDateString()}</span>
                                  )}
                                </div>
                              </div>
                            </div>
                            
                            <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                              {!file.is_directory && (
                                <>
                                                                     <button
                                     onClick={(e) => {
                                       e.stopPropagation();
                                       if (selectedWorkspace) {
                                         const downloadUrl = `/api/files/${selectedWorkspace.id}/download?file_path=${encodeURIComponent(file.path)}`;
                                         const link = document.createElement('a');
                                         link.href = downloadUrl;
                                         link.download = file.name;
                                         link.style.display = 'none';
                                         
                                         // Authorization 헤더를 추가하기 위해 fetch로 처리
                                         fetch(downloadUrl, {
                                           headers: {
                                             'Authorization': `Bearer ${localStorage.getItem('token')}`
                                           }
                                         })
                                         .then(response => response.blob())
                                         .then(blob => {
                                           const url = window.URL.createObjectURL(blob);
                                           link.href = url;
                                           document.body.appendChild(link);
                                           link.click();
                                           document.body.removeChild(link);
                                           window.URL.revokeObjectURL(url);
                                         })
                                         .catch(error => {
                                           console.error('파일 다운로드 실패:', error);
                                           alert('파일 다운로드에 실패했습니다.');
                                         });
                                       }
                                     }}
                                     className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
                                     title="다운로드"
                                   >
                                     <Terminal className="w-3.5 h-3.5 text-gray-500" />
                                   </button>
                                   <button
                                     onClick={async (e) => {
                                       e.stopPropagation();
                                       if (selectedWorkspace && window.confirm(`정말로 "${file.name}"를 삭제하시겠습니까?`)) {
                                         try {
                                           const response = await fetch(`/api/files/${selectedWorkspace.id}/delete?file_path=${encodeURIComponent(file.path)}`, {
                                             method: 'DELETE',
                                             headers: {
                                               'Authorization': `Bearer ${localStorage.getItem('token')}`
                                             }
                                           });
                                           
                                           if (response.ok) {
                                             // 파일 목록 새로고침
                                             loadFiles(selectedWorkspace.id, currentPath);
                                             alert('파일이 성공적으로 삭제되었습니다.');
                                           } else {
                                             const errorData = await response.json();
                                             alert(`파일 삭제 실패: ${errorData.detail}`);
                                           }
                                         } catch (error) {
                                           console.error('파일 삭제 실패:', error);
                                           alert('파일 삭제에 실패했습니다.');
                                         }
                                       }
                                     }}
                                     className="p-1.5 hover:bg-red-50 rounded-lg transition-colors"
                                     title="삭제"
                                   >
                                     <Trash2 className="w-3.5 h-3.5 text-red-500" />
                                   </button>
                                </>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <Code className="w-16 h-16 text-gray-200 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    워크스페이스를 선택하세요
                  </h3>
                  <p className="text-gray-500">
                    왼쪽에서 워크스페이스를 선택하면 파일 구조를 볼 수 있습니다
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 워크스페이스 생성 모달 */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-gray-900">새 워크스페이스 생성</h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-4 h-4 text-gray-500" />
              </button>
            </div>
            
            <div className="space-y-4 mb-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  워크스페이스 이름 *
                </label>
                <input
                  type="text"
                  value={newWorkspace.name}
                  onChange={(e) => setNewWorkspace(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300"
                  placeholder="예: 데이터 분석 프로젝트"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  설명 (선택사항)
                </label>
                <textarea
                  value={newWorkspace.description}
                  onChange={(e) => setNewWorkspace(prev => ({ ...prev, description: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-300 resize-none"
                  rows={3}
                  placeholder="워크스페이스에 대한 간단한 설명을 입력하세요"
                />
              </div>
            </div>
            
            <div className="flex items-center justify-end space-x-3">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              >
                취소
              </button>
              <button
                onClick={createWorkspace}
                className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
              >
                생성
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default WorkspacesPage;