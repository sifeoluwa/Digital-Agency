#!/usr/bin/env python3
"""
JWT Secret Generator for Digital Agency Platform
Generates cryptographically secure JWT secrets for production use
"""

import secrets
import hashlib
import base64
from datetime import datetime

def generate_jwt_secret(length=64):
    """Generate a cryptographically secure JWT secret"""
    return secrets.token_urlsafe(length)

def generate_multiple_secrets(count=3):
    """Generate multiple JWT secrets to choose from"""
    secrets_list = []
    for i in range(count):
        secret = generate_jwt_secret()
        secrets_list.append(secret)
    return secrets_list

def main():
    print("🔐 JWT Secret Generator for Digital Agency Platform")
    print("=" * 60)
    print()
    
    print("Generated JWT Secrets (choose one):")
    print("-" * 40)
    
    secrets_list = generate_multiple_secrets(3)
    
    for i, secret in enumerate(secrets_list, 1):
        print(f"{i}. {secret}")
        print(f"   Length: {len(secret)} characters")
        print()
    
    print("💡 Security Tips:")
    print("- Use the longest secret (option 1 recommended)")
    print("- Never share this secret publicly")
    print("- Store it securely in your environment variables")
    print("- Generate a new secret for each environment")
    print()
    
    print("📝 Add to your .env file:")
    print(f'JWT_SECRET="{secrets_list[0]}"')
    print()
    
    print("Generated on:", datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"))

if __name__ == "__main__":
    main()