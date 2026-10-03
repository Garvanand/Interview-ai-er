export async function POST(req: Request) {
  const { prompt } = await req.json().catch(() => ({}))
  if (!prompt) {
    return new Response(JSON.stringify({ error: "Missing prompt" }), { status: 400 })
  }

  const groqApiKey = process.env.GROQ_API_KEY
  const geminiApiKey = process.env.GOOGLE_GENERATIVE_AI_API_KEY || process.env.GEMINI_API_KEY

  if (groqApiKey) {
    const model = process.env.GROQ_MODEL || "llama-3.3-70b-versatile"
    const groqRes = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${groqApiKey}`,
      },
      body: JSON.stringify({
        model,
        messages: [
          {
            role: "system",
            content: "You are an expert technical interview and systems architecture advisor. Provide concise, rigorous, and technical guidance.",
          },
          { role: "user", content: prompt },
        ],
        temperature: 1,
        max_completion_tokens: 2048,
        top_p: 1,
        reasoning_effort: "medium",
        stream: true,
      }),
    })

    if (!groqRes.ok || !groqRes.body) {
      const errText = await groqRes.text().catch(() => "")
      return new Response(JSON.stringify({ error: `Groq error: ${errText}` }), { status: groqRes.status })
    }

    const encoder = new TextEncoder()
    const decoder = new TextDecoder()
    const reader = groqRes.body.getReader()

    const readable = new ReadableStream({
      async start(controller) {
        let buffer = ""
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split("\n")
          buffer = lines.pop() || ""

          for (const line of lines) {
            const trimmed = line.trim()
            if (!trimmed || trimmed.startsWith(":")) continue
            if (trimmed === "data: [DONE]") {
              controller.close()
              return
            }
            if (trimmed.startsWith("data: ")) {
              try {
                const parsed = JSON.parse(trimmed.slice(6))
                const delta = parsed.choices?.[0]?.delta?.content || ""
                if (delta) {
                  controller.enqueue(encoder.encode(delta))
                }
              } catch {
                // Ignore parse errors on incomplete SSE chunks
              }
            }
          }
        }
        controller.close()
      },
    })

    return new Response(readable, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "no-store",
      },
    })
  }

  // Fallback to Gemini if configured
  if (geminiApiKey) {
    const { streamText } = await import("ai")
    const { google } = await import("@ai-sdk/google")
    const result = await streamText({
      model: google("models/gemini-1.5-flash"),
      prompt,
    })
    const encoder = new TextEncoder()
    const transform = new TransformStream<string, Uint8Array>({
      transform(chunk, controller) {
        controller.enqueue(encoder.encode(chunk))
      },
    })
    const readable = (result.textStream as any).pipeThrough(transform)
    return new Response(readable, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "no-store",
      },
    })
  }

  return new Response(
    JSON.stringify({ error: "Missing GROQ_API_KEY or GEMINI_API_KEY in environment variables." }),
    { status: 400 },
  )
}
