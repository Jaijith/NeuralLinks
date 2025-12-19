"""
Test script to verify OpenAI gpt-5-nano API call format
"""
import os
import sys
from pathlib import Path

# Get API key from AWS Secrets Manager
try:
    import boto3
    secrets_client = boto3.client('secretsmanager', region_name='us-west-2')
    secret_name = '2n1/openai/api-key'
    response = secrets_client.get_secret_value(SecretId=secret_name)
    OPENAI_API_KEY = response['SecretString']
    print(f"✅ Retrieved OpenAI API key from Secrets Manager")
except Exception as e:
    print(f"❌ Could not retrieve API key: {e}")
    sys.exit(1)

from openai import OpenAI

# Initialize client
client = OpenAI(api_key=OPENAI_API_KEY)

def call_nano_model(prompt: str):
    """
    Calls GPT-5-nano using the responses API
    """
    response = client.responses.create(
        model="gpt-5-nano-2025-08-07",
        input=prompt
    )
    return response

if __name__ == "__main__":
    user_prompt = "Write a short, engaging social media post (2-3 sentences) about enjoying a sunset. Be casual and friendly."
    
    print(f"\n📝 Prompt: {user_prompt}\n")
    
    response = call_nano_model(user_prompt)
    
    print("=== Assistant Reply ===")
    print(response.output_text)
    
    print("\n=== Usage ===")
    print(f"Input tokens  : {response.usage.input_tokens}")
    print(f"Output tokens : {response.usage.output_tokens}")
    print(f"Total tokens  : {response.usage.total_tokens}")

