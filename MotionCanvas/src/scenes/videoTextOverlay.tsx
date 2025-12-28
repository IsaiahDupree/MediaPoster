import {makeScene2D} from '@motion-canvas/2d';
import {Txt, Rect, Video} from '@motion-canvas/2d/lib/components';
import {createRef} from '@motion-canvas/core';
import {all, waitFor} from '@motion-canvas/core/lib/flow';

/**
 * Animated text overlay scene for videos.
 * 
 * This scene demonstrates how to add animated text overlays on top of videos.
 * Note: Motion Canvas is primarily for vector animations, but can composite
 * with video backgrounds.
 */
export default makeScene2D(function* (view) {
  // Video background (if you have a video file)
  // const videoRef = createRef<Video>();
  // const video = new Video({
  //   ref: videoRef,
  //   src: '/path/to/video.mp4',
  //   width: 1920,
  //   height: 1080,
  // });
  // view.add(video);

  // Text overlay with animation
  const textRef = createRef<Txt>();
  const bgRef = createRef<Rect>();

  // Semi-transparent background for text readability
  const bg = new Rect({
    ref: bgRef,
    width: 1920,
    height: 250,
    fill: '#000000',
    opacity: 0.6,
    radius: 30,
    y: 300, // Position at bottom
  });

  // Animated text
  const text = new Txt({
    ref: textRef,
    text: 'MediaPoster\nAnimated Graphics',
    fontSize: 64,
    fill: '#ffffff',
    fontFamily: 'Arial',
    fontWeight: 700,
    textAlign: 'center',
    y: 300, // Position at bottom
  });

  view.add(bg);
  view.add(text);

  // Initial state: invisible and scaled down
  textRef().opacity(0);
  textRef().scale(0.3);
  textRef().y(400); // Start below
  bgRef().opacity(0);
  bgRef().y(400);

  // Slide up and fade in
  yield* all(
    textRef().opacity(1, 0.6),
    textRef().scale(1, 0.6),
    textRef().y(300, 0.6),
    bgRef().opacity(0.6, 0.6),
    bgRef().y(300, 0.6),
  );

  // Hold
  yield* waitFor(2);

  // Pulse animation
  yield* all(
    textRef().scale(1.05, 0.15),
    bgRef().opacity(0.8, 0.15),
  );
  yield* all(
    textRef().scale(1, 0.15),
    bgRef().opacity(0.6, 0.15),
  );

  // Hold
  yield* waitFor(1);

  // Slide down and fade out
  yield* all(
    textRef().opacity(0, 0.5),
    textRef().y(400, 0.5),
    bgRef().opacity(0, 0.5),
    bgRef().y(400, 0.5),
  );
});

