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
    text: "This unique property is crucial for life on Earth, allowing ice to float on lakes and oceans, insulating the water below and protecting aquatic life during cold months.",
    fontSize: 64,
    fill: '#ffffff',
    fontFamily: 'Arial',
    fontWeight: 700,
    textAlign: 'center',
  });

  view.add(bg);
  view.add(text);


  // Slide in from bottom
  textRef().opacity(0);
  textRef().y(400);
  yield* all(
    textRef().opacity(1, 0.6),
    textRef().y(0, 0.6),
  );
  yield* waitFor(1);
  yield* all(
    textRef().opacity(0, 0.5),
    textRef().y(-400, 0.5),
  );

});
