import {makeScene2D} from '@motion-canvas/2d';
import {Txt, Rect} from '@motion-canvas/2d/lib/components';
import {createRef} from '@motion-canvas/core';
import {all, waitFor} from '@motion-canvas/core/lib/flow';

export default makeScene2D(function* (view) {
  // Background for text readability
  const bgRef = createRef<Rect>();
  const bg = new Rect({
    ref: bgRef,
    width: 1920,
    height: 250,
    fill: '#000000',
    opacity: 0.6,
    radius: 30,
  });

  // Animated text
  const textRef = createRef<Txt>();
  const text = new Txt({
    ref: textRef,
    text: "Welcome to our exploration of a fascinating phenomenon in thermodynamics: why ice floats on water.",
    fontSize: 64,
    fill: '#ffffff',
    fontFamily: 'Arial',
    fontWeight: 700,
    textAlign: 'center',
  });

  view.add(bg);
  view.add(text);


  // Bounce animation
  textRef().opacity(0);
  textRef().scale(0.3);
  yield* all(
    textRef().opacity(1, 0.6),
    textRef().scale(1, 0.6),
  );
  yield* waitFor(0.5);
  yield* textRef().scale(1.1, 0.2);
  yield* textRef().scale(1, 0.2);
  yield* waitFor(1);
  yield* all(
    textRef().opacity(0, 0.5),
    textRef().scale(0.5, 0.5),
  );

});
