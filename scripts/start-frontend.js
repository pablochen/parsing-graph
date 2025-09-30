#!/usr/bin/env node
/**
 * 프론트엔드 개발 서버 시작 스크립트
 */
const { execSync, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const PROJECT_ROOT = path.resolve(__dirname, '..');
const FRONTEND_DIR = path.join(PROJECT_ROOT, 'frontend');

function checkRequirements() {
    console.log('🔍 필수 요구사항 확인 중...');
    
    // Node.js 버전 확인
    const nodeVersion = process.version;
    const majorVersion = parseInt(nodeVersion.slice(1).split('.')[0]);
    
    if (majorVersion < 18) {
        console.log('❌ Node.js 18 이상이 필요합니다.');
        return false;
    }
    
    // package.json 확인
    const packageJsonPath = path.join(FRONTEND_DIR, 'package.json');
    if (!fs.existsSync(packageJsonPath)) {
        console.log('❌ frontend/package.json 파일이 없습니다.');
        return false;
    }
    
    // node_modules 확인
    const nodeModulesPath = path.join(FRONTEND_DIR, 'node_modules');
    if (!fs.existsSync(nodeModulesPath)) {
        console.log('📦 의존성 설치 중...');
        try {
            process.chdir(FRONTEND_DIR);
            execSync('npm install', { stdio: 'inherit' });
            console.log('✅ 의존성 설치 완료');
        } catch (error) {
            console.log('❌ 의존성 설치 실패:', error.message);
            return false;
        }
    }
    
    console.log('✅ 필수 요구사항 확인 완료');
    return true;
}

function startDevServer() {
    console.log('🚀 React 개발 서버 시작 중...');
    
    process.chdir(FRONTEND_DIR);
    
    // 환경변수 설정
    const env = {
        ...process.env,
        VITE_API_BASE_URL: process.env.VITE_API_BASE_URL || '/api/v1',
        PORT: '3000'
    };
    
    const devServer = spawn('npm', ['run', 'dev'], {
        stdio: 'inherit',
        env: env
    });
    
    devServer.on('error', (error) => {
        console.log('❌ 개발 서버 시작 실패:', error.message);
        process.exit(1);
    });
    
    process.on('SIGINT', () => {
        console.log('\n👋 개발 서버 종료');
        devServer.kill('SIGINT');
        process.exit(0);
    });
    
    return devServer;
}

function main() {
    console.log('=== 보험약관 PDF 파싱 시스템 프론트엔드 ===');
    console.log();
    
    // 요구사항 확인
    if (!checkRequirements()) {
        process.exit(1);
    }
    
    console.log('⚠️  백엔드 서버가 실행 중인지 확인하세요 (http://localhost:8000)');
    console.log();
    
    // 개발 서버 시작
    const server = startDevServer();
    
    // 성공 메시지 (약간의 지연 후)
    setTimeout(() => {
        console.log();
        console.log('✅ 프론트엔드 서버 실행 중:');
        console.log('   🌐 Local:   http://localhost:3000/');
        console.log('   📱 Network: http://0.0.0.0:3000/');
        console.log();
        console.log('💡 개발 팁:');
        console.log('   - Ctrl+C로 서버 종료');
        console.log('   - 파일 변경 시 자동 새로고침');
        console.log('   - API는 프록시로 백엔드에 연결됨');
    }, 3000);
}

if (require.main === module) {
    main();
}

module.exports = {
    checkRequirements,
    startDevServer
};