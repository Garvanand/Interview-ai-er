"use client"

import { useState, useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { apiClient, type CodeEvaluation } from '@/lib/api-client'
import { CheckCircle, XCircle, Play, Code2, AlertCircle, Timer, Zap } from 'lucide-react'
import dynamic from 'next/dynamic'

const Monaco = dynamic(() => import('./code-editor'), { ssr: false })

interface EnhancedCodeEditorProps {
  sessionId?: string
  questionId?: string
  onCodeSubmit?: (evaluation: CodeEvaluation) => void
}

const LANGUAGE_OPTIONS = [
  { value: 'python', label: 'Python', extension: '.py' },
  { value: 'javascript', label: 'JavaScript', extension: '.js' },
  { value: 'typescript', label: 'TypeScript', extension: '.ts' },
  { value: 'java', label: 'Java', extension: '.java' },
  { value: 'cpp', label: 'C++', extension: '.cpp' },
  { value: 'csharp', label: 'C#', extension: '.cs' },
  { value: 'go', label: 'Go', extension: '.go' },
  { value: 'rust', label: 'Rust', extension: '.rs' },
]

const LANGUAGE_SNIPPETS: Record<string, string> = {
  python: `# Write your solution here
def solve_problem(input_data):
    """
    Your solution goes here
    """
    # Example: Find the maximum value in a list
    if not input_data:
        return None
    return max(input_data)

# Test your solution
test_data = [1, 5, 3, 9, 2, 7]
result = solve_problem(test_data)
print(f"Result: {result}")`,
  
  javascript: `// Write your solution here
function solveProblem(inputData) {
  /**
   * Your solution goes here
   */
  // Example: Find the maximum value in an array
  if (!inputData || inputData.length === 0) {
    return null;
  }
  return Math.max(...inputData);
}

// Test your solution
const testData = [1, 5, 3, 9, 2, 7];
const result = solveProblem(testData);
console.log(\`Result: \${result}\`);`,
  
  typescript: `// Write your solution here
function solveProblem(inputData: number[]): number | null {
  /**
   * Your solution goes here
   */
  // Example: Find the maximum value in an array
  if (!inputData || inputData.length === 0) {
    return null;
  }
  return Math.max(...inputData);
}

// Test your solution
const testData: number[] = [1, 5, 3, 9, 2, 7];
const result = solveProblem(testData);
console.log(\`Result: \${result}\`);`,
  
  java: `public class Solution {
    public static Integer solveProblem(int[] inputData) {
        /**
         * Your solution goes here
         */
        // Example: Find the maximum value in an array
        if (inputData == null || inputData.length == 0) {
            return null;
        }
        
        int max = inputData[0];
        for (int i = 1; i < inputData.length; i++) {
            if (inputData[i] > max) {
                max = inputData[i];
            }
        }
        return max;
    }
    
    public static void main(String[] args) {
        int[] testData = {1, 5, 3, 9, 2, 7};
        Integer result = solveProblem(testData);
        System.out.println("Result: " + result);
    }
}`,
  
  cpp: `#include <iostream>
#include <vector>
#include <algorithm>
#include <climits>

using namespace std;

int solveProblem(const vector<int>& inputData) {
    /**
     * Your solution goes here
     */
    // Example: Find the maximum value in a vector
    if (inputData.empty()) {
        return INT_MIN;
    }
    
    return *max_element(inputData.begin(), inputData.end());
}

int main() {
    vector<int> testData = {1, 5, 3, 9, 2, 7};
    int result = solveProblem(testData);
    cout << "Result: " << result << endl;
    return 0;
}`,
  
  csharp: `using System;
using System.Linq;

public class Solution {
    public static int? SolveProblem(int[] inputData) {
        /**
         * Your solution goes here
         */
        // Example: Find the maximum value in an array
        if (inputData == null || inputData.Length == 0) {
            return null;
        }
        
        return inputData.Max();
    }
    
    public static void Main(string[] args) {
        int[] testData = {1, 5, 3, 9, 2, 7};
        int? result = SolveProblem(testData);
        Console.WriteLine($"Result: {result}");
    }
}`,
  
  go: `package main

import (
    "fmt"
    "math"
)

func solveProblem(inputData []int) *int {
    /**
     * Your solution goes here
     */
    // Example: Find the maximum value in a slice
    if len(inputData) == 0 {
        return nil
    }
    
    max := inputData[0]
    for _, value := range inputData[1:] {
        if value > max {
            max = value
        }
    }
    
    return &max
}

func main() {
    testData := []int{1, 5, 3, 9, 2, 7}
    result := solveProblem(testData)
    if result != nil {
        fmt.Printf("Result: %d\\n", *result)
    }
}`,
  
  rust: `fn solve_problem(input_data: &[i32]) -> Option<i32> {
    /**
     * Your solution goes here
     */
    // Example: Find the maximum value in a slice
    if input_data.is_empty() {
        return None;
    }
    
    input_data.iter().max().copied()
}

fn main() {
    let test_data = vec![1, 5, 3, 9, 2, 7];
    let result = solve_problem(&test_data);
    match result {
        Some(value) => println!("Result: {}", value),
        None => println!("No result"),
    }
}`,
}

export function EnhancedCodeEditor({ sessionId, questionId, onCodeSubmit }: EnhancedCodeEditorProps) {
  const [language, setLanguage] = useState<string>('python')
  const [code, setCode] = useState<string>(LANGUAGE_SNIPPETS.python)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [evaluation, setEvaluation] = useState<CodeEvaluation | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [executionTime, setExecutionTime] = useState<number>(0)
  const [isRunning, setIsRunning] = useState(false)
  
  const startTime = useRef<number>(0)
  const typingStartTime = useRef<number>(Date.now())
  const keystrokes = useRef<number[]>([])

  // Update code when language changes
  useEffect(() => {
    setCode(LANGUAGE_SNIPPETS[language] || '')
  }, [language])

  // Typing analysis for security
  useEffect(() => {
    const handleKeydown = () => {
      const now = Date.now()
      keystrokes.current.push(now)
      
      // Keep only last 20 keystrokes
      if (keystrokes.current.length > 20) {
        keystrokes.current = keystrokes.current.slice(-20)
      }
    }

    document.addEventListener('keydown', handleKeydown)
    return () => document.removeEventListener('keydown', handleKeydown)
  }, [])

  const handleLanguageChange = (newLanguage: string) => {
    setLanguage(newLanguage)
    setCode(LANGUAGE_SNIPPETS[newLanguage] || '')
    setEvaluation(null)
    setError(null)
  }

  const resetCode = () => {
    setCode(LANGUAGE_SNIPPETS[language] || '')
    setEvaluation(null)
    setError(null)
  }

  const runCode = async () => {
    if (!code.trim()) return

    setIsRunning(true)
    setError(null)
    
    try {
      // Intentional explicit unsupported state instead of fake output
      await new Promise(resolve => setTimeout(resolve, 500))
      setError("Real code execution is currently unavailable. Please use 'Submit for Evaluation' to get AI feedback on your code.")
    } finally {
      setIsRunning(false)
    }
  }

  const submitCode = async () => {
    if (!code.trim() || !sessionId || !questionId) {
      setError('Missing session ID, question ID, or code')
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      // Calculate typing metrics for security
      const typingDuration = (Date.now() - typingStartTime.current) / 1000
      const keystrokeCount = keystrokes.current.length
      
      // Submit code for evaluation
      const result = await apiClient.submitCode(sessionId, questionId, code, language)
      setEvaluation(result.evaluation)
      
      // Log code submission
      await apiClient.logEvent(sessionId, 'code_submitted', {
        question_id: questionId,
        language,
        code_length: code.length,
        execution_time: executionTime,
        typing_duration: typingDuration,
        keystroke_count: keystrokeCount
      })
      
      // Call callback if provided
      if (onCodeSubmit) {
        onCodeSubmit(result.evaluation)
      }
      
    } catch (err: any) {
      setError(err.message || 'Failed to submit code')
    } finally {
      setIsSubmitting(false)
    }
  }

  const getMonacoLanguage = (lang: string): string => {
    const languageMap: Record<string, string> = {
      'python': 'python',
      'javascript': 'javascript',
      'typescript': 'typescript',
      'java': 'java',
      'cpp': 'cpp',
      'csharp': 'csharp',
      'go': 'go',
      'rust': 'rust'
    }
    return languageMap[lang] || 'plaintext'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Code2 className="h-5 w-5" />
                Enhanced Code Editor
              </CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                Write, run, and submit your code for AI-powered evaluation
              </p>
            </div>
            <div className="flex items-center gap-2">
              {executionTime > 0 && (
                <Badge variant="outline" className="flex items-center gap-1">
                  <Timer className="h-3 w-3" />
                  {executionTime}ms
                </Badge>
              )}
              {evaluation && (
                <Badge variant={evaluation.score >= 80 ? 'default' : evaluation.score >= 60 ? 'secondary' : 'destructive'}>
                  Score: {evaluation.score}/100
                </Badge>
              )}
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Controls */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium">Language:</label>
              <Select value={language} onValueChange={handleLanguageChange}>
                <SelectTrigger className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {LANGUAGE_OPTIONS.map((lang) => (
                    <SelectItem key={lang.value} value={lang.value}>
                      {lang.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <Button onClick={runCode} disabled={isRunning || !code.trim()}>
              {isRunning ? (
                <>
                  <Timer className="h-4 w-4 mr-2 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Run Code
                </>
              )}
            </Button>
            
            <Button onClick={resetCode} variant="outline">
              Reset
            </Button>
            
            {sessionId && questionId && (
              <Button 
                onClick={submitCode} 
                disabled={isSubmitting || !code.trim()}
                className="ml-auto"
              >
                {isSubmitting ? 'Submitting...' : 'Submit for Evaluation'}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Code Editor */}
      <Card>
        <CardContent className="pt-6">
          <div className="rounded-lg border border-border">
            <Monaco 
              value={code} 
              onChange={(value) => setCode(value || '')} 
              language={getMonacoLanguage(language)}
              onFocus={() => typingStartTime.current = Date.now()}
            />
          </div>
        </CardContent>
      </Card>

      {/* Evaluation Results */}
      {evaluation && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-500" />
              Code Evaluation Results
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Overall Score */}
            <div className="text-center">
              <p className="text-sm font-medium text-muted-foreground">Overall Score</p>
              <p className="text-4xl font-bold text-green-600">{evaluation.score}/100</p>
            </div>

            {/* Detailed Scores */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium">Code Quality</p>
                <Progress value={evaluation.code_quality} className="mt-2" />
                <p className="text-sm text-muted-foreground mt-1">{evaluation.code_quality}/100</p>
              </div>
              <div>
                <p className="text-sm font-medium">Correctness</p>
                <Progress value={evaluation.correctness} className="mt-2" />
                <p className="text-sm text-muted-foreground mt-1">{evaluation.correctness}/100</p>
              </div>
              <div>
                <p className="text-sm font-medium">Efficiency</p>
                <Progress value={evaluation.efficiency} className="mt-2" />
                <p className="text-sm text-muted-foreground mt-1">{evaluation.efficiency}/100</p>
              </div>
              <div>
                <p className="text-sm font-medium">Readability</p>
                <Progress value={evaluation.readability} className="mt-2" />
                <p className="text-sm text-muted-foreground mt-1">{evaluation.readability}/100</p>
              </div>
            </div>

            {/* Complexity Analysis */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <p className="text-sm font-medium">Time Complexity</p>
                <Badge variant="outline" className="flex items-center gap-1">
                  <Zap className="h-3 w-3" />
                  {evaluation.time_complexity}
                </Badge>
              </div>
              <div className="space-y-2">
                <p className="text-sm font-medium">Space Complexity</p>
                <Badge variant="outline" className="flex items-center gap-1">
                  <Zap className="h-3 w-3" />
                  {evaluation.space_complexity}
                </Badge>
              </div>
            </div>

            {/* Feedback */}
            <div>
              <p className="text-sm font-medium">Feedback</p>
              <p className="text-sm mt-1">{evaluation.feedback}</p>
            </div>

            {/* Strengths and Improvements */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-green-700">Strengths</p>
                <ul className="text-sm mt-1 space-y-1">
                  {evaluation.strengths.map((strength, index) => (
                    <li key={index} className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      {strength}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="text-sm font-medium text-orange-700">Improvements</p>
                <ul className="text-sm mt-1 space-y-1">
                  {evaluation.improvements.map((improvement, index) => (
                    <li key={index} className="flex items-center gap-2">
                      <XCircle className="h-4 w-4 text-orange-500" />
                      {improvement}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Best Practices Score */}
            <div>
              <p className="text-sm font-medium">Best Practices</p>
              <Progress value={evaluation.best_practices} className="mt-2" />
              <p className="text-sm text-muted-foreground mt-1">{evaluation.best_practices}/100</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error Display */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  )
}
