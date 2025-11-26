#!/usr/bin/env python3
"""
Helper script to generate secure random keys for .env file.
"""
import secrets

print("=" * 60)
print("Tribe Backend - Secure Key Generator")
print("=" * 60)
print()
print("Copy these values to your .env file:")
print()
print(f"SECRET_KEY={secrets.token_urlsafe(32)}")
print(f"JWT_SECRET_KEY={secrets.token_urlsafe(32)}")
print()
print("=" * 60)
print("⚠️  Keep these keys secure and never commit them to version control!")
print("=" * 60)

