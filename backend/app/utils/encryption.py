"""
Encryption utilities for sensitive data protection
Used primarily for encrypting RSA private keys in the database
"""
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from ..config import settings

class KeyEncryption:
    """Utility for encrypting/decrypting sensitive keys"""
    
    def __init__(self):
        # Derive encryption key from application secret
        # In production, consider using a separate encryption key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'maxplatform_oidc_key_encryption_salt_2025',  # Static salt for deterministic key derivation
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(
            kdf.derive(settings.secret_key.encode())
        )
        self.cipher = Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt string data
        
        Args:
            data: Plain text string to encrypt
            
        Returns:
            Base64 encoded encrypted string
        """
        if not data:
            raise ValueError("Cannot encrypt empty data")
            
        encrypted_bytes = self.cipher.encrypt(data.encode())
        return encrypted_bytes.decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt string data
        
        Args:
            encrypted_data: Base64 encoded encrypted string
            
        Returns:
            Decrypted plain text string
        """
        if not encrypted_data:
            raise ValueError("Cannot decrypt empty data")
            
        try:
            decrypted_bytes = self.cipher.decrypt(encrypted_data.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt data: {str(e)}")

# Global instance for application-wide use
key_encryption = KeyEncryption()

def encrypt_data(data: str) -> str:
    """
    Encrypt sensitive data using application encryption key
    
    Args:
        data: Plain text to encrypt
        
    Returns:
        Encrypted string
    """
    return key_encryption.encrypt(data)

def decrypt_data(encrypted_data: str) -> str:
    """
    Decrypt sensitive data using application encryption key
    
    Args:
        encrypted_data: Encrypted string
        
    Returns:
        Decrypted plain text
    """
    return key_encryption.decrypt(encrypted_data)