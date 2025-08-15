"use client";

import { Canvas } from "@/components/canvas";
import { CanvasProvider } from "@/contexts/canvas-context";

export default function CanvasPage() {
  return (
    <CanvasProvider>
      <Canvas />
    </CanvasProvider>
  );
}