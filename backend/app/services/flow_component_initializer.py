import logging
from typing import List
from sqlalchemy.orm import Session

from ..models.flow_studio import ComponentTemplate
from ..schemas.flow_studio import ComponentTemplateCreate

logger = logging.getLogger(__name__)

class FlowComponentInitializer:
    """Flow Studio 컴포넌트 템플릿 초기화 클래스"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_builtin_component_templates(self) -> List[ComponentTemplateCreate]:
        """내장 컴포넌트 템플릿 목록 반환"""
        return [
            # Chat Input
            ComponentTemplateCreate(
                name="Chat Input",
                category="Inputs",
                description="사용자로부터 채팅 입력을 받는 컴포넌트",
                icon="💬",
                component_type="input",
                config_schema={
                    "type": "object",
                    "properties": {
                        "placeholder": {
                            "type": "string",
                            "title": "플레이스홀더",
                            "default": "메시지를 입력하세요..."
                        }
                    }
                },
                input_schema={},
                output_schema={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "사용자 입력 메시지"}
                    }
                }
            ),
            
            # Prompt
            ComponentTemplateCreate(
                name="Prompt",
                category="Prompts",
                description="동적 변수를 지원하는 프롬프트 템플릿",
                icon="📋",
                component_type="processing",
                config_schema={
                    "type": "object",
                    "properties": {
                        "template": {
                            "type": "string",
                            "title": "프롬프트 템플릿",
                            "default": "Answer the user as if you were a GenAI expert, enthusiastic about helping them get started building something fresh."
                        }
                    }
                },
                input_schema={
                    "type": "object",
                    "properties": {
                        "user_input": {"type": "string", "description": "사용자 입력"}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "완성된 프롬프트"}
                    }
                }
            ),
            
            # OpenAI
            ComponentTemplateCreate(
                name="OpenAI",
                category="Models",
                description="OpenAI GPT 모델을 사용하는 컴포넌트",
                icon="🤖",
                component_type="model",
                config_schema={
                    "type": "object",
                    "properties": {
                        "model_name": {
                            "type": "string",
                            "title": "모델 이름",
                            "default": "gpt-4o-mini"
                        },
                        "temperature": {
                            "type": "number",
                            "title": "Temperature",
                            "default": 0.1
                        }
                    }
                },
                input_schema={
                    "type": "object",
                    "properties": {
                        "input": {"type": "string", "description": "모델에 전달할 입력"}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "모델 출력 텍스트"}
                    }
                }
            ),
            
            # Chat Output
            ComponentTemplateCreate(
                name="Chat Output",
                category="Outputs",
                description="채팅 형태로 출력을 표시하는 컴포넌트",
                icon="💭",
                component_type="output",
                config_schema={
                    "type": "object",
                    "properties": {
                        "show_timestamp": {
                            "type": "boolean",
                            "title": "타임스탬프 표시",
                            "default": True
                        }
                    }
                },
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "출력할 텍스트"}
                    }
                },
                output_schema={}
            )
        ]
    
    async def initialize_builtin_components(self) -> int:
        """내장 컴포넌트 템플릿들을 데이터베이스에 초기화"""
        try:
            # 기존 내장 컴포넌트 확인
            existing_count = self.db.query(ComponentTemplate)\
                .filter(ComponentTemplate.is_builtin == True).count()
            
            if existing_count > 0:
                logger.info(f"이미 {existing_count}개의 내장 컴포넌트가 존재합니다.")
                return existing_count
            
            # 내장 컴포넌트 템플릿 생성
            templates = self.get_builtin_component_templates()
            created_count = 0
            
            for template_data in templates:
                template = ComponentTemplate(**template_data.model_dump())
                self.db.add(template)
                created_count += 1
            
            self.db.commit()
            
            logger.info(f"내장 컴포넌트 {created_count}개 초기화 완료")
            return created_count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"내장 컴포넌트 초기화 실패: {e}")
            raise 