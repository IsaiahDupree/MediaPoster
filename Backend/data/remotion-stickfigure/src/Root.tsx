import { Composition } from "remotion";
import { StickFigureVideo } from "./StickFigureVideo";
import scenes from "../scenes.json";

export const RemotionRoot: React.FC = () => {
  const fps = 30;
  const durationInSeconds = 90;
  const durationInFrames = durationInSeconds * fps;

  return (
    <>
      <Composition
        id="StickFigureExplainer"
        component={StickFigureVideo}
        durationInFrames={durationInFrames}
        fps={fps}
        width={1080}
        height={1920}
        defaultProps={{
          scenes: scenes.scenes,
          audioSrc: "./audio_DTJQ6Skks0k.mp3",
        }}
      />
    </>
  );
};
