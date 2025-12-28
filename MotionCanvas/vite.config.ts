import {defineConfig} from 'vite';
// @ts-ignore - CommonJS module compatibility
import motionCanvasPlugin from '@motion-canvas/vite-plugin';
// @ts-ignore - CommonJS module compatibility
import ffmpegPlugin from '@motion-canvas/ffmpeg';

export default defineConfig({
  plugins: [
    // @ts-ignore - CommonJS default export
    (motionCanvasPlugin.default || motionCanvasPlugin)(),
    // @ts-ignore - CommonJS default export
    (ffmpegPlugin.default || ffmpegPlugin)(),
  ],
});

