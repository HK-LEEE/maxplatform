import React from 'react'
import { Link } from 'react-router-dom'
import { BookOpenIcon, UsersIcon, ChartBarIcon, CogIcon } from 'lucide-react'

const HomePage = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* 헤더 */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <BookOpenIcon className="h-8 w-8 text-indigo-600" />
              <h1 className="ml-3 text-2xl font-bold text-gray-900">
                Manufacturing AI & DX
              </h1>
            </div>
            <div className="flex space-x-4">
              <Link
                to="/login"
                className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
              >
                로그인
              </Link>
              <Link
                to="/register"
                className="bg-indigo-600 text-white hover:bg-indigo-700 px-4 py-2 rounded-md text-sm font-medium"
              >
                회원가입
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* 메인 콘텐츠 */}
      <main>
        {/* 히어로 섹션 */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="text-center">
            <h1 className="text-4xl tracking-tight font-extrabold text-gray-900 sm:text-5xl md:text-6xl">
              <span className="block">데이터 분석을 위한</span>
              <span className="block text-indigo-600">Jupyter 플랫폼</span>
            </h1>
            <p className="mt-3 max-w-md mx-auto text-base text-gray-500 sm:text-lg md:mt-5 md:text-xl md:max-w-3xl">
              클라우드 기반 Jupyter Lab 환경에서 Python 데이터 분석을 시작하세요. 
              개인 워크스페이스, 파일 관리, 협업 기능을 모두 제공합니다.
            </p>
            <div className="mt-5 max-w-md mx-auto sm:flex sm:justify-center md:mt-8">
              <div className="rounded-md shadow">
                <Link
                  to="/register"
                  className="w-full flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 md:py-4 md:text-lg md:px-10"
                >
                  무료로 시작하기
                </Link>
              </div>
              <div className="mt-3 rounded-md shadow sm:mt-0 sm:ml-3">
                <Link
                  to="/login"
                  className="w-full flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-indigo-600 bg-white hover:bg-gray-50 md:py-4 md:text-lg md:px-10"
                >
                  로그인
                </Link>
              </div>
            </div>
          </div>
        </div>

        {/* 기능 소개 */}
        <div className="py-12 bg-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="lg:text-center">
              <h2 className="text-base text-indigo-600 font-semibold tracking-wide uppercase">
                주요 기능
              </h2>
              <p className="mt-2 text-3xl leading-8 font-extrabold tracking-tight text-gray-900 sm:text-4xl">
                데이터 분석을 더 쉽게
              </p>
              <p className="mt-4 max-w-2xl text-xl text-gray-500 lg:mx-auto">
                전문적인 데이터 분석 환경을 클라우드에서 바로 사용하세요
              </p>
            </div>

            <div className="mt-10">
              <dl className="space-y-10 md:space-y-0 md:grid md:grid-cols-2 md:gap-x-8 md:gap-y-10">
                <div className="relative">
                  <dt>
                    <div className="absolute flex items-center justify-center h-12 w-12 rounded-md bg-indigo-500 text-white">
                      <BookOpenIcon className="h-6 w-6" />
                    </div>
                    <p className="ml-16 text-lg leading-6 font-medium text-gray-900">
                      Jupyter Lab 환경
                    </p>
                  </dt>
                  <dd className="mt-2 ml-16 text-base text-gray-500">
                    최신 Jupyter Lab을 클라우드에서 바로 사용할 수 있습니다. 
                    Python, 데이터 과학 라이브러리가 미리 설치되어 있습니다.
                  </dd>
                </div>

                <div className="relative">
                  <dt>
                    <div className="absolute flex items-center justify-center h-12 w-12 rounded-md bg-indigo-500 text-white">
                      <UsersIcon className="h-6 w-6" />
                    </div>
                    <p className="ml-16 text-lg leading-6 font-medium text-gray-900">
                      개인 워크스페이스
                    </p>
                  </dt>
                  <dd className="mt-2 ml-16 text-base text-gray-500">
                    각 사용자마다 독립적인 워크스페이스를 제공합니다. 
                    프로젝트별로 환경을 분리하여 관리할 수 있습니다.
                  </dd>
                </div>

                <div className="relative">
                  <dt>
                    <div className="absolute flex items-center justify-center h-12 w-12 rounded-md bg-indigo-500 text-white">
                      <ChartBarIcon className="h-6 w-6" />
                    </div>
                    <p className="ml-16 text-lg leading-6 font-medium text-gray-900">
                      파일 관리
                    </p>
                  </dt>
                  <dd className="mt-2 ml-16 text-base text-gray-500">
                    데이터 파일 업로드, 다운로드, 관리 기능을 제공합니다. 
                    분석 결과를 쉽게 저장하고 공유할 수 있습니다.
                  </dd>
                </div>

                <div className="relative">
                  <dt>
                    <div className="absolute flex items-center justify-center h-12 w-12 rounded-md bg-indigo-500 text-white">
                      <CogIcon className="h-6 w-6" />
                    </div>
                    <p className="ml-16 text-lg leading-6 font-medium text-gray-900">
                      사용자 관리
                    </p>
                  </dt>
                  <dd className="mt-2 ml-16 text-base text-gray-500">
                    역할 기반 접근 제어와 그룹 관리 기능으로 
                    팀 단위의 협업을 지원합니다.
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        </div>

        {/* CTA 섹션 */}
        <div className="bg-indigo-700">
          <div className="max-w-2xl mx-auto text-center py-16 px-4 sm:py-20 sm:px-6 lg:px-8">
            <h2 className="text-3xl font-extrabold text-white sm:text-4xl">
              <span className="block">지금 바로 시작하세요</span>
            </h2>
            <p className="mt-4 text-lg leading-6 text-indigo-200">
              무료 계정을 만들고 클라우드에서 데이터 분석을 시작해보세요
            </p>
            <Link
              to="/register"
              className="mt-8 w-full inline-flex items-center justify-center px-5 py-3 border border-transparent text-base font-medium rounded-md text-indigo-600 bg-white hover:bg-indigo-50 sm:w-auto"
            >
              무료 회원가입
            </Link>
          </div>
        </div>
      </main>

      {/* 푸터 */}
      <footer className="bg-white">
        <div className="max-w-7xl mx-auto py-12 px-4 sm:px-6 md:flex md:items-center md:justify-between lg:px-8">
          <div className="flex justify-center space-x-6 md:order-2">
            <p className="text-gray-400 text-sm">
              © 2024 Jupyter Data Platform. All rights reserved.
            </p>
          </div>
          <div className="mt-8 md:mt-0 md:order-1">
            <div className="flex items-center">
              <BookOpenIcon className="h-6 w-6 text-indigo-600" />
              <span className="ml-2 text-gray-500 text-sm">
                Jupyter Data Platform
              </span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default HomePage 