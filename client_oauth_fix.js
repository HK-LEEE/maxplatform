// 🔧 수정된 클라이언트 OAuth 메시지 처리 로직

// Handle PostMessage from popup
private handleOAuthMessage(event: MessageEvent<OAuthMessage>, resolve: Function, reject: Function): void {
  // 기존 origin 검증 로직 유지...
  const trustedOrigins = this.getTrustedOrigins();
  const validationResult = this.validateMessageOrigin(event.origin, event.data);
  
  if (!validationResult.isValid) {
    console.warn('🚨 SECURITY: Message rejected from untrusted origin');
    return;
  }
  
  if (!this.validateMessageStructure(event.data)) {
    console.warn('🚨 SECURITY: Invalid message structure detected');
    return;
  }

  console.log('📨 Received OAuth message:', event.data);
  
  // 🔧 수정: 단순화된 메시지 구조 처리
  let messageData: OAuthMessageFlat;
  let actualMessageType: string;
  
  // Handle nested OAUTH_MESSAGE structure from auth server
  if (event.data.type === 'OAUTH_MESSAGE' && 'data' in event.data) {
    console.log('📦 Processing nested OAuth message from auth server');
    const nestedMessage = event.data as OAuthMessageNested;
    const innerData = nestedMessage.data;
    
    // 🔧 CRITICAL FIX: 새로운 플로우에서는 OAUTH_SUCCESS만 처리
    if (innerData.type === 'OAUTH_SUCCESS' || innerData.type === 'OAUTH_ERROR' || innerData.type === 'OAUTH_ACK') {
      // 표준 메시지 타입 직접 처리
      messageData = {
        type: innerData.type,
        tokenData: innerData.tokenData,
        token: innerData.token,
        error: innerData.error,
        error_description: innerData.error_description
      };
      actualMessageType = innerData.type;
    } 
    // 🚨 DEPRECATED: 더 이상 사용되지 않는 메시지 타입들
    else if (innerData.type === 'OAUTH_LOGIN_SUCCESS_CONTINUE' || 
             innerData.type === 'OAUTH_ALREADY_AUTHENTICATED') {
      console.warn(`⚠️ DEPRECATED: Received deprecated message type '${innerData.type}'`);
      console.warn('🔴 This message type should not be sent in the new OAuth flow');
      console.warn('📋 Expected flow: OAuth authorize → callback → OAUTH_SUCCESS');
      
      // 명확한 에러 메시지로 rejected
      this.cleanup();
      reject(new Error(
        `Deprecated OAuth message type received: ${innerData.type}.\n\n` +
        `The OAuth server has been updated to use a standard flow:\n` +
        `1. All users (new and existing) go through OAuth authorize\n` +
        `2. Server generates authorization code\n` +
        `3. Callback exchanges code for token\n` +
        `4. OAUTH_SUCCESS message is sent\n\n` +
        `Please ensure the OAuth server is updated to the new flow.`
      ));
      return;
    } else {
      // 알 수 없는 메시지 타입
      console.error('Unknown inner OAuth message type:', innerData.type);
      this.cleanup();
      reject(new Error(`Unknown OAuth message type: ${innerData.type}`));
      return;
    }
  } 
  // Flat structure handling (backward compatibility)
  else if (event.data.type === 'OAUTH_SUCCESS' || 
           event.data.type === 'OAUTH_ERROR' || 
           event.data.type === 'OAUTH_ACK') {
    messageData = event.data as OAuthMessageFlat;
    actualMessageType = messageData.type;
  } else {
    console.error('Invalid OAuth message type:', event.data.type);
    this.cleanup();
    reject(new Error(`Invalid OAuth message type: ${event.data.type}`));
    return;
  }
  
  this.messageReceived = true;

  // 🔧 단순화된 메시지 처리
  if (actualMessageType === 'OAUTH_SUCCESS') {
    console.log('✅ OAUTH_SUCCESS message received, processing...');
    
    // Send acknowledgment back to popup
    if (event.source && typeof event.source.postMessage === 'function') {
      try {
        console.log('📤 Sending acknowledgment to popup...');
        (event.source as Window).postMessage({ type: 'OAUTH_ACK' }, event.origin === 'null' ? '*' : event.origin);
        console.log('✅ Acknowledgment sent to popup');
      } catch (e) {
        console.error('Failed to send acknowledgment to popup:', e);
      }
    }
    
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }
    
    this.cleanup();
    console.log('🧹 Cleanup completed');
    
    // 토큰 데이터 처리
    if (messageData.tokenData) {
      console.log('📦 Resolving with full token data');
      resolve(messageData.tokenData);
    } else if (messageData.token) {
      console.log('📦 Resolving with access token only');
      resolve({
        access_token: messageData.token,
        token_type: 'Bearer',
        expires_in: 3600,
        scope: this.scopes.join(' ')
      });
    } else {
      console.error('❌ No token data in OAUTH_SUCCESS message');
      reject(new Error('No token data received in OAUTH_SUCCESS message'));
    }
  } else if (actualMessageType === 'OAUTH_ERROR') {
    // Send acknowledgment for error case
    if (event.source && typeof event.source.postMessage === 'function') {
      try {
        (event.source as Window).postMessage({ type: 'OAUTH_ACK' }, event.origin === 'null' ? '*' : event.origin);
      } catch (e) {
        console.error('Failed to send error acknowledgment:', e);
      }
    }
    
    this.cleanup();
    
    console.log('❌ OAuth error received:', messageData.error);
    reject(new Error(messageData.error || 'OAuth authentication failed'));
  }
}

