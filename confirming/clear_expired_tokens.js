// 브라우저 콘솔에서 실행할 토큰 정리 스크립트
console.log('🧹 만료된 토큰 정리 시작...');

// localStorage 정리
localStorage.removeItem('token');
localStorage.removeItem('refreshToken');
localStorage.removeItem('access_token');
console.log('✅ localStorage 정리 완료');

// 모든 쿠키 정리
document.cookie.split(";").forEach(function(c) { 
    document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/"); 
});
console.log('✅ 쿠키 정리 완료');

// sessionStorage 정리
sessionStorage.clear();
console.log('✅ sessionStorage 정리 완료');

console.log('🎉 모든 토큰 정리 완료! 페이지를 새로고침하세요.');

// 3초 후 자동 새로고침
setTimeout(() => {
    console.log('🔄 페이지 새로고침...');
    window.location.reload();
}, 3000);