import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { message, artifact } = body;

    // Call the backend canvas API
    const response = await fetch(`${process.env.BACKEND_URL || 'http://localhost:8032'}/canvas/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        artifact,
      }),
    });

    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Canvas chat API error:", error);
    return NextResponse.json(
      { error: "Failed to process canvas chat request" },
      { status: 500 }
    );
  }
}