// 🔧 수정된 BroadcastChannel 메시지 처리 (동일한 로직 적용)
private handleBroadcastMessage(event: MessageEvent, resolve: Function, reject: Function, broadcastChannel: BroadcastChannel | null): void {
  if (event.data.type === 'OAUTH_SUCCESS') {
    console.log('✅ OAuth success via BroadcastChannel');
    this.messageReceived = true;
    
    // Send acknowledgment back via BroadcastChannel
    if (broadcastChannel) {
      try {
        console.log('📤 Sending acknowledgment via BroadcastChannel...');
        broadcastChannel.postMessage({ type: 'OAUTH_ACK' });
        console.log('✅ Acknowledgment sent via BroadcastChannel');
      } catch (e) {
        console.error('Failed to send BroadcastChannel acknowledgment:', e);
      }
    }
    
    this.cleanup();
    broadcastChannel?.close();
    
    if (event.data.tokenData) {
      resolve(event.data.tokenData);
    } else if (event.data.token) {
      resolve({
        access_token: event.data.token,
        token_type: 'Bearer',
        expires_in: 3600,
        scope: this.scopes.join(' ')
      });
    } else {
      reject(new Error('No token data in BroadcastChannel OAUTH_SUCCESS message'));
    }
  } else if (event.data.type === 'OAUTH_ERROR') {
    console.log('❌ OAuth error via BroadcastChannel');
    
    // Send acknowledgment for error case
    if (broadcastChannel) {
      try {
        broadcastChannel.postMessage({ type: 'OAUTH_ACK' });
      } catch (e) {
        console.error('Failed to send error acknowledgment via BroadcastChannel:', e);
      }
    }
    
    this.cleanup();
    broadcastChannel?.close();
    
    console.log('❌ BroadcastChannel OAuth error:', event.data.error);
    reject(new Error(event.data.error || 'OAuth authentication failed'));
  }
  // 🚨 DEPRECATED: 더 이상 처리하지 않는 메시지 타입들
  else if (event.data.type === 'OAUTH_LOGIN_SUCCESS_CONTINUE' || 
           event.data.type === 'OAUTH_ALREADY_AUTHENTICATED') {
    console.warn(`⚠️ DEPRECATED: Received deprecated BroadcastChannel message type '${event.data.type}'`);
    console.warn('🔴 This message type should not be sent in the new OAuth flow');
    
    this.cleanup();
    broadcastChannel?.close();
    
    reject(new Error(
      `Deprecated OAuth BroadcastChannel message type: ${event.data.type}.\n` +
      `Please update the OAuth server to use the new standard flow.`
    ));
  }
}