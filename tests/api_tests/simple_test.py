#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests

print("Testing ARGO API...")
try:
    response = requests.get("http://localhost:8000", timeout=10)
    print(f"API Status: {response.status_code}")
    print(f"Response: {response.json()}")
    if response.status_code == 200:
        print(" API is working!")
    else:
        print(" API returned error status")
except requests.exceptions.ConnectionError:
    print(" Cannot connect - start server with: cd backend\api; python main.py")
except Exception as e:
    print(f" Test failed: {e}")
