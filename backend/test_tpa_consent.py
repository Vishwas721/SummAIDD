"""
Test script for TPA Consent Management Endpoints
Phase 1 - Foundation & Consent

Tests the three consent management endpoints:
1. POST /tpa/consent/{patient_id} - Request consent
2. POST /tpa/consent/{patient_id}/verify - Verify OTP
3. GET /tpa/consent/{patient_id} - Get consent status

Usage: python test_tpa_consent.py
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_consent_workflow():
    """Test complete consent workflow for a patient"""
    # Use patient_id = 1 (assuming it exists from demo data)
    patient_id = 1
    mobile_number = "+919876543210"
    test_otp = "123456"
    
    print("=" * 70)
    print("Testing TPA Consent Management Endpoints")
    print("=" * 70)
    
    # Test 1: Request consent
    print("\n[TEST 1] POST /tpa/consent/{patient_id} - Request Consent")
    print("-" * 70)
    try:
        response = requests.post(
            f"{BASE_URL}/tpa/consent/{patient_id}",
            json={"mobile_number": mobile_number}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ PASS: Consent request created successfully")
            consent_data = response.json()
            assert consent_data["patient_id"] == patient_id
            assert consent_data["consent_status"] == False
            assert consent_data["responded_at"] is None
        elif response.status_code == 400:
            print("⚠️  Consent already exists (expected if test run multiple times)")
        else:
            print(f"❌ FAIL: Unexpected status code {response.status_code}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 2: Get consent status (before verification)
    print("\n[TEST 2] GET /tpa/consent/{patient_id} - Get Consent Status (Pending)")
    print("-" * 70)
    try:
        response = requests.get(f"{BASE_URL}/tpa/consent/{patient_id}")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            consent_data = response.json()
            if consent_data["consent_status"]:
                print("⚠️  Consent already verified (expected if test run multiple times)")
            else:
                print("✅ PASS: Consent status retrieved (pending)")
        else:
            print(f"❌ FAIL: Unexpected status code {response.status_code}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 3: Verify consent with OTP
    print("\n[TEST 3] POST /tpa/consent/{patient_id}/verify - Verify OTP")
    print("-" * 70)
    try:
        response = requests.post(
            f"{BASE_URL}/tpa/consent/{patient_id}/verify",
            json={"otp": test_otp}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ PASS: OTP verified, consent granted")
            consent_data = response.json()
            assert consent_data["consent_status"] == True
            assert consent_data["responded_at"] is not None
        elif response.status_code == 400:
            print("⚠️  Consent already verified (expected if test run multiple times)")
        else:
            print(f"❌ FAIL: Unexpected status code {response.status_code}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 4: Get consent status (after verification)
    print("\n[TEST 4] GET /tpa/consent/{patient_id} - Get Consent Status (Approved)")
    print("-" * 70)
    try:
        response = requests.get(f"{BASE_URL}/tpa/consent/{patient_id}")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            consent_data = response.json()
            if consent_data["consent_status"] == True:
                print("✅ PASS: Consent status verified")
            else:
                print("⚠️  Consent not verified yet")
        else:
            print(f"❌ FAIL: Unexpected status code {response.status_code}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 5: Error handling - Non-existent patient
    print("\n[TEST 5] Error Handling - Non-existent Patient")
    print("-" * 70)
    try:
        response = requests.post(
            f"{BASE_URL}/tpa/consent/99999",
            json={"mobile_number": mobile_number}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 404:
            print("✅ PASS: Correctly returns 404 for non-existent patient")
        else:
            print(f"❌ FAIL: Expected 404, got {response.status_code}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 6: Error handling - Invalid OTP format
    print("\n[TEST 6] Error Handling - Invalid OTP Format")
    print("-" * 70)
    try:
        # Create a new consent for patient 2 (if exists)
        test_patient_id = 2
        requests.post(
            f"{BASE_URL}/tpa/consent/{test_patient_id}",
            json={"mobile_number": "+919876543211"}
        )
        
        # Try invalid OTP
        response = requests.post(
            f"{BASE_URL}/tpa/consent/{test_patient_id}/verify",
            json={"otp": "abc"}  # Non-numeric OTP
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 400:
            print("✅ PASS: Correctly rejects invalid OTP format")
        else:
            print(f"⚠️  Expected 400, got {response.status_code}")
    except Exception as e:
        print(f"⚠️  Note: {e}")
    
    print("\n" + "=" * 70)
    print("Test suite completed!")
    print("=" * 70)


if __name__ == "__main__":
    print("\n🚀 Starting TPA Consent Endpoint Tests\n")
    print("⚠️  Prerequisites:")
    print("   1. FastAPI server running on http://localhost:8000")
    print("   2. Database schema updated with patient_consents table")
    print("   3. At least one patient exists in the database\n")
    
    try:
        # Quick health check
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("✅ Server is running\n")
            test_consent_workflow()
        else:
            print("❌ Server not responding correctly")
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to server at http://localhost:8000")
        print("   Please start the server with: python backend/main.py")
