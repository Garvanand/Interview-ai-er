"use client"

import { EnhancedCodeEditor } from '@/components/ide/enhanced-code-editor'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Code2, Play, BookOpen, Zap } from 'lucide-react'

export default function IDEPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold">Code IDE</h1>
          <p className="text-xl text-muted-foreground">
            Write, run, and evaluate code with AI-powered analysis
          </p>
        </div>

        {/* Features Overview */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Code2 className="h-5 w-5 text-blue-600" />
                Multi-Language Support
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Support for Python, JavaScript, TypeScript, Java, C++, C#, Go, and Rust with syntax highlighting and intelligent code completion.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Play className="h-5 w-5 text-green-600" />
                Code Execution
              </CardTitle>
            </CardContent>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Run your code in a safe environment and see real-time output. Perfect for testing algorithms and data structures.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-purple-600" />
                AI Evaluation
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Get instant feedback on code quality, correctness, efficiency, and best practices with detailed scoring breakdown.
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Enhanced Code Editor */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="h-5 w-5" />
              Code Editor & Evaluation
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Write your code, run it, and submit for AI-powered evaluation
            </p>
          </CardHeader>
          <CardContent>
            <EnhancedCodeEditor />
          </CardContent>
        </Card>

        {/* Additional Information */}
        <Card>
          <CardHeader>
            <CardTitle>How to Use</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="font-medium mb-2">Getting Started</h4>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• Select your programming language from the dropdown</li>
                  <li>• Write or modify the provided code template</li>
                  <li>• Use the "Run Code" button to test your solution</li>
                  <li>• Submit your code for comprehensive evaluation</li>
                </ul>
              </div>
              <div>
                <h4 className="font-medium mb-2">Evaluation Criteria</h4>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• Code Quality: Readability and structure</li>
                  <li>• Correctness: Logical accuracy</li>
                  <li>• Efficiency: Time and space complexity</li>
                  <li>• Best Practices: Coding standards and conventions</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
