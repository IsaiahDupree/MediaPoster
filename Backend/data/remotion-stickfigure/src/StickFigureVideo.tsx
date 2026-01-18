import React from "react";
import { AbsoluteFill, Audio, Sequence, useCurrentFrame, useVideoConfig, staticFile } from "remotion";
import { StickFigure } from "./components/StickFigure";
import { SceneBackground } from "./components/SceneBackground";

interface Scene {
  start_time: number;
  end_time: number;
  scene_title: string;
  stick_figure_action: string;
  visual_elements: string[];
  emotion: string;
}

interface Props {
  scenes: Scene[];
  audioSrc: string;
}

export const StickFigureVideo: React.FC<Props> = ({ scenes, audioSrc }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTime = frame / fps;

  // Find current scene
  const currentScene = scenes.find(
    (scene) => currentTime >= scene.start_time && currentTime < scene.end_time
  ) || scenes[0];

  const sceneIndex = scenes.indexOf(currentScene);

  return (
    <AbsoluteFill style={{ backgroundColor: "#1a1a2e" }}>
      {/* Audio track */}
      <Audio src={staticFile("audio_DTJQ6Skks0k.mp3")} />

      {/* Scene background with visual elements */}
      <SceneBackground
        scene={currentScene}
        progress={(currentTime - currentScene.start_time) / (currentScene.end_time - currentScene.start_time)}
      />

      {/* Stick figure */}
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <StickFigure
          action={currentScene.stick_figure_action}
          emotion={currentScene.emotion}
          sceneIndex={sceneIndex}
          progress={(currentTime - currentScene.start_time) / (currentScene.end_time - currentScene.start_time)}
        />
      </AbsoluteFill>

      {/* Scene title overlay */}
      <div
        style={{
          position: "absolute",
          bottom: 100,
          left: 0,
          right: 0,
          textAlign: "center",
          color: "#ffffff",
          fontSize: 32,
          fontFamily: "Arial, sans-serif",
          fontWeight: "bold",
          textShadow: "2px 2px 4px rgba(0,0,0,0.5)",
          padding: "20px",
        }}
      >
        {currentScene.scene_title}
      </div>
    </AbsoluteFill>
  );
};
