import {makeScene2D} from '@motion-canvas/2d';
import {Txt, Rect, Img, Layout} from '@motion-canvas/2d/lib/components';
import {createRef} from '@motion-canvas/core';
import {all, waitFor, chain} from '@motion-canvas/core/lib/flow';
import {easeOutCubic, easeInOutCubic} from '@motion-canvas/core/lib/tweening';

/**
 * TopicScene - Standard explainer topic scene
 * 
 * Features:
 * - Animated icon/placeholder
 * - Title with zoom effect
 * - Description fade-in
 * - Background gradient
 * - Configurable colors and timing
 * 
 * Data structure expected:
 * {
 *   title: string,
 *   description?: string,
 *   icon?: string,
 *   accentColor?: string,
 *   duration?: number
 * }
 */

interface TopicData {
  title: string;
  description?: string;
  icon?: string;
  accentColor?: string;
  duration?: number;
}

// Default configuration
const DEFAULT_CONFIG = {
  backgroundColor: '#0f0f0f',
  textColor: '#ffffff',
  accentColor: '#FFD54F',
  descriptionColor: '#aaaaaa',
  duration: 60,
  titleFontSize: 64,
  descriptionFontSize: 32,
  iconSize: 200,
  zoomLevel: 1.1,
};

export default makeScene2D(function* (view) {
  // This would be injected from the content brief
  const topic: TopicData = {
    title: 'Sample Topic',
    description: 'This is a sample description for the topic scene.',
    accentColor: DEFAULT_CONFIG.accentColor,
    duration: DEFAULT_CONFIG.duration,
  };

  const config = { ...DEFAULT_CONFIG, ...topic };

  // Background with subtle gradient
  const bg = createRef<Rect>();
  view.add(
    <Rect
      ref={bg}
      width={1920}
      height={1080}
      fill={`linear-gradient(180deg, ${config.backgroundColor} 0%, #1a1a2e 100%)`}
    />
  );

  // Accent glow behind icon
  const glow = createRef<Rect>();
  view.add(
    <Rect
      ref={glow}
      width={300}
      height={300}
      y={-100}
      fill={config.accentColor}
      opacity={0}
      radius={150}
      shadowBlur={100}
      shadowColor={config.accentColor}
    />
  );

  // Icon placeholder (or actual icon if provided)
  const icon = createRef<Rect>();
  view.add(
    <Rect
      ref={icon}
      width={config.iconSize}
      height={config.iconSize}
      y={-100}
      fill={config.accentColor}
      radius={20}
      opacity={0}
      scale={0.8}
    />
  );

  // Title
  const title = createRef<Txt>();
  view.add(
    <Txt
      ref={title}
      text={topic.title}
      fontSize={config.titleFontSize}
      fill={config.textColor}
      fontWeight={700}
      fontFamily="Inter, Arial, sans-serif"
      y={100}
      opacity={0}
    />
  );

  // Description
  const desc = createRef<Txt>();
  view.add(
    <Txt
      ref={desc}
      text={topic.description || ''}
      fontSize={config.descriptionFontSize}
      fill={config.descriptionColor}
      y={180}
      opacity={0}
      width={1200}
      textWrap={true}
      textAlign="center"
    />
  );

  // ========== ANIMATION SEQUENCE ==========

  // Phase 1: Glow and icon fade in
  yield* all(
    glow().opacity(0.3, 0.4, easeOutCubic),
    icon().opacity(1, 0.5, easeOutCubic),
    icon().scale(1, 0.5, easeOutCubic),
  );

  yield* waitFor(0.2);

  // Phase 2: Title appears with slight scale
  yield* all(
    title().opacity(1, 0.4, easeOutCubic),
    title().position.y(100, 0).to(80, 0.4, easeOutCubic),
  );

  yield* waitFor(0.1);

  // Phase 3: Description fades in
  yield* desc().opacity(1, 0.3, easeOutCubic);

  // Phase 4: Subtle zoom on icon (signature explainer effect)
  yield* icon().scale(config.zoomLevel, 0.8, easeInOutCubic);

  // Hold for narration (most of the duration)
  const holdDuration = (topic.duration || config.duration) - 3;
  yield* waitFor(holdDuration > 0 ? holdDuration : 2);

  // Phase 5: Animate out
  yield* all(
    icon().opacity(0, 0.4, easeOutCubic),
    icon().scale(0.9, 0.4, easeOutCubic),
    glow().opacity(0, 0.4),
    title().opacity(0, 0.4),
    desc().opacity(0, 0.3),
  );
});
