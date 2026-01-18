import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

interface Props {
  action: string;
  emotion: string;
  sceneIndex: number;
  progress: number;
}

// Consistent stick figure design - same proportions across all poses
const FIGURE_COLOR = "#00ff88";
const HEAD_RADIUS = 40;
const BODY_LENGTH = 120;
const ARM_LENGTH = 80;
const LEG_LENGTH = 100;
const STROKE_WIDTH = 8;

export const StickFigure: React.FC<Props> = ({ action, emotion, sceneIndex, progress }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Smooth animation spring
  const bounce = spring({ frame, fps, config: { damping: 12, stiffness: 100 } });

  // Get pose based on scene action
  const pose = getPoseForAction(action, sceneIndex, progress, bounce);

  // Emotion affects head expression
  const expression = getExpressionForEmotion(emotion);

  return (
    <svg
      width="400"
      height="500"
      viewBox="0 0 400 500"
      style={{ overflow: "visible" }}
    >
      {/* Head */}
      <circle
        cx={200 + pose.headX}
        cy={60 + pose.headY}
        r={HEAD_RADIUS}
        fill="none"
        stroke={FIGURE_COLOR}
        strokeWidth={STROKE_WIDTH}
      />

      {/* Face expression */}
      <g transform={`translate(${200 + pose.headX}, ${60 + pose.headY})`}>
        {/* Eyes */}
        <circle cx={-12} cy={-5} r={expression.eyeSize} fill={FIGURE_COLOR} />
        <circle cx={12} cy={-5} r={expression.eyeSize} fill={FIGURE_COLOR} />
        
        {/* Mouth */}
        <path
          d={expression.mouthPath}
          fill="none"
          stroke={FIGURE_COLOR}
          strokeWidth={4}
          strokeLinecap="round"
        />
      </g>

      {/* Neck to Body */}
      <line
        x1={200 + pose.headX}
        y1={100 + pose.headY}
        x2={200}
        y2={100 + BODY_LENGTH}
        stroke={FIGURE_COLOR}
        strokeWidth={STROKE_WIDTH}
        strokeLinecap="round"
      />

      {/* Left Arm */}
      <line
        x1={200}
        y1={130}
        x2={200 - ARM_LENGTH * Math.cos(pose.leftArmAngle)}
        y2={130 + ARM_LENGTH * Math.sin(pose.leftArmAngle)}
        stroke={FIGURE_COLOR}
        strokeWidth={STROKE_WIDTH}
        strokeLinecap="round"
      />

      {/* Right Arm */}
      <line
        x1={200}
        y1={130}
        x2={200 + ARM_LENGTH * Math.cos(pose.rightArmAngle)}
        y2={130 + ARM_LENGTH * Math.sin(pose.rightArmAngle)}
        stroke={FIGURE_COLOR}
        strokeWidth={STROKE_WIDTH}
        strokeLinecap="round"
      />

      {/* Left Leg */}
      <line
        x1={200}
        y1={220}
        x2={200 - LEG_LENGTH * Math.sin(pose.leftLegAngle)}
        y2={220 + LEG_LENGTH * Math.cos(pose.leftLegAngle)}
        stroke={FIGURE_COLOR}
        strokeWidth={STROKE_WIDTH}
        strokeLinecap="round"
      />

      {/* Right Leg */}
      <line
        x1={200}
        y1={220}
        x2={200 + LEG_LENGTH * Math.sin(pose.rightLegAngle)}
        y2={220 + LEG_LENGTH * Math.cos(pose.rightLegAngle)}
        stroke={FIGURE_COLOR}
        strokeWidth={STROKE_WIDTH}
        strokeLinecap="round"
      />
    </svg>
  );
};

function getPoseForAction(action: string, sceneIndex: number, progress: number, bounce: number) {
  // Base poses for different actions
  const poses: Record<number, any> = {
    0: { // Thinking/curious
      headX: Math.sin(progress * Math.PI) * 5,
      headY: 0,
      leftArmAngle: 0.8,
      rightArmAngle: 0.3 + bounce * 0.2,
      leftLegAngle: 0.2,
      rightLegAngle: -0.2,
    },
    1: { // Holding phone
      headX: -10,
      headY: 5,
      leftArmAngle: 1.2,
      rightArmAngle: 1.5,
      leftLegAngle: 0.1,
      rightLegAngle: -0.1,
    },
    2: { // Sorting/organizing
      headX: Math.sin(progress * Math.PI * 2) * 10,
      headY: 0,
      leftArmAngle: 0.5 + Math.sin(progress * Math.PI * 4) * 0.3,
      rightArmAngle: 0.5 - Math.sin(progress * Math.PI * 4) * 0.3,
      leftLegAngle: 0.15,
      rightLegAngle: -0.15,
    },
    3: { // Pointing at AI
      headX: 0,
      headY: 0,
      leftArmAngle: 0.8,
      rightArmAngle: -0.5 + bounce * 0.1,
      leftLegAngle: 0.2,
      rightLegAngle: -0.2,
    },
    4: { // Walking among icons
      headX: Math.sin(progress * Math.PI * 3) * 5,
      headY: Math.abs(Math.sin(progress * Math.PI * 6)) * -10,
      leftArmAngle: 0.5 + Math.sin(progress * Math.PI * 6) * 0.3,
      rightArmAngle: 0.5 - Math.sin(progress * Math.PI * 6) * 0.3,
      leftLegAngle: Math.sin(progress * Math.PI * 6) * 0.4,
      rightLegAngle: -Math.sin(progress * Math.PI * 6) * 0.4,
    },
    5: { // Operating conveyor
      headX: -5,
      headY: 0,
      leftArmAngle: 0.3 + Math.sin(progress * Math.PI * 2) * 0.2,
      rightArmAngle: 0.8,
      leftLegAngle: 0.15,
      rightLegAngle: -0.15,
    },
    6: { // Watering plant
      headX: 0,
      headY: -5,
      leftArmAngle: 1.0,
      rightArmAngle: -0.3,
      leftLegAngle: 0.2,
      rightLegAngle: -0.2,
    },
    7: { // Arms wide open celebration
      headX: 0,
      headY: -5 * bounce,
      leftArmAngle: -0.8,
      rightArmAngle: -0.8,
      leftLegAngle: 0.3,
      rightLegAngle: -0.3,
    },
  };

  return poses[sceneIndex] || poses[0];
}

function getExpressionForEmotion(emotion: string) {
  const expressions: Record<string, { eyeSize: number; mouthPath: string }> = {
    Curious: { eyeSize: 6, mouthPath: "M -8 12 Q 0 8 8 12" },
    Engaged: { eyeSize: 5, mouthPath: "M -10 10 Q 0 16 10 10" },
    Focused: { eyeSize: 4, mouthPath: "M -8 12 L 8 12" },
    Informative: { eyeSize: 5, mouthPath: "M -10 10 Q 0 14 10 10" },
    Adaptable: { eyeSize: 5, mouthPath: "M -10 10 Q 0 16 10 10" },
    Concentrated: { eyeSize: 4, mouthPath: "M -6 12 L 6 12" },
    Optimistic: { eyeSize: 6, mouthPath: "M -12 8 Q 0 20 12 8" },
    Excited: { eyeSize: 7, mouthPath: "M -14 6 Q 0 22 14 6" },
  };

  return expressions[emotion] || expressions.Curious;
}
