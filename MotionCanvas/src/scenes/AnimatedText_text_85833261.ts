import {makeScene2D} from '@motion-canvas/2d';
import {Txt, Img} from '@motion-canvas/2d/lib/components';
import {audio} from '@motion-canvas/core';

export default makeScene2D(function* (view) {


          const text = new Txt({
            text: "Pure Code Test",
            fontSize: 72,
            fill: "#ffffff",
            position: [0, 0],
          });
          view.add(text);
          yield* text.opacity(1.0, 5.0);
        
});
