import {makeProject} from '@motion-canvas/core';
import hello_from_code_ from './scenes/hello_from_code_?scene';

import pure_code_example from './scenes/pure_code_example?scene';

import pure_code_workflow from './scenes/pure_code_workflow?scene';

import hello_motion_canvas_ from './scenes/hello_motion_canvas_?scene';


import animatedText from './scenes/animatedText?scene';

export default makeProject({
  scenes: [hello_from_code_, pure_code_example, pure_code_workflow, hello_motion_canvas_, animatedText],
});

