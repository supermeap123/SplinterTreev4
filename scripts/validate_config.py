"""
Script to validate Heroku configuration and test API keys.
Run this after deploying to verify everything is set up correctly.
"""
import os
import sys
import requests
import json
from dotenv import load_dotenv

# Load .env file if it exists (for local testing)
load_dotenv()

def test_openrouter_key():
    """Test OpenRouter API key validity"""
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        return False, "OpenRouter API key not found"
    
    try:
        response = requests.get(
            'https://openrouter.ai/api/v1/auth/key',
            headers={'Authorization': f'Bearer {api_key}'}
        )
        if response.status_code == 200:
            return True, "OpenRouter API key is valid"
        return False, f"OpenRouter API key invalid (Status: {response.status_code})"
    except Exception as e:
        return False, f"Error testing OpenRouter API key: {str(e)}"

def test_discord_token():
    """Test Discord token validity"""
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        return False, "Discord token not found"
    
    try:
        response = requests.get(
            'https://discord.com/api/v9/users/@me',
            headers={'Authorization': f'Bot {token}'}
        )
        if response.status_code == 200:
            return True, "Discord token is valid"
        return False, f"Discord token invalid (Status: {response.status_code})"
    except Exception as e:
        return False, f"Error testing Discord token: {str(e)}"

def test_webhooks():
    """Test Discord webhooks"""
    results = []
    i = 1
    while True:
        webhook_url = os.getenv(f'DISCORD_WEBHOOK_{i}')
        if not webhook_url:
            break
            
        try:
            response = requests.get(webhook_url)
            if response.status_code == 200:
                results.append((True, f"Webhook {i} is valid"))
            else:
                results.append((False, f"Webhook {i} invalid (Status: {response.status_code})"))
        except Exception as e:
            results.append((False, f"Error testing webhook {i}: {str(e)}"))
        
        i += 1
    
    return results

def check_security_config():
    """Check security-related configuration"""
    warnings = []
    
    # Check admin password
    if os.getenv('ADMIN_PASSWORD') == 'change_me_in_production':
        warnings.append("WARNING: Using default admin password")
    
    # Check debug mode
    if os.getenv('DEBUG', 'false').lower() == 'true':
        warnings.append("WARNING: Debug mode is enabled")
    
    # Check secret key
    if not os.getenv('SECRET_KEY'):
        warnings.append("WARNING: No custom SECRET_KEY set")
    
    return warnings

def main():
    """Main validation function"""
    print("Validating Heroku configuration...\n")
    
    # Required vars
    required_vars = [
        'DISCORD_TOKEN',
        'OPENROUTER_API_KEY',
        'ADMIN_USERNAME',
        'ADMIN_PASSWORD',
        'SECRET_KEY'
    ]
    
    # Check required vars
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required config vars:")
        for var in missing_vars:
            print(f"  - {var}")
        sys.exit(1)
    
    print("✅ All required config vars are set\n")
    
    # Test OpenRouter API key
    success, message = test_openrouter_key()
    print(f"{'✅' if success else '❌'} OpenRouter API: {message}")
    
    # Test Discord token
    success, message = test_discord_token()
    print(f"{'✅' if success else '❌'} Discord Token: {message}")
    
    # Test webhooks
    webhook_results = test_webhooks()
    if webhook_results:
        print("\nWebhook Status:")
        for success, message in webhook_results:
            print(f"{'✅' if success else '❌'} {message}")
    else:
        print("\n⚠️ No webhooks configured")
    
    # Check security config
    warnings = check_security_config()
    if warnings:
        print("\nSecurity Warnings:")
        for warning in warnings:
            print(f"⚠️ {warning}")
    
    print("\nConfiguration validation complete.")

if __name__ == '__main__':
    main()
