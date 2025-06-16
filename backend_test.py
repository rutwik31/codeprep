#!/usr/bin/env python3
import requests
import json
import time
import unittest
import os
from dotenv import load_dotenv

# Load environment variables from frontend .env file to get the backend URL
load_dotenv('/app/frontend/.env')

# Get the backend URL from environment variables
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL')
if not BACKEND_URL:
    raise ValueError("REACT_APP_BACKEND_URL not found in environment variables")

API_BASE_URL = f"{BACKEND_URL}/api"

class BackendTest(unittest.TestCase):
    def setUp(self):
        # Verify the backend is running
        try:
            response = requests.get(f"{API_BASE_URL}/")
            self.assertEqual(response.status_code, 200)
            print(f"Backend is running at {API_BASE_URL}")
        except Exception as e:
            self.fail(f"Backend is not running or not accessible: {str(e)}")

    def test_get_problems(self):
        """Test GET /api/problems endpoint"""
        print("\n--- Testing Problem Management API: GET /api/problems ---")
        response = requests.get(f"{API_BASE_URL}/problems")
        self.assertEqual(response.status_code, 200)
        problems = response.json()
        self.assertIsInstance(problems, list)
        self.assertGreaterEqual(len(problems), 3)  # At least 3 sample problems
        
        # Verify problem structure
        for problem in problems:
            self.assertIn("id", problem)
            self.assertIn("title", problem)
            self.assertIn("description", problem)
            self.assertIn("difficulty", problem)
            self.assertIn("test_cases", problem)
            self.assertIn("time_limit", problem)
        
        print(f"Found {len(problems)} problems")
        print("Problem IDs:", [p["id"] for p in problems])
        print("✅ GET /api/problems test passed")

    def test_get_problem_by_id(self):
        """Test GET /api/problems/{id} endpoint"""
        print("\n--- Testing Problem Management API: GET /api/problems/{id} ---")
        problem_ids = ["two-sum", "palindrome-check", "fibonacci"]
        
        for problem_id in problem_ids:
            response = requests.get(f"{API_BASE_URL}/problems/{problem_id}")
            self.assertEqual(response.status_code, 200)
            problem = response.json()
            self.assertEqual(problem["id"], problem_id)
            self.assertIn("title", problem)
            self.assertIn("description", problem)
            self.assertIn("test_cases", problem)
            print(f"✅ Successfully retrieved problem: {problem_id}")
        
        # Test with non-existent problem ID
        response = requests.get(f"{API_BASE_URL}/problems/non-existent-problem")
        self.assertEqual(response.status_code, 404)
        print("✅ Correctly returns 404 for non-existent problem")
        print("✅ GET /api/problems/{id} test passed")

    def test_execute_correct_solution(self):
        """Test /api/execute endpoint with correct solutions"""
        print("\n--- Testing Code Execution Engine: Correct Solutions ---")
        
        # Test two-sum problem with correct solution
        two_sum_solution = """
def two_sum(nums, target):
    num_map = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in num_map:
            return [num_map[complement], i]
        num_map[num] = i
    return []
"""
        response = self.execute_code("two-sum", two_sum_solution)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result["success"])
        self.assertEqual(result["total_passed"], result["total_tests"])
        print(f"✅ two-sum correct solution passed {result['total_passed']}/{result['total_tests']} tests")
        
        # Test palindrome-check problem with correct solution
        palindrome_solution = """
def is_palindrome(s):
    # Remove non-alphanumeric characters and convert to lowercase
    s = ''.join(c for c in s if c.isalnum()).lower()
    return s == s[::-1]
"""
        response = self.execute_code("palindrome-check", palindrome_solution)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result["success"])
        self.assertEqual(result["total_passed"], result["total_tests"])
        print(f"✅ palindrome-check correct solution passed {result['total_passed']}/{result['total_tests']} tests")
        
        # Test fibonacci problem with correct solution
        fibonacci_solution = """
def fibonacci(n):
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n-1) + fibonacci(n-2)
"""
        response = self.execute_code("fibonacci", fibonacci_solution)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result["success"])
        self.assertEqual(result["total_passed"], result["total_tests"])
        print(f"✅ fibonacci correct solution passed {result['total_passed']}/{result['total_tests']} tests")
        
        print("✅ Code execution with correct solutions test passed")

    def test_execute_incorrect_solution(self):
        """Test /api/execute endpoint with incorrect solutions"""
        print("\n--- Testing Code Execution Engine: Incorrect Solutions ---")
        
        # Test two-sum problem with incorrect solution
        incorrect_solution = """
def two_sum(nums, target):
    # This solution is incorrect - always returns [0, 1]
    return [0, 1]
"""
        response = self.execute_code("two-sum", incorrect_solution)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertFalse(result["success"])  # Overall success should be false
        self.assertLess(result["total_passed"], result["total_tests"])  # Should not pass all tests
        print(f"✅ two-sum incorrect solution correctly failed, passed only {result['total_passed']}/{result['total_tests']} tests")
        
        print("✅ Code execution with incorrect solutions test passed")

    def test_execute_syntax_error(self):
        """Test /api/execute endpoint with code containing syntax errors"""
        print("\n--- Testing Code Execution Engine: Syntax Errors ---")
        
        # Code with syntax error
        code_with_syntax_error = """
def two_sum(nums, target):
    # This code has a syntax error - missing closing parenthesis
    for i in range(len(nums):
        return [0, 1]
"""
        response = self.execute_code("two-sum", code_with_syntax_error)
        # The server might return 200 with error in result or 500 directly
        # Both are acceptable for error handling
        self.assertTrue(response.status_code in [200, 500])
        
        if response.status_code == 200:
            result = response.json()
            self.assertFalse(result["success"])
            
            # Check if at least one test case has an error
            has_error = any(test.get("error") for test in result["test_results"])
            self.assertTrue(has_error)
        else:
            print("Server returned 500 for syntax error, which is acceptable error handling")
            
        print("✅ Syntax error correctly detected and handled")
        print("✅ Code execution with syntax errors test passed")

    def test_execute_timeout(self):
        """Test /api/execute endpoint with code that should timeout"""
        print("\n--- Testing Code Execution Engine: Timeout Protection ---")
        
        # Code with infinite loop
        infinite_loop_code = """
def two_sum(nums, target):
    # This will cause a timeout
    while True:
        pass
    return [0, 1]
"""
        response = self.execute_code("two-sum", infinite_loop_code)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertFalse(result["success"])
        
        # Check if at least one test case has a timeout error
        has_timeout = any("timeout" in (test.get("error") or "").lower() for test in result["test_results"])
        self.assertTrue(has_timeout)
        print("✅ Timeout protection correctly detected infinite loop")
        
        print("✅ Code execution timeout protection test passed")

    def test_database_integration(self):
        """Test database integration for submissions"""
        print("\n--- Testing Database Integration ---")
        
        # First, submit a solution to create a submission record
        solution = """
def two_sum(nums, target):
    for i in range(len(nums)):
        for j in range(i+1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []
"""
        response = self.execute_code("two-sum", solution)
        self.assertEqual(response.status_code, 200)
        
        # Now check if the submission was stored in the database
        response = requests.get(f"{API_BASE_URL}/submissions")
        self.assertEqual(response.status_code, 200)
        submissions = response.json()
        self.assertIsInstance(submissions, list)
        
        # Verify at least one submission exists
        self.assertGreaterEqual(len(submissions), 1)
        
        # Verify submission structure
        for submission in submissions:
            self.assertIn("id", submission)
            self.assertIn("problem_id", submission)
            self.assertIn("code", submission)
            self.assertIn("result", submission)
            self.assertIn("submitted_at", submission)
        
        print(f"Found {len(submissions)} submissions in the database")
        print("✅ Database integration test passed")

    def execute_code(self, problem_id, code):
        """Helper method to execute code for a problem"""
        payload = {
            "problem_id": problem_id,
            "code": code,
            "language": "python"
        }
        return requests.post(f"{API_BASE_URL}/execute", json=payload)

if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)