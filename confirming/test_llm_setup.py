#!/usr/bin/env python3
"""
LLM 설정 테스트 스크립트
Azure OpenAI와 Ollama 연결을 테스트합니다.
"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

async def test_azure_openai():
    """Azure OpenAI 연결 테스트"""
    print("🔵 Azure OpenAI 연결 테스트 중...")
    
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    
    if not endpoint or not api_key:
        print("❌ Azure OpenAI 설정이 없습니다 (.env 파일 확인)")
        return False
    
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }
    
    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
    
    payload = {
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 10
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=10) as response:
                if response.status == 200:
                    print("✅ Azure OpenAI 연결 성공!")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Azure OpenAI 연결 실패 ({response.status}): {error_text}")
                    return False
    except Exception as e:
        print(f"❌ Azure OpenAI 연결 오류: {e}")
        return False

async def test_ollama():
    """Ollama 연결 테스트"""
    print("🟡 Ollama 연결 테스트 중...")
    
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    default_model = os.getenv("OLLAMA_DEFAULT_MODEL", "llama3.2")
    
    try:
        # 서비스 상태 확인
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/api/tags", timeout=5) as response:
                if response.status == 200:
                    result = await response.json()
                    models = [model["name"] for model in result.get("models", [])]
                    print(f"✅ Ollama 연결 성공! 설치된 모델: {models}")
                    
                    if default_model in [m.split(':')[0] for m in models]:
                        print(f"✅ 기본 모델 '{default_model}' 확인됨")
                    else:
                        print(f"⚠️  기본 모델 '{default_model}'가 설치되지 않았습니다")
                        print(f"   설치하려면: ollama pull {default_model}")
                    
                    return True
                else:
                    print(f"❌ Ollama 서비스 오류 ({response.status})")
                    return False
    except Exception as e:
        print(f"❌ Ollama 연결 오류: {e}")
        print("   Ollama가 실행 중인지 확인하세요: ollama serve")
        return False

async def test_simple_chat():
    """간단한 채팅 테스트"""
    print("\n🤖 간단한 LLM 채팅 테스트...")
    
    provider = os.getenv("DEFAULT_LLM_PROVIDER", "ollama")
    
    if provider == "azure":
        success = await test_azure_chat()
    else:
        success = await test_ollama_chat()
    
    return success

async def test_azure_chat():
    """Azure OpenAI 채팅 테스트"""
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }
    
    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
    
    payload = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Python에서 리스트를 역순으로 만드는 방법은?"}
        ],
        "max_tokens": 100,
        "temperature": 0.1
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=30) as response:
                if response.status == 200:
                    result = await response.json()
                    answer = result["choices"][0]["message"]["content"]
                    print(f"✅ Azure OpenAI 응답: {answer[:100]}...")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Azure OpenAI 채팅 실패: {error_text}")
                    return False
    except Exception as e:
        print(f"❌ Azure OpenAI 채팅 오류: {e}")
        return False

async def test_ollama_chat():
    """Ollama 채팅 테스트"""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_DEFAULT_MODEL", "llama3.2")
    
    payload = {
        "model": model,
        "prompt": "Python에서 리스트를 역순으로 만드는 방법은? 간단히 답해주세요.",
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 100
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{base_url}/api/generate", 
                                  json=payload, timeout=60) as response:
                if response.status == 200:
                    result = await response.json()
                    answer = result["response"]
                    print(f"✅ Ollama 응답: {answer[:100]}...")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Ollama 채팅 실패: {error_text}")
                    return False
    except Exception as e:
        print(f"❌ Ollama 채팅 오류: {e}")
        return False

async def main():
    """메인 테스트 실행"""
    print("🚀 Jupyter 플랫폼 LLM 설정 테스트 시작\n")
    
    # 환경 변수 확인
    print("📋 환경 설정 확인:")
    print(f"   DEFAULT_LLM_PROVIDER: {os.getenv('DEFAULT_LLM_PROVIDER', 'ollama')}")
    print(f"   AZURE_OPENAI_ENDPOINT: {'설정됨' if os.getenv('AZURE_OPENAI_ENDPOINT') else '없음'}")
    print(f"   OLLAMA_BASE_URL: {os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}")
    print()
    
    # 연결 테스트
    azure_ok = await test_azure_openai()
    ollama_ok = await test_ollama()
    
    # 채팅 테스트
    if azure_ok or ollama_ok:
        chat_ok = await test_simple_chat()
    else:
        chat_ok = False
    
    # 결과 요약
    print("\n📊 테스트 결과 요약:")
    print(f"   Azure OpenAI: {'✅ 정상' if azure_ok else '❌ 실패'}")
    print(f"   Ollama: {'✅ 정상' if ollama_ok else '❌ 실패'}")
    print(f"   채팅 테스트: {'✅ 정상' if chat_ok else '❌ 실패'}")
    
    if not (azure_ok or ollama_ok):
        print("\n⚠️  최소 하나의 LLM 제공자가 설정되어야 합니다.")
        print("   Azure OpenAI 또는 Ollama 설정을 확인해주세요.")
    elif chat_ok:
        print("\n🎉 LLM 설정이 완료되었습니다! Jupyter 플랫폼에서 AI 도우미를 사용할 수 있습니다.")

if __name__ == "__main__":
    asyncio.run(main()) 