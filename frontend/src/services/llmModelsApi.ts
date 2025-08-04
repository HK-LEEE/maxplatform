/**
 * LLM Models API Service
 * Unified API client for LLM model management with automatic token handling
 */

import api from './api'

export interface LLMModel {
  id: string
  model_name: string
  model_type: string
  model_id: string
  description?: string
  config: any
  owner_type: string
  owner_id: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface LLMModelPermission {
  id: string
  model_id: string
  grantee_type: 'USER' | 'GROUP'
  grantee_id: string
  granted_by: string
  created_at: string
  updated_at: string
}

export interface CreatePermissionRequest {
  model_id: string
  grantee_type: 'USER' | 'GROUP'
  grantee_id: string
}

/**
 * LLM Models API - Wave 1 Implementation
 * Provides centralized, token-managed API calls for LLM model operations
 */
export const llmModelsAPI = {
  /**
   * Get all LLM models
   */
  getModels: async (accessibleOnly: boolean = true): Promise<LLMModel[]> => {
    const response = await api.get('/llm-models', {
      params: { accessible_only: accessibleOnly }
    })
    return response.data
  },

  /**
   * Get specific LLM model by ID
   */
  getModel: async (modelId: string): Promise<LLMModel> => {
    const response = await api.get(`/llm-models/${modelId}`)
    return response.data
  },

  /**
   * Create new LLM model
   */
  createModel: async (modelData: Omit<LLMModel, 'id' | 'created_at' | 'updated_at'>): Promise<LLMModel> => {
    const response = await api.post('/llm-models', modelData)
    return response.data
  },

  /**
   * Update existing LLM model
   */
  updateModel: async (modelId: string, modelData: Partial<LLMModel>): Promise<LLMModel> => {
    const response = await api.put(`/llm-models/${modelId}`, modelData)
    return response.data
  },

  /**
   * Delete LLM model
   */
  deleteModel: async (modelId: string): Promise<void> => {
    await api.delete(`/llm-models/${modelId}`)
  },

  /**
   * Get permissions for a specific model
   */
  getModelPermissions: async (modelId: string): Promise<LLMModelPermission[]> => {
    const response = await api.get(`/llm-models/${modelId}/permissions`)
    return response.data
  },

  /**
   * Create permission for a model
   */
  createModelPermission: async (permission: CreatePermissionRequest): Promise<LLMModelPermission> => {
    const response = await api.post(`/llm-models/${permission.model_id}/permissions`, permission)
    return response.data
  },

  /**
   * Delete specific permission
   */
  deleteModelPermission: async (modelId: string, permissionId: string): Promise<void> => {
    await api.delete(`/llm-models/${modelId}/permissions/${permissionId}`)
  },

  /**
   * Batch operations for group permissions
   */
  
  /**
   * Get all models with their group permissions for a specific group
   */
  getGroupModelPermissions: async (groupId: string): Promise<{
    allModels: LLMModel[]
    assignedModels: LLMModel[]
    assignedModelIds: string[]
  }> => {
    try {
      // Get all models (accessible_only=false to see all models for admin)
      const allModels = await llmModelsAPI.getModels(false)
      
      const assignedModelIds: string[] = []
      const assignedModels: LLMModel[] = []
      
      // Check permissions for each model
      for (const model of allModels) {
        try {
          const permissions = await llmModelsAPI.getModelPermissions(model.id)
          const hasGroupPermission = permissions.some(p => 
            p.grantee_type === 'GROUP' && p.grantee_id === groupId
          )
          
          if (hasGroupPermission) {
            assignedModelIds.push(model.id)
            assignedModels.push(model)
          }
        } catch (error) {
          console.error(`Failed to check permissions for model ${model.id}:`, error)
          // Continue with other models even if one fails
        }
      }
      
      return {
        allModels,
        assignedModels,
        assignedModelIds
      }
    } catch (error) {
      console.error('Failed to get group model permissions:', error)
      throw error
    }
  },

  /**
   * Update group permissions for multiple models
   */
  updateGroupModelPermissions: async (
    groupId: string, 
    selectedModelIds: string[]
  ): Promise<void> => {
    try {
      // First, get current permissions and remove existing group permissions
      const { allModels } = await llmModelsAPI.getGroupModelPermissions(groupId)
      
      // Remove existing group permissions
      for (const model of allModels) {
        try {
          const permissions = await llmModelsAPI.getModelPermissions(model.id)
          const groupPermission = permissions.find(p => 
            p.grantee_type === 'GROUP' && p.grantee_id === groupId
          )
          
          if (groupPermission) {
            await llmModelsAPI.deleteModelPermission(model.id, groupPermission.id)
          }
        } catch (error) {
          console.error(`Failed to delete existing permission for model ${model.id}:`, error)
          // Continue with other models
        }
      }
      
      // Add new permissions for selected models
      for (const modelId of selectedModelIds) {
        try {
          await llmModelsAPI.createModelPermission({
            model_id: modelId,
            grantee_type: 'GROUP',
            grantee_id: groupId
          })
        } catch (error) {
          console.error(`Failed to create permission for model ${modelId}:`, error)
          // Continue with other models
        }
      }
    } catch (error) {
      console.error('Failed to update group model permissions:', error)
      throw error
    }
  }
}

// Default export for backward compatibility
export default llmModelsAPI