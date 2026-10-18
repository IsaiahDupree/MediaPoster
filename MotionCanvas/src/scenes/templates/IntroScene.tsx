import {makeScene2D} from '@motion-canvas/2d';
import {Txt, Rect, Layout} from '@motion-canvas/2d/lib/components';
import {createRef} from '@motion-canvas/core';
import {all, waitFor, sequence} from '@motion-canvas/core/lib/flow';
import {easeOutCubic, easeOutBack, easeInOutCubic} from '@motion-canvas/core/lib/tweening';

/**
 * IntroScene - Video introduction scene
 * 
 * Features:
 * - Animated title reveal
 * - Subtitle/tagline
 * - Topic count indicator
 * - Dynamic gradient background
 * 
 * Data structure expected:
 * {
 *   title: string,
 *   subtitle?: string,
 *   topicCount?: number,
 *   accentColor?: string
 * }
 */

interface IntroData {
  title: string;
  subtitle?: string;
  topicCount?: number;
  accentColor?: string;
}

const DEFAULT_CONFIG = {
  backgroundColor: '#0a0a0a',
  textColor: '#ffffff',
  accentColor: '#FFD54F',
  duration: 5,
};

export default makeScene2D(function* (view) {
  const intro: IntroData = {
    title: 'Every Algorithm Explained',
    subtitle: 'A complete visual guide',
    topicCount: 10,
    accentColor: DEFAULT_CONFIG.accentColor,
  };

  const config = { ...DEFAULT_CONFIG, ...intro };

  // Background with animated gradient
  const bg = createRef<Rect>();
  view.add(
    <Rect
      ref={bg}
      width={1920}
      height={1080}
      fill={`linear-gradient(135deg, ${config.backgroundColor} 0%, #1a1a2e 50%, #0a0a0a 100%)`}
    />
  );

  // Decorative accent lines
  const accentLine1 = createRef<Rect>();
  const accentLine2 = createRef<Rect>();
  view.add(
    <>
      <Rect
        ref={accentLine1}
        width={0}
        height={4}
        y={-200}
        fill={config.accentColor}
        radius={2}
      />
      <Rect
        ref={accentLine2}
        width={0}
        height={4}
        y={200}
        fill={config.accentColor}
        radius={2}
      />
    </>
  );

  // Main title
  const title = createRef<Txt>();
  view.add(
    <Txt
      ref={title}
      text={intro.title}
      fontSize={80}
      fill={config.textColor}
      fontWeight={800}
      fontFamily="Inter, Arial, sans-serif"
      opacity={0}
      scale={0.8}
      y={-40}
    />
  );

  // Subtitle
  const subtitle = createRef<Txt>();
  view.add(
    <Txt
      ref={subtitle}
      text={intro.subtitle || ''}
      fontSize={36}
      fill={config.accentColor}
      fontWeight={500}
      opacity={0}
      y={60}
    />
  );

  // Topic count badge
  const badge = createRef<Layout>();
  const badgeText = createRef<Txt>();
  view.add(
    <Layout
      ref={badge}
      direction="row"
      alignItems="center"
      gap={12}
      y={140}
      opacity={0}
    >
      <Rect
        width={50}
        height={50}
        fill={config.accentColor}
        radius={25}
      >
        <Txt
          text={String(intro.topicCount || 0)}
          fontSize={24}
          fill={config.backgroundColor}
          fontWeight={700}
        />
      </Rect>
      <Txt
        ref={badgeText}
        text="topics covered"
        fontSize={24}
        fill={config.textColor}
        opacity={0.7}
      />
    </Layout>
  );

  // ========== ANIMATION SEQUENCE ==========

  // Phase 1: Accent lines sweep in
  yield* all(
    accentLine1().width(600, 0.6, easeOutCubic),
    accentLine2().width(600, 0.6, easeOutCubic),
  );

  yield* waitFor(0.2);

  // Phase 2: Title appears with scale bounce
  yield* all(
    title().opacity(1, 0.5, easeOutCubic),
    title().scale(1, 0.5, easeOutBack),
  );

  yield* waitFor(0.2);

  // Phase 3: Subtitle fades in
  yield* subtitle().opacity(1, 0.4, easeOutCubic);

  yield* waitFor(0.2);

  // Phase 4: Topic count badge
  yield* badge().opacity(1, 0.4, easeOutCubic);

  // Hold
  yield* waitFor(config.duration - 2.5);

  // Phase 5: Animate out
  yield* all(
    title().opacity(0, 0.4),
    title().scale(0.95, 0.4),
    subtitle().opacity(0, 0.3),
    badge().opacity(0, 0.3),
    accentLine1().width(0, 0.4, easeInOutCubic),
    accentLine2().width(0, 0.4, easeInOutCubic),
  );
});
