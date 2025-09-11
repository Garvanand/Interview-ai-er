import { streamText } from "ai"
import { google } from "@ai-sdk/google"

export async function POST(req: Request) {
  const { prompt } = await req.json().catch(() => ({}))
  if (!prompt) {
    return new Response(JSON.stringify({ error: "Missing prompt" }), { status: 400 })
  }

  if (!process.env.GOOGLE_GENERATIVE_AI_API_KEY) {
    return new Response(
      JSON.stringify({ error: "Missing GOOGLE_GENERATIVE_AI_API_KEY. Add it in Project Settings." }),
      { status: 400 },
    )
  }

  // Stream from Gemini
  const result = await streamText({
    model: google("models/gemini-1.5-flash"),
    prompt,
  })

  // Return as plain text stream for easy client consumption
  // Convert ReadableStream<string> to ReadableStream<Uint8Array>
  const encoder = new TextEncoder()
  const transform = new TransformStream<string, Uint8Array>({
    transform(chunk, controller) {
      controller.enqueue(encoder.encode(chunk))
    },
  })

  // @ts-expect-error - textStream is a ReadableStream<string>
  const readable = result.textStream.pipeThrough(transform)
  return new Response(readable, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-store",
    },
  })
}
