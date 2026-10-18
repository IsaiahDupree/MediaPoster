import {makeScene2D} from '@motion-canvas/2d';
import {Txt, Rect, Circle, Layout} from '@motion-canvas/2d/lib/components';
import {createRef} from '@motion-canvas/core';
import {all, waitFor, loop} from '@motion-canvas/core/lib/flow';
import {easeOutCubic, easeInOutSine} from '@motion-canvas/core/lib/tweening';

/**
 * OutroScene - Video outro/conclusion scene
 * 
 * Features:
 * - Thank you message
 * - Call to action (subscribe, like)
 * - Social icons placeholder
 * - Animated particles/effects
 * 
 * Data structure expected:
 * {
 *   message: string,
 *   ctaText?: string,
 *   showSubscribe?: boolean
 * }
 */

interface OutroData {
  message: string;
  ctaText?: string;
  showSubscribe?: boolean;
}

const DEFAULT_CONFIG = {
  backgroundColor: '#0a0a0a',
  textColor: '#ffffff',
  accentColor: '#FF0000', // YouTube red
  duration: 10,
};

export default makeScene2D(function* (view) {
  const outro: OutroData = {
    message: 'Thanks for watching!',
    ctaText: 'Subscribe for more',
    showSubscribe: true,
  };

  const config = { ...DEFAULT_CONFIG };

  // Background
  const bg = createRef<Rect>();
  view.add(
    <Rect
      ref={bg}
      width={1920}
      height={1080}
      fill={`linear-gradient(180deg, ${config.backgroundColor} 0%, #0f0f1a 100%)`}
    />
  );

  // Floating particles for visual interest
  const particles: ReturnType<typeof createRef<Circle>>[] = [];
  for (let i = 0; i < 6; i++) {
    const particle = createRef<Circle>();
    particles.push(particle);
    view.add(
      <Circle
        ref={particle}
        size={20 + Math.random() * 30}
        fill={config.accentColor}
        opacity={0.1 + Math.random() * 0.2}
        x={-800 + Math.random() * 1600}
        y={-400 + Math.random() * 800}
      />
    );
  }

  // Main message
  const message = createRef<Txt>();
  view.add(
    <Txt
      ref={message}
      text={outro.message}
      fontSize={72}
      fill={config.textColor}
      fontWeight={700}
      fontFamily="Inter, Arial, sans-serif"
      opacity={0}
      y={-80}
    />
  );

  // Subscribe button
  const subscribeBtn = createRef<Layout>();
  view.add(
    <Layout
      ref={subscribeBtn}
      direction="row"
      alignItems="center"
      gap={16}
      y={80}
      opacity={0}
    >
      <Rect
        width={200}
        height={56}
        fill={config.accentColor}
        radius={28}
      >
        <Txt
          text="SUBSCRIBE"
          fontSize={20}
          fill={config.textColor}
          fontWeight={700}
        />
      </Rect>
    </Layout>
  );

  // CTA text
  const cta = createRef<Txt>();
  view.add(
    <Txt
      ref={cta}
      text={outro.ctaText || ''}
      fontSize={32}
      fill={config.textColor}
      opacity={0}
      y={180}
    />
  );

  // ========== ANIMATION SEQUENCE ==========

  // Phase 1: Message fades in
  yield* message().opacity(1, 0.8, easeOutCubic);

  yield* waitFor(0.5);

  // Phase 2: Subscribe button appears
  if (outro.showSubscribe) {
    yield* all(
      subscribeBtn().opacity(1, 0.5, easeOutCubic),
      subscribeBtn().position.y(80, 0).to(60, 0.5, easeOutCubic),
    );
  }

  yield* waitFor(0.3);

  // Phase 3: CTA text
  yield* cta().opacity(0.8, 0.4, easeOutCubic);

  // Phase 4: Animate floating particles
  yield* all(
    ...particles.map((p, i) =>
      p().position.y(p().position.y() - 100, config.duration - 3, easeInOutSine)
    )
  );

  // Hold
  yield* waitFor(config.duration - 4);

  // Phase 5: Fade out
  yield* all(
    message().opacity(0, 0.5),
    subscribeBtn().opacity(0, 0.4),
    cta().opacity(0, 0.4),
    ...particles.map(p => p().opacity(0, 0.5)),
  );
});
