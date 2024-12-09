import requests
import json
import sys
import traceback

def test_comparison():
    url = 'http://localhost:5000/api/compare'
    data = {
        'expected_terms_id': 'test-id',
        'contract_ids': ['test-contract-id']
    }
    
    print("Starting test...")
    print("-" * 50)
    
    try:
        print("1. Testing connection to server...")
        requests.get('http://localhost:5000/api/compare/test')
        print("✓ Server is accessible")
        
        print("\n2. Sending comparison request...")
        print(f"URL: {url}")
        print("Request data:")
        print(json.dumps(data, indent=2))
        
        response = requests.post(url, json=data)
        
        print("\n3. Response received:")
        print(f"Status code: {response.status_code}")
        print("Headers:")
        print(json.dumps(dict(response.headers), indent=2))
        print("Body:")
        print(json.dumps(response.json(), indent=2))
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to server. Is Flask running?")
        sys.exit(1)
    except Exception as e:
        print("❌ Error occurred:")
        print(str(e))
        print("\nTraceback:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    test_comparison() 