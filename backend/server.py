from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
import subprocess
import tempfile
import sys
import time
import signal
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class Problem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    difficulty: str
    sample_input: str
    sample_output: str
    test_cases: List[Dict[str, str]]
    time_limit: int = 5  # seconds
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CodeSubmission(BaseModel):
    problem_id: str
    code: str
    language: str = "python"

class ExecutionResult(BaseModel):
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    execution_time: float
    test_results: List[Dict[str, Any]]
    total_passed: int
    total_tests: int

class SubmissionRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    problem_id: str
    code: str
    language: str
    result: ExecutionResult
    submitted_at: datetime = Field(default_factory=datetime.utcnow)

# Sample problems
SAMPLE_PROBLEMS = [
    {
        "id": "two-sum",
        "title": "Two Sum",
        "description": """Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.

You may assume that each input would have exactly one solution, and you may not use the same element twice.

Example:
Input: nums = [2,7,11,15], target = 9
Output: [0,1]
Explanation: Because nums[0] + nums[1] == 9, we return [0, 1].

Write a function called `two_sum(nums, target)` that returns the indices.""",
        "difficulty": "Easy",
        "sample_input": "[2, 7, 11, 15]\n9",
        "sample_output": "[0, 1]",
        "test_cases": [
            {"input": "[2, 7, 11, 15]\n9", "expected_output": "[0, 1]"},
            {"input": "[3, 2, 4]\n6", "expected_output": "[1, 2]"},
            {"input": "[3, 3]\n6", "expected_output": "[0, 1]"},
            {"input": "[1, 2, 3, 4, 5]\n8", "expected_output": "[2, 4]"}
        ],
        "time_limit": 3
    },
    {
        "id": "palindrome-check",
        "title": "Palindrome Check",
        "description": """Write a function to check if a given string is a palindrome. A palindrome is a word, phrase, number, or other sequence of characters that reads the same forward and backward.

For this problem, consider only alphanumeric characters and ignore cases.

Example:
Input: "A man a plan a canal Panama"
Output: True

Write a function called `is_palindrome(s)` that returns True if the string is a palindrome, False otherwise.""",
        "difficulty": "Easy",
        "sample_input": "A man a plan a canal Panama",
        "sample_output": "True",
        "test_cases": [
            {"input": "A man a plan a canal Panama", "expected_output": "True"},
            {"input": "race a car", "expected_output": "False"},
            {"input": "hello", "expected_output": "False"},
            {"input": "Madam", "expected_output": "True"},
            {"input": "12321", "expected_output": "True"}
        ],
        "time_limit": 2
    },
    {
        "id": "fibonacci",
        "title": "Fibonacci Number",
        "description": """The Fibonacci numbers, commonly denoted F(n) form a sequence, called the Fibonacci sequence, such that each number is the sum of the two preceding ones, starting from 0 and 1.

F(0) = 0, F(1) = 1
F(n) = F(n - 1) + F(n - 2), for n > 1.

Given n, calculate F(n).

Example:
Input: 4
Output: 3
Explanation: F(4) = F(3) + F(2) = 2 + 1 = 3.

Write a function called `fibonacci(n)` that returns the nth Fibonacci number.""",
        "difficulty": "Easy",
        "sample_input": "4",
        "sample_output": "3",
        "test_cases": [
            {"input": "0", "expected_output": "0"},
            {"input": "1", "expected_output": "1"},
            {"input": "4", "expected_output": "3"},
            {"input": "7", "expected_output": "13"},
            {"input": "10", "expected_output": "55"}
        ],
        "time_limit": 3
    }
]

def timeout_handler(signum, frame):
    raise TimeoutError("Code execution timed out")

