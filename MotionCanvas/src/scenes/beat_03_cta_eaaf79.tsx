import {makeScene2D} from '@motion-canvas/2d';
import {Txt, Rect} from '@motion-canvas/2d/lib/components';
import {createRef} from '@motion-canvas/core';
import {all, waitFor} from '@motion-canvas/core/lib/flow';

export default makeScene2D(function* (view) {

  // Solid background
  const bgRef = createRef<Rect>();
  const bg = new Rect({
    ref: bgRef,
    width: 1920,
    height: 250,
    fill: '#1a1a1a',
    opacity: 0.7,
    radius: 30,
  });



  // Animated text
  const textRef = createRef<Txt>();
  const text = new Txt({
    ref: textRef,
    text: "If you found this fun fact intriguing, don\u2019t forget to like, share, and subscribe for more scientific insights!",
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


  // Scale animation with pop
  textRef().opacity(0);
  textRef().scale(0);
  yield* all(
    textRef().opacity(1, 0.8),
    textRef().scale(1, 0.8),
  );
  yield* waitFor(1);
  yield* textRef().scale(1.2, 0.3);
  yield* textRef().scale(1, 0.3);
  yield* waitFor(0.5);
  yield* all(
    textRef().opacity(0, 0.5),
    textRef().scale(0, 0.5),
  );

  
  // Fade out background
  yield* bgRef().opacity(0, 0.5);
});
