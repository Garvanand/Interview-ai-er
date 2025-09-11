"use client"

import { useRef, useEffect } from 'react'
import { Editor } from '@monaco-editor/react'

interface CodeEditorProps {
  value: string
  onChange: (value: string | undefined) => void
  language: string
  onFocus?: () => void
  height?: string
  readOnly?: boolean
}

export default function CodeEditor({ 
  value, 
  onChange, 
  language, 
  onFocus,
  height = "500px",
  readOnly = false 
}: CodeEditorProps) {
  const editorRef = useRef<any>(null)

  const handleEditorDidMount = (editor: any) => {
    editorRef.current = editor
    
    // Set editor options
    editor.updateOptions({
      minimap: { enabled: false },
      fontSize: 14,
      lineNumbers: 'on',
      roundedSelection: false,
      scrollBeyondLastLine: false,
      automaticLayout: true,
      theme: 'vs-dark',
      wordWrap: 'on',
      folding: true,
      showFoldingControls: 'always',
      renderLineHighlight: 'all',
      selectOnLineNumbers: true,
      cursorBlinking: 'smooth',
      cursorSmoothCaretAnimation: 'on',
      smoothScrolling: true,
      tabSize: 2,
      insertSpaces: true,
      detectIndentation: true,
      trimAutoWhitespace: true,
      largeFileOptimizations: true,
      suggestOnTriggerCharacters: true,
      acceptSuggestionOnEnter: 'on',
      tabCompletion: 'on',
      wordBasedSuggestions: 'off',
      parameterHints: {
        enabled: true,
        cycle: true
      },
      autoIndent: 'full',
      formatOnPaste: true,
      formatOnType: true,
      suggest: {
        insertMode: 'replace',
        showKeywords: true,
        showSnippets: true,
        showClasses: true,
        showFunctions: true,
        showVariables: true,
        showConstants: true,
        showEnums: true,
        showModules: true,
        showProperties: true,
        showEvents: true,
        showOperators: true,
        showUnits: true,
        showValues: true,
        showColors: true,
        showFiles: true,
        showReferences: true,
        showFolders: true,
        showTypeParameters: true,
        showWords: true,
        showColors: true,
        showFiles: true,
        showReferences: true,
        showFolders: true,
        showTypeParameters: true,
        showWords: true
      }
    })

    // Focus event
    if (onFocus) {
      editor.onDidFocusEditorWidget(() => {
        onFocus()
      })
    }

    // Add custom keybindings
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      // Save functionality can be added here
      console.log('Save triggered')
    })

    // Add custom actions
    editor.addAction({
      id: 'format-code',
      label: 'Format Code',
      keybindings: [
        monaco.KeyMod.Shift | monaco.KeyMod.Alt | monaco.KeyCode.KeyF
      ],
      contextMenuGroupId: '1_modification',
      run: (editor) => {
        editor.getAction('editor.action.formatDocument').run()
      }
    })

    // Add comment/uncomment action
    editor.addAction({
      id: 'toggle-comment',
      label: 'Toggle Comment',
      keybindings: [
        monaco.KeyMod.CtrlCmd | monaco.KeyCode.Slash
      ],
      contextMenuGroupId: '1_modification',
      run: (editor) => {
        editor.getAction('editor.action.commentLine').run()
      }
    })
  }

  const handleEditorChange = (value: string | undefined) => {
    onChange(value)
  }

  return (
    <div className="w-full">
      <Editor
        height={height}
        defaultLanguage={language}
        language={language}
        value={value}
        onChange={handleEditorChange}
        onMount={handleEditorDidMount}
        options={{
          readOnly,
          automaticLayout: true,
          scrollBeyondLastLine: false,
          minimap: { enabled: false },
          fontSize: 14,
          lineNumbers: 'on',
          roundedSelection: false,
          theme: 'vs-dark',
          wordWrap: 'on',
          folding: true,
          showFoldingControls: 'always',
          renderLineHighlight: 'all',
          selectOnLineNumbers: true,
          cursorBlinking: 'smooth',
          cursorSmoothCaretAnimation: 'on',
          smoothScrolling: true,
          tabSize: 2,
          insertSpaces: true,
          detectIndentation: true,
          trimAutoWhitespace: true,
          largeFileOptimizations: true,
          suggestOnTriggerCharacters: true,
          acceptSuggestionOnEnter: 'on',
          tabCompletion: 'on',
          wordBasedSuggestions: 'off',
          parameterHints: {
            enabled: true,
            cycle: true
          },
          autoIndent: 'full',
          formatOnPaste: true,
          formatOnType: true
        }}
        theme="vs-dark"
      />
    </div>
  )
}