def execute_python_code(code: str, input_data: str, time_limit: int = 5) -> Dict[str, Any]:
    """Execute Python code safely with timeout and input"""
    try:
        # Create a temporary file for the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp_file:
            # Prepare the code with input handling
            full_code = f"""
import sys
import json

# User's code
{code}

# Read input and process
try:
    input_lines = '''{input_data}'''.strip().split('\\n')
    
    # Try to parse input intelligently
    if len(input_lines) == 1:
        try:
            # Try to evaluate as Python literal (list, number, etc.)
            test_input = eval(input_lines[0])
        except:
            # Treat as string
            test_input = input_lines[0]
    else:
        # Multiple lines - treat as separate arguments
        test_input = []
        for line in input_lines:
            try:
                test_input.append(eval(line))
            except:
                test_input.append(line)
    
    # Call the appropriate function based on available functions
    result = None
    if 'two_sum' in globals() and callable(two_sum):
        if isinstance(test_input, list) and len(test_input) >= 2:
            result = two_sum(test_input[0], test_input[1])
        else:
            result = "Error: two_sum requires array and target"
    elif 'is_palindrome' in globals() and callable(is_palindrome):
        result = is_palindrome(str(test_input))
    elif 'fibonacci' in globals() and callable(fibonacci):
        result = fibonacci(int(test_input))
    else:
        result = "No recognized function found. Please implement the required function."
    
    print(json.dumps(result) if isinstance(result, (list, dict)) else str(result))
    
except Exception as e:
    print(f"Error: {{str(e)}}")
"""
            tmp_file.write(full_code)
            tmp_file.flush()
            
            # Execute the code with timeout
            start_time = time.time()
            
            try:
                # Set up timeout signal
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(time_limit)
                
                # Execute the code
                result = subprocess.run(
                    [sys.executable, tmp_file.name],
                    capture_output=True,
                    text=True,
                    timeout=time_limit
                )
                
                # Clear the alarm
                signal.alarm(0)
                
                execution_time = time.time() - start_time
                
                if result.returncode == 0:
                    return {
                        "success": True,
                        "output": result.stdout.strip(),
                        "error": None,
                        "execution_time": execution_time
                    }
                else:
                    return {
                        "success": False,
                        "output": None,
                        "error": result.stderr.strip() or "Runtime error occurred",
                        "execution_time": execution_time
                    }
                    
            except (subprocess.TimeoutExpired, TimeoutError):
                return {
                    "success": False,
                    "output": None,
                    "error": f"Code execution timed out after {time_limit} seconds",
                    "execution_time": time_limit
                }
            finally:
                signal.alarm(0)  # Clear any remaining alarm
                
    except Exception as e:
        return {
            "success": False,
            "output": None,
            "error": f"Execution error: {str(e)}",
            "execution_time": 0
        }
    finally:
        # Clean up temporary file
        try:
            os.unlink(tmp_file.name)
        except:
            pass

@api_router.get("/")
async def root():
    return {"message": "Placement Coding Platform API"}

@api_router.get("/problems", response_model=List[Problem])
async def get_problems():
    """Get all available problems"""
    problems = []
    for prob_data in SAMPLE_PROBLEMS:
        problem = Problem(**prob_data)
        problems.append(problem)
    return problems

@api_router.get("/problems/{problem_id}", response_model=Problem)
async def get_problem(problem_id: str):
    """Get a specific problem by ID"""
    for prob_data in SAMPLE_PROBLEMS:
        if prob_data["id"] == problem_id:
            return Problem(**prob_data)
    raise HTTPException(status_code=404, detail="Problem not found")

@api_router.post("/execute", response_model=ExecutionResult)
async def execute_code(submission: CodeSubmission):
    """Execute code against test cases"""
    try:
        # Find the problem
        problem_data = None
        for prob in SAMPLE_PROBLEMS:
            if prob["id"] == submission.problem_id:
                problem_data = prob
                break
        
        if not problem_data:
            raise HTTPException(status_code=404, detail="Problem not found")
        
        # Execute against all test cases
        test_results = []
        passed_count = 0
        
        for i, test_case in enumerate(problem_data["test_cases"]):
            execution_result = execute_python_code(
                submission.code, 
                test_case["input"], 
                problem_data.get("time_limit", 5)
            )
            
            expected = test_case["expected_output"].strip()
            actual = execution_result.get("output", "").strip()
            
            passed = execution_result["success"] and actual == expected
            if passed:
                passed_count += 1
            
            test_results.append({
                "test_case": i + 1,
                "input": test_case["input"],
                "expected_output": expected,
                "actual_output": actual,
                "passed": passed,
                "error": execution_result.get("error"),
                "execution_time": execution_result.get("execution_time", 0)
            })
        
        # Overall result
        overall_success = passed_count == len(problem_data["test_cases"])
        
        result = ExecutionResult(
            success=overall_success,
            output=f"Passed {passed_count}/{len(problem_data['test_cases'])} test cases",
            test_results=test_results,
            total_passed=passed_count,
            total_tests=len(problem_data["test_cases"]),
            execution_time=sum(tr.get("execution_time", 0) for tr in test_results)
        )
        
        # Save submission to database
        submission_record = SubmissionRecord(
            problem_id=submission.problem_id,
            code=submission.code,
            language=submission.language,
            result=result
        )
        
        await db.submissions.insert_one(submission_record.dict())
        
        return result
        
    except Exception as e:
        logger.error(f"Code execution error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")

@api_router.get("/submissions")
async def get_submissions():
    """Get recent submissions"""
    submissions = await db.submissions.find().sort("submitted_at", -1).limit(10).to_list(10)
    return [SubmissionRecord(**sub) for sub in submissions]

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()