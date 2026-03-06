"""
Test script for Audit & Alert Override Endpoints
Epic 4.1 & 4.2 - WORM Audit Logging

Tests the audit logging and alert override endpoints:
1. POST /audit/log - Create audit log entry
2. GET /audit/{patient_id} - Retrieve audit logs
3. POST /audit/safety-check/override - Create alert override + audit log

Usage: python test_audit_endpoints.py
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_audit_logging():
    """Test audit logging and alert override endpoints"""
    # Use patient_id = 1 (assuming it exists from seed data)
    patient_id = 1
    
    print("=" * 70)
    print("Testing Audit & Alert Override Endpoints (Epic 4.1 & 4.2)")
    print("=" * 70)
    
    # Test 1: Create audit log - VIEWED_SUMMARY
    print("\n[TEST 1] POST /audit/log - Create Audit Log (VIEWED_SUMMARY)")
    print("-" * 70)
    try:
        payload = {
            "patient_id": patient_id,
            "user_id": "dr_smith",
            "action_type": "VIEWED_SUMMARY",
            "action_metadata": {
                "session_id": "abc123",
                "ip_address": "192.168.1.100"
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/audit/log",
            json=payload
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 201:
            print("✅ PASS: Audit log created successfully")
            log_data = response.json()
            assert log_data["patient_id"] == patient_id
            assert log_data["user_id"] == "dr_smith"
            assert log_data["action_type"] == "VIEWED_SUMMARY"
            assert log_data["log_id"] is not None
            assert log_data["created_at"] is not None
            print(f"   Log ID: {log_data['log_id']}")
            print(f"   Created At: {log_data['created_at']}")
        else:
            print(f"❌ FAIL: Unexpected status code {response.status_code}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 2: Create audit log - PRESCRIBED_DRUG
    print("\n[TEST 2] POST /audit/log - Create Audit Log (PRESCRIBED_DRUG)")
    print("-" * 70)
    try:
        payload = {
            "patient_id": patient_id,
            "user_id": "dr_jones",
            "action_type": "PRESCRIBED_DRUG",
            "action_metadata": {
                "drug_name": "Lisinopril",
                "dosage": "10mg",
                "frequency": "once daily"
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/audit/log",
            json=payload
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 201:
            print("✅ PASS: Audit log created successfully")
            log_data = response.json()
            assert log_data["action_type"] == "PRESCRIBED_DRUG"
            assert log_data["action_metadata"]["drug_name"] == "Lisinopril"
        else:
            print(f"❌ FAIL: Unexpected status code {response.status_code}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 3: Create audit log - CLICKED_CITATION
    print("\n[TEST 3] POST /audit/log - Create Audit Log (CLICKED_CITATION)")
    print("-" * 70)
    try:
        payload = {
            "patient_id": patient_id,
            "user_id": "dr_smith",
            "action_type": "CLICKED_CITATION",
            "action_metadata": {
                "citation_id": 42,
                "report_id": 5,
                "chunk_id": 12
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/audit/log",
            json=payload
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 201:
            print("✅ PASS: Audit log created successfully")
        else:
            print(f"❌ FAIL: Unexpected status code {response.status_code}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 4: Retrieve audit logs for patient
    print(f"\n[TEST 4] GET /audit/{patient_id} - Retrieve Audit Logs")
    print("-" * 70)
    try:
        response = requests.get(f"{BASE_URL}/audit/{patient_id}")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            logs = response.json()
            print(f"✅ PASS: Retrieved {len(logs)} audit log(s)")
            
            # Verify chronological order
            if len(logs) > 1:
                timestamps = [log["created_at"] for log in logs]
                assert timestamps == sorted(timestamps), "Logs not in chronological order"
                print("   Logs are in chronological order (oldest first)")
            
            # Display summary
            print(f"\n   Audit Log Summary:")
            for idx, log in enumerate(logs, 1):
                print(f"   {idx}. {log['action_type']} by {log['user_id']} at {log['created_at']}")
        else:
            print(f"❌ FAIL: Unexpected status code {response.status_code}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 5: Create alert override (dual action)
    print("\n[TEST 5] POST /audit/safety-check/override - Create Alert Override")
    print("-" * 70)
    try:
        payload = {
            "patient_id": patient_id,
            "drug_name": "Penicillin V",
            "allergy_keyword": "penicillin",
            "doctor_reason": "Patient tolerance test completed successfully on 2026-03-05. Informed consent documented in chart note #4521.",
            "overridden_by": "dr_smith"
        }
        
        response = requests.post(
            f"{BASE_URL}/audit/safety-check/override",
            json=payload
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 201:
            print("✅ PASS: Alert override created successfully")
            override_data = response.json()
            assert override_data["patient_id"] == patient_id
            assert override_data["drug_name"] == "Penicillin V"
            assert override_data["allergy_keyword"] == "penicillin"
            assert override_data["overridden_by"] == "dr_smith"
            print(f"   Override ID: {override_data['override_id']}")
            print(f"   Created At: {override_data['created_at']}")
        else:
            print(f"❌ FAIL: Unexpected status code {response.status_code}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 6: Verify OVERRODE_ALERT audit log was auto-created
    print(f"\n[TEST 6] GET /audit/{patient_id} - Verify OVERRODE_ALERT Audit Log")
    print("-" * 70)
    try:
        response = requests.get(f"{BASE_URL}/audit/{patient_id}")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            logs = response.json()
            override_logs = [log for log in logs if log["action_type"] == "OVERRODE_ALERT"]
            
            if override_logs:
                print(f"✅ PASS: Found {len(override_logs)} OVERRODE_ALERT audit log(s)")
                latest_override = override_logs[-1]
                print(f"   Latest Override Audit Log:")
                print(f"   - User: {latest_override['user_id']}")
                print(f"   - Drug: {latest_override['action_metadata'].get('drug_name')}")
                print(f"   - Allergy: {latest_override['action_metadata'].get('allergy_keyword')}")
                print(f"   - Created: {latest_override['created_at']}")
            else:
                print("❌ FAIL: No OVERRODE_ALERT audit log found")
        else:
            print(f"❌ FAIL: Unexpected status code {response.status_code}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 7: Test invalid patient_id (404 error)
    print("\n[TEST 7] GET /audit/99999 - Test Invalid Patient ID")
    print("-" * 70)
    try:
        response = requests.get(f"{BASE_URL}/audit/99999")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 404:
            print("✅ PASS: Correctly returns 404 for non-existent patient")
        else:
            print(f"❌ FAIL: Expected 404, got {response.status_code}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 8: Test invalid action_type (422 validation error)
    print("\n[TEST 8] POST /audit/log - Test Invalid Action Type")
    print("-" * 70)
    try:
        payload = {
            "patient_id": patient_id,
            "user_id": "dr_smith",
            "action_type": "INVALID_ACTION",  # Not in enum
            "action_metadata": {}
        }
        
        response = requests.post(
            f"{BASE_URL}/audit/log",
            json=payload
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 422:
            print("✅ PASS: Correctly rejects invalid action_type with 422")
        else:
            print(f"❌ FAIL: Expected 422, got {response.status_code}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print("\n" + "=" * 70)
    print("Test Suite Complete")
    print("=" * 70)


if __name__ == "__main__":
    test_audit_logging()
