import { NextResponse } from "next/server"

export async function POST(req: Request) {
  const { language, code } = await req.json().catch(() => ({}))
  if (!language || !code) {
    return NextResponse.json({ error: "Missing language or code" }, { status: 400 })
  }
  const supported = ["javascript", "typescript", "python"]
  if (!supported.includes(language)) {
    return NextResponse.json({ error: `Unsupported language: ${language}` }, { status: 400 })
  }
  return NextResponse.json({ output: `Executed ${language} code (${code.length} chars)` })
}
