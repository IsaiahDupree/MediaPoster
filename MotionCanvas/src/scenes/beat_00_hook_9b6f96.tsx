import {makeScene2D} from '@motion-canvas/2d';
import {Txt, Rect} from '@motion-canvas/2d/lib/components';
import {createRef} from '@motion-canvas/core';
import {all, waitFor} from '@motion-canvas/core/lib/flow';

export default makeScene2D(function* (view) {

  // Gradient background
  const bgRef = createRef<Rect>();
  const bg = new Rect({
    ref: bgRef,
    width: 1920,
    height: 1080,
    fill: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    opacity: 0.8,
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

  // Initialize background
  bgRef().opacity(0);
  yield* bgRef().opacity(0.7, 0.5);


  // Bounce animation with scale
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

  
  // Fade out background
  yield* bgRef().opacity(0, 0.5);
});
