import { NextResponse } from "next/server"
import { generateText } from "ai"
import { google } from "@ai-sdk/google"

export async function POST(req: Request) {
  const { prompt } = await req.json().catch(() => ({}))
  if (!prompt) return NextResponse.json({ error: "Missing prompt" }, { status: 400 })

  if (!process.env.GOOGLE_GENERATIVE_AI_API_KEY) {
    return NextResponse.json(
      { error: "Missing GOOGLE_GENERATIVE_AI_API_KEY. Add it in Project Settings." },
      { status: 400 },
    )
  }

  try {
    const { text } = await generateText({
      model: google("models/gemini-1.5-flash"),
      prompt,
    })
    return NextResponse.json({ text })
  } catch (e: any) {
    return NextResponse.json({ error: e?.message || "AI error" }, { status: 500 })
  }
}
