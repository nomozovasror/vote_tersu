#!/usr/bin/env python3
import httpx
import json

url = "https://student.tersu.uz/rest/v1/data/employee-list"
token = "uE1tujuAokux6GcmYx3VBumn86JqWG73"

headers = {"Authorization": f"Bearer {token}"}

try:
    response = httpx.get(url, headers=headers, timeout=10.0)
    print(f"Status Code: {response.status_code}")
    print(f"Response:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)[:500]}")
except Exception as e:
    print(f"Error: {e}")
