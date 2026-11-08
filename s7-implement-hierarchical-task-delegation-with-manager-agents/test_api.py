import requests
import json

# Test the API endpoint
BASE_URL = "http://localhost:8000"

# Sample expense request
expense_data = {
    "expense_type": "Travel",
    "amount": 1500,
    "policy_limit": 2000,
    "receipt_provided": "Yes",
    "business_purpose": "Q3 client meeting in NYC - 2 days"
}

print("Testing Expense Policy Validator API")
print("=" * 50)

# Test 1: Health check
print("\n1. Testing Health Check...")
try:
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Root endpoint
print("\n2. Testing Root Endpoint...")
try:
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")

# Test 3: Validate Expense - CORRECT WAY
print("\n3. Testing Expense Validation (POST with JSON body)...")
try:
    response = requests.post(
        f"{BASE_URL}/expense/validate",
        json=expense_data,  # This sends as Content-Type: application/json
        headers={"Content-Type": "application/json"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 50)
print("Test Complete!")
