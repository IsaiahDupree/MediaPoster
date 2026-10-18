import {makeScene2D} from '@motion-canvas/2d';
import {Txt, Rect} from '@motion-canvas/2d/lib/components';
import {createRef} from '@motion-canvas/core';
import {all, waitFor} from '@motion-canvas/core/lib/flow';

export default makeScene2D(function* (view) {
  // Create text reference
  const textRef = createRef<Txt>();
  const bgRef = createRef<Rect>();

  // Background rectangle for text readability
  const bg = new Rect({
    ref: bgRef,
    width: 1920,
    height: 200,
    fill: '#000000',
    opacity: 0.7,
    radius: 20,
  });

  // Animated text
  const text = new Txt({
    ref: textRef,
    text: 'Hello from Motion Canvas!',
    fontSize: 72,
    fill: '#ffffff',
    fontFamily: 'Arial',
    fontWeight: 700,
  });

  view.add(bg);
  view.add(text);

  // Start with text invisible
  textRef().opacity(0);
  textRef().scale(0.5);
  bgRef().opacity(0);

  // Animate text appearance
  yield* all(
    textRef().opacity(1, 0.8),
    textRef().scale(1, 0.8),
    bgRef().opacity(0.7, 0.8),
  );

  // Hold for a moment
  yield* waitFor(1);

  // Bounce animation
  yield* textRef().scale(1.1, 0.2);
  yield* textRef().scale(1, 0.2);

  // Hold again
  yield* waitFor(1);

  // Fade out
  yield* all(
    textRef().opacity(0, 0.5),
    bgRef().opacity(0, 0.5),
  );
});

