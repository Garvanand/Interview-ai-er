"use client"

import { useState, useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { apiClient, type CodeEvaluation } from "@/lib/api-client"
import {
  Play,
  RotateCcw,
  CheckCircle2,
  XCircle,
  Terminal,
  Zap,
  Clock,
  Sparkles,
  Loader2,
  Layers,
  Code2,
  AlertCircle,
  FileCode,
  ShieldCheck
} from "lucide-react"
import dynamic from "next/dynamic"

const Monaco = dynamic(() => import("./code-editor"), { ssr: false })

interface EnhancedCodeEditorProps {
  sessionId?: string
  questionId?: string
  onCodeSubmit?: (evaluation: CodeEvaluation) => void
}

const LANGUAGE_OPTIONS = [
  { value: "python", label: "Python 3.12", extension: ".py" },
  { value: "javascript", label: "Node.js (ES6)", extension: ".js" },
  { value: "typescript", label: "TypeScript 5.x", extension: ".ts" },
  { value: "cpp", label: "C++ 20", extension: ".cpp" },
  { value: "go", label: "Go 1.22", extension: ".go" },
  { value: "rust", label: "Rust 2021", extension: ".rs" },
  { value: "java", label: "Java 21", extension: ".java" },
]

const LANGUAGE_SNIPPETS: Record<string, string> = {
  python: `# Algorithmic Assessment Sandbox
# Target: Optimal Time and Space Complexity

def solve_problem(input_data: list[int]) -> int | None:
    """
    Computes maximum subarray sum using Kadane's algorithm.
    Time Complexity: O(n)
    Space Complexity: O(1)
    """
    if not input_data:
        return None

    max_so_far = input_data[0]
    curr_max = input_data[0]

    for x in input_data[1:]:
        curr_max = max(x, curr_max + x)
        max_so_far = max(max_so_far, curr_max)

    return max_so_far

if __name__ == "__main__":
    sample = [-2, 1, -3, 4, -1, 2, 1, -5, 4]
    result = solve_problem(sample)
    print(f"Input: {sample}")
    print(f"Max Subarray Sum: {result}")
`,
  javascript: `// Algorithmic Assessment Sandbox
// Target: Optimal Time and Space Complexity

function solveProblem(inputData) {
  if (!inputData || inputData.length === 0) return null;

  let maxSoFar = inputData[0];
  let currMax = inputData[0];

  for (let i = 1; i < inputData.length; i++) {
    currMax = Math.max(inputData[i], currMax + inputData[i]);
    maxSoFar = Math.max(maxSoFar, currMax);
  }

  return maxSoFar;
}

const sample = [-2, 1, -3, 4, -1, 2, 1, -5, 4];
console.log("Input:", sample);
console.log("Max Subarray Sum:", solveProblem(sample));
`,
  typescript: `// Algorithmic Assessment Sandbox
// Target: Optimal Time and Space Complexity

function solveProblem(inputData: number[]): number | null {
  if (!inputData || inputData.length === 0) return null;

  let maxSoFar = inputData[0];
  let currMax = inputData[0];

  for (let i = 1; i < inputData.length; i++) {
    currMax = Math.max(inputData[i], currMax + inputData[i]);
    maxSoFar = Math.max(maxSoFar, currMax);
  }

  return maxSoFar;
}

const sample: number[] = [-2, 1, -3, 4, -1, 2, 1, -5, 4];
console.log("Input:", sample);
console.log("Max Subarray Sum:", solveProblem(sample));
`,
  cpp: `#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

int solveProblem(const vector<int>& nums) {
    if (nums.empty()) return 0;
    int maxSoFar = nums[0];
    int currMax = nums[0];

    for (size_t i = 1; i < nums.size(); ++i) {
        currMax = max(nums[i], currMax + nums[i]);
        maxSoFar = max(maxSoFar, currMax);
    }
    return maxSoFar;
}

int main() {
    vector<int> sample = {-2, 1, -3, 4, -1, 2, 1, -5, 4};
    cout << "Max Subarray Sum: " << solveProblem(sample) << endl;
    return 0;
}
`,
  go: `package main

import (
	"fmt"
)

func solveProblem(nums []int) int {
	if len(nums) == 0 {
		return 0
	}
	maxSoFar := nums[0]
	currMax := nums[0]

	for _, x := range nums[1:] {
		if x > currMax+x {
			currMax = x
		} else {
			currMax += x
		}
		if currMax > maxSoFar {
			maxSoFar = currMax
		}
	}
	return maxSoFar
}

func main() {
	sample := []int{-2, 1, -3, 4, -1, 2, 1, -5, 4}
	fmt.Printf("Max Subarray Sum: %d\\n", solveProblem(sample))
}
`,
  rust: `fn solve_problem(nums: &[i32]) -> Option<i32> {
    if nums.is_empty() {
        return None;
    }
    let mut max_so_far = nums[0];
    let mut curr_max = nums[0];

    for &x in &nums[1..] {
        curr_max = curr_max.max(x + curr_max);
        max_so_far = max_so_far.max(curr_max);
    }
    Some(max_so_far)
}

fn main() {
    let sample = [-2, 1, -3, 4, -1, 2, 1, -5, 4];
    println!("Max Subarray Sum: {:?}", solve_problem(&sample));
}
`,
  java: `public class Solution {
    public static Integer solveProblem(int[] nums) {
        if (nums == null || nums.length == 0) return null;
        int maxSoFar = nums[0];
        int currMax = nums[0];

        for (int i = 1; i < nums.length; i++) {
            currMax = Math.max(nums[i], currMax + nums[i]);
            maxSoFar = Math.max(maxSoFar, currMax);
        }
        return maxSoFar;
    }

    public static void main(String[] args) {
        int[] sample = {-2, 1, -3, 4, -1, 2, 1, -5, 4};
        System.out.println("Max Subarray Sum: " + solveProblem(sample));
    }
}
`,
}

export function EnhancedCodeEditor({ sessionId, questionId, onCodeSubmit }: EnhancedCodeEditorProps) {
  const [language, setLanguage] = useState<string>("python")
  const [code, setCode] = useState<string>(LANGUAGE_SNIPPETS.python)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [evaluation, setEvaluation] = useState<CodeEvaluation | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [executionTime, setExecutionTime] = useState<number>(0)
  const [isRunning, setIsRunning] = useState(false)
  const [activeTab, setActiveTab] = useState<string>("console")
  const [runOutput, setRunOutput] = useState<{
    success?: boolean
    stdout?: string
    stderr?: string
    exit_code?: number
    error?: string
  } | null>(null)
  const [showResetConfirm, setShowResetConfirm] = useState(false)

  const typingStartTime = useRef<number>(Date.now())
  const keystrokes = useRef<number[]>([])

  useEffect(() => {
    try {
      const saved = localStorage.getItem(`ide_draft_${language}`)
      if (saved !== null) {
        setCode(saved)
        return
      }
    } catch (e) {}
    setCode(LANGUAGE_SNIPPETS[language] || "")
  }, [language])

  // Track keystroke cadence for behavioral integrity & handle shortcuts
  useEffect(() => {
    const handleKeydown = (e: KeyboardEvent) => {
      // Escape closes reset modal
      if (e.key === "Escape" && showResetConfirm) {
        e.preventDefault()
        setShowResetConfirm(false)
        return
      }

      // Ctrl+Enter or Cmd+Enter to execute code
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault()
        runCode()
        return
      }

      const now = Date.now()
      keystrokes.current.push(now)
      if (keystrokes.current.length > 20) {
        keystrokes.current = keystrokes.current.slice(-20)
      }
    }

    document.addEventListener("keydown", handleKeydown)
    return () => document.removeEventListener("keydown", handleKeydown)
  }, [code, language, showResetConfirm])

  const handleCodeChange = (value: string | undefined) => {
    const nextCode = value || ""
    setCode(nextCode)
    try {
      localStorage.setItem(`ide_draft_${language}`, nextCode)
    } catch (e) {}
  }

  const handleLanguageChange = (newLanguage: string) => {
    setLanguage(newLanguage)
    try {
      const saved = localStorage.getItem(`ide_draft_${newLanguage}`)
      if (saved !== null) {
        setCode(saved)
      } else {
        setCode(LANGUAGE_SNIPPETS[newLanguage] || "")
      }
    } catch (e) {
      setCode(LANGUAGE_SNIPPETS[newLanguage] || "")
    }
    setEvaluation(null)
    setRunOutput(null)
    setError(null)
  }

  const handleResetClick = () => {
    const starter = (LANGUAGE_SNIPPETS[language] || "").trim()
    if (code.trim() !== starter) {
      setShowResetConfirm(true)
    } else {
      performReset()
    }
  }

  const performReset = () => {
    try {
      localStorage.removeItem(`ide_draft_${language}`)
    } catch (e) {}
    setCode(LANGUAGE_SNIPPETS[language] || "")
    setEvaluation(null)
    setRunOutput(null)
    setError(null)
    setShowResetConfirm(false)
  }

  const runCode = async () => {
    if (!code.trim()) return

    setIsRunning(true)
    setError(null)
    setActiveTab("console")
    const t0 = Date.now()

    try {
      const res = await apiClient.runCode(code, language)
      setExecutionTime(Date.now() - t0)
      setRunOutput({
        success: res.success,
        stdout: res.stdout || "",
        stderr: res.stderr || "",
        exit_code: res.exit_code,
        error: res.error,
      })
    } catch (err: any) {
      setError(err?.message || "Sandbox execution failed.")
    } finally {
      setIsRunning(false)
    }
  }

  const submitCode = async () => {
    if (!code.trim() || !sessionId || !questionId) {
      setError("Missing active session or problem identity.")
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      const typingDuration = (Date.now() - typingStartTime.current) / 1000
      const keystrokeCount = keystrokes.current.length

      const result = await apiClient.submitCode(sessionId, questionId, code, language)
      setEvaluation(result.evaluation)
      setActiveTab("rubric")

      await apiClient.logEvent(sessionId, "code_submitted", {
        question_id: questionId,
        language,
        code_length: code.length,
        execution_time: executionTime,
        typing_duration: typingDuration,
        keystroke_count: keystrokeCount,
      })

      if (onCodeSubmit) {
        onCodeSubmit(result.evaluation)
      }
    } catch (err: any) {
      setError(err?.message || "Failed to submit code for rubric evaluation.")
    } finally {
      setIsSubmitting(false)
    }
  }

  const getMonacoLanguage = (lang: string): string => {
    const languageMap: Record<string, string> = {
      python: "python",
      javascript: "javascript",
      typescript: "typescript",
      java: "java",
      cpp: "cpp",
      go: "go",
      rust: "rust",
    }
    return languageMap[lang] || "plaintext"
  }

  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0b0f19] overflow-hidden shadow-xs">
      {/* Top Command Bar */}
      <div className="px-4 py-2.5 bg-slate-50 dark:bg-[#0d121f] border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center space-x-3">
          {/* Language Selector */}
          <div className="flex items-center space-x-2">
            <span className="text-[11px] font-mono uppercase text-slate-500">RUNTIME:</span>
            <Select value={language} onValueChange={handleLanguageChange}>
              <SelectTrigger className="h-8 w-36 text-xs font-mono bg-white dark:bg-[#111726] border-slate-200 dark:border-slate-700">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {LANGUAGE_OPTIONS.map((lang) => (
                  <SelectItem key={lang.value} value={lang.value} className="text-xs font-mono">
                    {lang.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="h-4 w-px bg-slate-200 dark:bg-slate-800" />

          {/* Action Buttons */}
          <Button
            size="sm"
            onClick={runCode}
            disabled={isRunning || !code.trim()}
            className="h-8 px-3 text-xs font-mono bg-slate-900 text-white hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900"
          >
            {isRunning ? (
              <>
                <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                Executing...
              </>
            ) : (
              <>
                <Play className="h-3.5 w-3.5 mr-1.5 fill-current" />
                Run Code
                <span className="ml-2 text-[10px] opacity-60">Ctrl+↵</span>
              </>
            )}
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={handleResetClick}
            className="h-8 px-2.5 text-xs font-mono border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800"
            title="Reset to starter implementation"
          >
            <RotateCcw className="h-3.5 w-3.5 mr-1" />
            Reset
          </Button>
        </div>

        <div className="flex items-center space-x-3">
          {executionTime > 0 && (
            <div className="flex items-center space-x-1.5 text-[11px] font-mono text-slate-500">
              <Clock className="h-3 w-3" />
              <span>{executionTime}ms</span>
            </div>
          )}

          {evaluation && (
            <Badge
              variant="outline"
              className={`font-mono text-xs px-2 py-0.5 ${
                evaluation.score >= 80
                  ? "border-emerald-500 text-emerald-500 bg-emerald-50/10"
                  : evaluation.score >= 60
                  ? "border-blue-500 text-blue-500 bg-blue-50/10"
                  : "border-amber-500 text-amber-500 bg-amber-50/10"
              }`}
            >
              RUBRIC SCORE: {evaluation.score}/100
            </Badge>
          )}

          {sessionId && questionId && (
            <Button
              size="sm"
              onClick={submitCode}
              disabled={isSubmitting || !code.trim()}
              className="h-8 px-3 text-xs font-mono bg-blue-600 hover:bg-blue-700 text-white"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                  Synthesizing Rubric...
                </>
              ) : (
                <>
                  <Sparkles className="h-3.5 w-3.5 mr-1.5" />
                  Submit Solution
                </>
              )}
            </Button>
          )}
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="px-4 py-2 border-b border-rose-200 dark:border-rose-900/50 bg-rose-50 dark:bg-rose-950/30 text-xs font-mono text-rose-600 dark:text-rose-400 flex items-center space-x-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Monaco Code Editor Pane */}
      <div className="border-b border-slate-200 dark:border-slate-800 bg-[#1e1e1e]">
        <Monaco
          value={code}
          onChange={handleCodeChange}
          language={getMonacoLanguage(language)}
          height="460px"
          onFocus={() => {
            typingStartTime.current = Date.now()
          }}
        />
      </div>

      {/* Bottom Panel: Console Execution & AI Evaluation Rubric */}
      <div className="bg-slate-50/50 dark:bg-[#0b0f19]">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <div className="px-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
            <TabsList className="h-9 bg-transparent p-0 space-x-4">
              <TabsTrigger
                value="console"
                className="h-9 rounded-none border-b-2 border-transparent data-[state=active]:border-slate-900 dark:data-[state=active]:border-slate-100 data-[state=active]:bg-transparent px-2 font-mono text-xs"
              >
                <Terminal className="h-3.5 w-3.5 mr-1.5" />
                Sandbox Console Output
                {runOutput && (
                  <span
                    className={`ml-2 w-1.5 h-1.5 rounded-full ${
                      runOutput.exit_code === 0 ? "bg-emerald-500" : "bg-rose-500"
                    }`}
                  />
                )}
              </TabsTrigger>

              {evaluation && (
                <TabsTrigger
                  value="rubric"
                  className="h-9 rounded-none border-b-2 border-transparent data-[state=active]:border-slate-900 dark:data-[state=active]:border-slate-100 data-[state=active]:bg-transparent px-2 font-mono text-xs"
                >
                  <Sparkles className="h-3.5 w-3.5 mr-1.5 text-blue-500" />
                  AI Evaluation Rubric
                  <Badge variant="outline" className="ml-2 text-[10px] font-mono px-1 py-0">
                    {evaluation.score}/100
                  </Badge>
                </TabsTrigger>
              )}
            </TabsList>

            {runOutput && activeTab === "console" && (
              <div className="text-[11px] font-mono text-slate-500 flex items-center space-x-2">
                <span>EXIT CODE:</span>
                <span
                  className={runOutput.exit_code === 0 ? "text-emerald-500 font-bold" : "text-rose-500 font-bold"}
                >
                  {runOutput.exit_code ?? (runOutput.success ? 0 : 1)}
                </span>
              </div>
            )}
          </div>

          {/* Console Tab */}
          <TabsContent value="console" className="m-0 p-4 font-mono text-xs bg-slate-950 text-slate-100 min-h-[140px] max-h-[260px] overflow-y-auto">
            {runOutput ? (
              <div className="space-y-3">
                {runOutput.stdout && (
                  <div>
                    <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Standard Output</div>
                    <pre className="text-emerald-300 font-mono text-xs whitespace-pre-wrap leading-relaxed">
                      {runOutput.stdout}
                    </pre>
                  </div>
                )}
                {runOutput.stderr && (
                  <div>
                    <div className="text-[10px] text-rose-400 uppercase tracking-wider mb-1">Standard Error</div>
                    <pre className="text-rose-400 font-mono text-xs whitespace-pre-wrap leading-relaxed">
                      {runOutput.stderr}
                    </pre>
                  </div>
                )}
                {runOutput.error && (
                  <div className="text-rose-400">
                    <span className="font-bold">Error:</span> {runOutput.error}
                  </div>
                )}
                {!runOutput.stdout && !runOutput.stderr && !runOutput.error && (
                  <div className="text-slate-500 italic">Process completed with code 0. No stdout or stderr emitted.</div>
                )}
              </div>
            ) : (
              <div className="h-28 flex flex-col items-center justify-center text-slate-500 space-y-1">
                <Terminal className="h-5 w-5 opacity-40" />
                <span className="text-[11px]">Click &quot;Run Code&quot; (or Ctrl+Enter) to execute in the sandbox.</span>
              </div>
            )}
          </TabsContent>

          {/* Rubric Tab */}
          {evaluation && (
            <TabsContent value="rubric" className="m-0 p-5 space-y-5">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f]">
                  <div className="text-[10px] font-mono text-slate-500 uppercase">Correctness</div>
                  <div className="text-lg font-bold font-mono text-slate-900 dark:text-slate-100 mt-0.5">
                    {evaluation.correctness}/100
                  </div>
                  <Progress value={evaluation.correctness} className="h-1 mt-1.5" />
                </div>
                <div className="p-3 rounded border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f]">
                  <div className="text-[10px] font-mono text-slate-500 uppercase">Efficiency</div>
                  <div className="text-lg font-bold font-mono text-slate-900 dark:text-slate-100 mt-0.5">
                    {evaluation.efficiency}/100
                  </div>
                  <Progress value={evaluation.efficiency} className="h-1 mt-1.5" />
                </div>
                <div className="p-3 rounded border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f]">
                  <div className="text-[10px] font-mono text-slate-500 uppercase">Code Quality</div>
                  <div className="text-lg font-bold font-mono text-slate-900 dark:text-slate-100 mt-0.5">
                    {evaluation.code_quality}/100
                  </div>
                  <Progress value={evaluation.code_quality} className="h-1 mt-1.5" />
                </div>
                <div className="p-3 rounded border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f]">
                  <div className="text-[10px] font-mono text-slate-500 uppercase">Readability</div>
                  <div className="text-lg font-bold font-mono text-slate-900 dark:text-slate-100 mt-0.5">
                    {evaluation.readability}/100
                  </div>
                  <Progress value={evaluation.readability} className="h-1 mt-1.5" />
                </div>
              </div>

              {/* Big-O Complexity Signals */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] flex items-center justify-between">
                  <span className="font-mono text-slate-500">Time Complexity:</span>
                  <span className="font-mono font-semibold text-slate-900 dark:text-slate-100">
                    {evaluation.time_complexity || "O(n)"}
                  </span>
                </div>
                <div className="p-3 rounded border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] flex items-center justify-between">
                  <span className="font-mono text-slate-500">Space Complexity:</span>
                  <span className="font-mono font-semibold text-slate-900 dark:text-slate-100">
                    {evaluation.space_complexity || "O(1)"}
                  </span>
                </div>
              </div>

              {/* Feedback Summary */}
              {evaluation.feedback && (
                <div className="p-3.5 rounded border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                  <span className="font-mono text-[10px] uppercase text-slate-500 block mb-1">
                    Evaluator Feedback
                  </span>
                  {evaluation.feedback}
                </div>
              )}

              {/* ML Defect & Vulnerability Intelligence */}
              {evaluation.ml_defect_detection && (
                <div className={`p-3.5 rounded border text-xs ${
                  evaluation.ml_defect_detection.risk_band === 'high'
                    ? 'border-rose-300 dark:border-rose-900/60 bg-rose-50/30 dark:bg-rose-950/20'
                    : evaluation.ml_defect_detection.risk_band === 'medium'
                    ? 'border-amber-300 dark:border-amber-900/60 bg-amber-50/30 dark:bg-amber-950/20'
                    : 'border-emerald-300 dark:border-emerald-900/60 bg-emerald-50/30 dark:bg-emerald-950/20'
                }`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <ShieldCheck className={`h-4 w-4 ${
                        evaluation.ml_defect_detection.risk_band === 'high' ? 'text-rose-500' :
                        evaluation.ml_defect_detection.risk_band === 'medium' ? 'text-amber-500' : 'text-emerald-500'
                      }`} />
                      <span className="font-mono text-[10px] uppercase font-bold tracking-wider text-slate-700 dark:text-slate-300">
                        CodeBERT Defect Intelligence (ML Risk Signal)
                      </span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase ${
                        evaluation.ml_defect_detection.risk_band === 'high'
                          ? 'bg-rose-100 text-rose-800 dark:bg-rose-900/50 dark:text-rose-300'
                          : evaluation.ml_defect_detection.risk_band === 'medium'
                          ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-300'
                          : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300'
                      }`}>
                        {evaluation.ml_defect_detection.risk_band} Risk
                      </span>
                      <span className="text-[10px] font-mono text-slate-500">
                        p(defect) = {(evaluation.ml_defect_detection.defect_probability * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 py-1 text-[11px] font-mono text-slate-600 dark:text-slate-400">
                    <div>
                      <span className="text-slate-400 dark:text-slate-500 block text-[9px] uppercase">Confidence</span>
                      <span className="font-semibold text-slate-800 dark:text-slate-200">
                        {(evaluation.ml_defect_detection.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 dark:text-slate-500 block text-[9px] uppercase">Latency</span>
                      <span className="font-semibold text-slate-800 dark:text-slate-200">
                        {evaluation.ml_defect_detection.inference_time_ms ? `${evaluation.ml_defect_detection.inference_time_ms.toFixed(0)}ms` : 'sub-100ms'}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 dark:text-slate-500 block text-[9px] uppercase">Encoder Head</span>
                      <span className="font-semibold text-slate-800 dark:text-slate-200">
                        {evaluation.ml_defect_detection.is_fine_tuned ? 'Fine-tuned' : 'Base CodeBERT'}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 dark:text-slate-500 block text-[9px] uppercase">Model Version</span>
                      <span className="font-semibold text-slate-800 dark:text-slate-200 truncate block">
                        {evaluation.ml_defect_detection.model_version}
                      </span>
                    </div>
                  </div>

                  {evaluation.ml_defect_detection.risk_indicators && evaluation.ml_defect_detection.risk_indicators.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-slate-200/60 dark:border-slate-800/60">
                      <span className="text-[10px] font-mono uppercase text-slate-500 block mb-1">
                        Detected Vulnerability & Bug Patterns:
                      </span>
                      <ul className="space-y-1">
                        {evaluation.ml_defect_detection.risk_indicators.map((ind, i) => (
                          <li key={i} className="flex items-center space-x-1.5 text-[11px] text-slate-700 dark:text-slate-300">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0" />
                            <span>{ind}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <p className="mt-2 text-[10px] text-slate-400 dark:text-slate-500 italic">
                    Note: ML defect probability serves as an advisory safety signal alongside runtime test execution and AI reasoning.
                  </p>
                </div>
              )}

              {/* Strengths & Improvements */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                {evaluation.strengths && evaluation.strengths.length > 0 && (
                  <div className="p-3 rounded border border-emerald-200 dark:border-emerald-900/40 bg-emerald-50/20 dark:bg-emerald-950/10">
                    <span className="font-mono text-[10px] uppercase text-emerald-600 dark:text-emerald-400 font-semibold block mb-2">
                      Verified Strengths
                    </span>
                    <ul className="space-y-1.5">
                      {evaluation.strengths.map((s, i) => (
                        <li key={i} className="flex items-start space-x-1.5 text-slate-700 dark:text-slate-300">
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0 mt-0.5" />
                          <span>{s}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {evaluation.improvements && evaluation.improvements.length > 0 && (
                  <div className="p-3 rounded border border-amber-200 dark:border-amber-900/40 bg-amber-50/20 dark:bg-amber-950/10">
                    <span className="font-mono text-[10px] uppercase text-amber-600 dark:text-amber-400 font-semibold block mb-2">
                      Remediation Targets
                    </span>
                    <ul className="space-y-1.5">
                      {evaluation.improvements.map((imp, i) => (
                        <li key={i} className="flex items-start space-x-1.5 text-slate-700 dark:text-slate-300">
                          <AlertCircle className="h-3.5 w-3.5 text-amber-500 shrink-0 mt-0.5" />
                          <span>{imp}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </TabsContent>
          )}
        </Tabs>
      </div>

      {/* Accessible Reset Confirmation Modal */}
      {showResetConfirm && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="ide-reset-title"
          onClick={() => setShowResetConfirm(false)}
        >
          <div
            className="w-full max-w-sm rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0d121f] p-5 shadow-xl space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div>
              <h2 id="ide-reset-title" className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                Reset Editor to Starter Template?
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
                This will overwrite your current solution with the default starter template for {LANGUAGE_OPTIONS.find((l) => l.value === language)?.label || language}. This action cannot be undone.
              </p>
            </div>
            <div className="flex justify-end gap-2 pt-1 border-t border-slate-100 dark:border-slate-800/80">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowResetConfirm(false)}
                className="text-xs h-8"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={performReset}
                className="text-xs h-8"
              >
                Reset Code
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
