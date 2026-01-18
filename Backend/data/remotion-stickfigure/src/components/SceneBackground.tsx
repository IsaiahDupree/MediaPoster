import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

interface Scene {
  start_time: number;
  end_time: number;
  scene_title: string;
  stick_figure_action: string;
  visual_elements: string[];
  emotion: string;
}

interface Props {
  scene: Scene;
  progress: number;
}

const ACCENT_COLOR = "#00ff88";
const SECONDARY_COLOR = "#ff6b6b";

export const SceneBackground: React.FC<Props> = ({ scene, progress }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const fadeIn = interpolate(progress, [0, 0.1], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill>
      {/* Gradient background */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: `linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)`,
        }}
      />

      {/* Animated grid pattern */}
      <svg
        style={{
          position: "absolute",
          inset: 0,
          opacity: 0.1,
        }}
        width="100%"
        height="100%"
      >
        <defs>
          <pattern id="grid" width="60" height="60" patternUnits="userSpaceOnUse">
            <path
              d="M 60 0 L 0 0 0 60"
              fill="none"
              stroke={ACCENT_COLOR}
              strokeWidth="1"
            />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
      </svg>

      {/* Visual elements for the scene */}
      <div
        style={{
          position: "absolute",
          top: 100,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          flexWrap: "wrap",
          gap: 20,
          padding: 40,
          opacity: fadeIn,
        }}
      >
        {scene.visual_elements.map((element, index) => (
          <VisualElement key={index} text={element} index={index} progress={progress} />
        ))}
      </div>
    </AbsoluteFill>
  );
};

const VisualElement: React.FC<{ text: string; index: number; progress: number }> = ({
  text,
  index,
  progress,
}) => {
  const delay = index * 0.1;
  const elementProgress = Math.max(0, Math.min(1, (progress - delay) * 2));

  // Determine icon based on text content
  const icon = getIconForElement(text);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 10,
        opacity: elementProgress,
        transform: `translateY(${(1 - elementProgress) * 30}px) scale(${0.8 + elementProgress * 0.2})`,
      }}
    >
      {/* Icon */}
      <div
        style={{
          width: 80,
          height: 80,
          borderRadius: 20,
          background: `linear-gradient(135deg, ${ACCENT_COLOR}20, ${ACCENT_COLOR}40)`,
          border: `2px solid ${ACCENT_COLOR}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 40,
        }}
      >
        {icon}
      </div>

      {/* Label */}
      <div
        style={{
          color: "#ffffff",
          fontSize: 16,
          fontFamily: "Arial, sans-serif",
          textAlign: "center",
          maxWidth: 120,
          textShadow: "1px 1px 2px rgba(0,0,0,0.5)",
        }}
      >
        {text.replace(/^Text: |^Icon of /g, "")}
      </div>
    </div>
  );
};

function getIconForElement(text: string): string {
  const lowerText = text.toLowerCase();

  if (lowerText.includes("thought") || lowerText.includes("question")) return "💭";
  if (lowerText.includes("smartphone") || lowerText.includes("phone")) return "📱";
  if (lowerText.includes("url")) return "🔗";
  if (lowerText.includes("thumbs-up")) return "👍";
  if (lowerText.includes("thumbs-down")) return "👎";
  if (lowerText.includes("folder") || lowerText.includes("filing")) return "📁";
  if (lowerText.includes("computer") || lowerText.includes("ai")) return "🤖";
  if (lowerText.includes("arrow") || lowerText.includes("data")) return "📊";
  if (lowerText.includes("video")) return "🎬";
  if (lowerText.includes("article")) return "📄";
  if (lowerText.includes("social")) return "📲";
  if (lowerText.includes("conveyor") || lowerText.includes("belt")) return "⚙️";
  if (lowerText.includes("bin") || lowerText.includes("good")) return "✅";
  if (lowerText.includes("bad")) return "❌";
  if (lowerText.includes("plant") || lowerText.includes("tree")) return "🌱";
  if (lowerText.includes("water")) return "💧";
  if (lowerText.includes("2026") || lowerText.includes("future")) return "🚀";
  if (lowerText.includes("sparkle")) return "✨";
  if (lowerText.includes("analyz")) return "📈";

  return "💡";
}
