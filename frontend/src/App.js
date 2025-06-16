import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Monaco Editor component (simplified version)
const CodeEditor = ({ value, onChange, language = "python" }) => {
  return (
    <div className="code-editor-container">
      <div className="editor-header">
        <span className="editor-title">Code Editor</span>
        <span className="language-badge">{language}</span>
      </div>
      <textarea
        className="code-editor"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="# Write your code here..."
        rows={15}
        style={{
          width: '100%',
          fontFamily: 'Monaco, Consolas, "Courier New", monospace',
          fontSize: '14px',
          padding: '16px',
          border: '1px solid #e5e7eb',
          borderRadius: '8px',
          backgroundColor: '#1f2937',
          color: '#f9fafb',
          resize: 'vertical',
          outline: 'none'
        }}
      />
    </div>
  );
};

const ProblemList = ({ onSelectProblem }) => {
  const [problems, setProblems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchProblems = async () => {
      try {
        const response = await axios.get(`${API}/problems`);
        setProblems(response.data);
      } catch (error) {
        console.error('Failed to fetch problems:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchProblems();
  }, []);

  if (loading) {
    return (
      <div className="loading-spinner">
        <div className="spinner"></div>
        <p>Loading problems...</p>
      </div>
    );
  }

  return (
    <div className="problem-list">
      <h2 className="section-title">🧩 Coding Problems</h2>
      <div className="problems-grid">
        {problems.map((problem) => (
          <div
            key={problem.id}
            className="problem-card"
            onClick={() => onSelectProblem(problem)}
          >
            <div className="problem-header">
              <h3 className="problem-title">{problem.title}</h3>
              <span className={`difficulty-badge ${problem.difficulty.toLowerCase()}`}>
                {problem.difficulty}
              </span>
            </div>
            <p className="problem-preview">
              {problem.description.substring(0, 100)}...
            </p>
            <div className="problem-footer">
              <span className="test-count">
                {problem.test_cases.length} test cases
              </span>
              <span className="time-limit">
                ⏱️ {problem.time_limit}s
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const ProblemSolver = ({ problem, onBack }) => {
  const [code, setCode] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!code.trim()) {
      alert('Please write some code before submitting!');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API}/execute`, {
        problem_id: problem.id,
        code: code,
        language: 'python'
      });
      setResult(response.data);
    } catch (error) {
      console.error('Execution failed:', error);
      setResult({
        success: false,
        output: 'Submission failed. Please try again.',
        test_results: [],
        total_passed: 0,
        total_tests: 0
      });
    } finally {
      setLoading(false);
    }
  };

  const getResultColor = (passed) => {
    return passed ? '#10b981' : '#ef4444';
  };

  return (
    <div className="problem-solver">
      <div className="solver-header">
        <button className="back-button" onClick={onBack}>
          ← Back to Problems
        </button>
        <h1 className="problem-title">{problem.title}</h1>
        <span className={`difficulty-badge ${problem.difficulty.toLowerCase()}`}>
          {problem.difficulty}
        </span>
      </div>

      <div className="solver-content">
        <div className="problem-section">
          <div className="problem-description">
            <h3>📋 Problem Description</h3>
            <div className="description-content">
              {problem.description.split('\n').map((line, index) => (
                <p key={index}>{line}</p>
              ))}
            </div>
          </div>

          <div className="sample-case">
            <h4>📝 Sample Input/Output</h4>
            <div className="sample-grid">
              <div className="sample-input">
                <strong>Input:</strong>
                <pre>{problem.sample_input}</pre>
              </div>
              <div className="sample-output">
                <strong>Output:</strong>
                <pre>{problem.sample_output}</pre>
              </div>
            </div>
          </div>
        </div>

        <div className="coding-section">
          <CodeEditor
            value={code}
            onChange={setCode}
            language="python"
          />
          
          <div className="submit-section">
            <button
              className="submit-button"
              onClick={handleSubmit}
              disabled={loading}
            >
              {loading ? (
                <>
                  <div className="button-spinner"></div>
                  Running Tests...
                </>
              ) : (
                '🚀 Run Code'
              )}
            </button>
          </div>

          {result && (
            <div className="results-section">
              <div className={`result-header ${result.success ? 'success' : 'failure'}`}>
                <h3>
                  {result.success ? '✅ All Tests Passed!' : '❌ Some Tests Failed'}
                </h3>
                <span className="score">
                  {result.total_passed}/{result.total_tests} tests passed
                </span>
              </div>

              <div className="test-results">
                {result.test_results.map((test, index) => (
                  <div
                    key={index}
                    className="test-result"
                    style={{ borderLeft: `4px solid ${getResultColor(test.passed)}` }}
                  >
                    <div className="test-header">
                      <strong>Test Case {test.test_case}</strong>
                      <span className={`test-status ${test.passed ? 'passed' : 'failed'}`}>
                        {test.passed ? 'PASSED' : 'FAILED'}
                      </span>
                    </div>
                    
                    <div className="test-details">
                      <div className="test-input">
                        <strong>Input:</strong>
                        <pre>{test.input}</pre>
                      </div>
                      <div className="test-outputs">
                        <div className="expected-output">
                          <strong>Expected:</strong>
                          <pre>{test.expected_output}</pre>
                        </div>
                        <div className="actual-output">
                          <strong>Your Output:</strong>
                          <pre style={{ color: test.passed ? '#10b981' : '#ef4444' }}>
                            {test.actual_output || test.error || 'No output'}
                          </pre>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

function App() {
  const [selectedProblem, setSelectedProblem] = useState(null);

  return (
    <div className="App">
      <div className="app-container">
        <header className="app-header">
          <div className="header-content">
            <h1 className="app-title">
              <span className="title-icon">💻</span>
              Placement Coding Platform
            </h1>
            <p className="app-subtitle">
              Practice coding problems and prepare for technical interviews
            </p>
          </div>
        </header>

        <main className="main-content">
          {selectedProblem ? (
            <ProblemSolver
              problem={selectedProblem}
              onBack={() => setSelectedProblem(null)}
            />
          ) : (
            <ProblemList onSelectProblem={setSelectedProblem} />
          )}
        </main>
      </div>
    </div>
  );
}

export default App;