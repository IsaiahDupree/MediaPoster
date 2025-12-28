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
    text: "This simple question has a complex answer that reveals the unique properties of water. As water cools, it becomes denser until it reaches 4 degrees Celsius. At this temperature, it is at its densest. But, as it continues to cool and freezes into ice, the structure of water molecules changes, creating a crystalline lattice that is less dense than liquid water.",
    fontSize: 64,
    fill: '#ffffff',
    fontFamily: 'Arial',
    fontWeight: 700,
    textAlign: 'center',
  });

  view.add(bg);
  view.add(text);


  // Fade in/out
  textRef().opacity(0);
  yield* textRef().opacity(1, 0.8);
  yield* waitFor(1);
  yield* textRef().opacity(0, 0.8);

});
