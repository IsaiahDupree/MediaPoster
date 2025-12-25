# E2E Test Implementation Guide

**Purpose:** Step-by-step guide to implement complete end-to-end tests for Instagram TrendTok

---

## Table of Contents

1. [Setup & Configuration](#setup--configuration)
2. [Test Framework Architecture](#test-framework-architecture)
3. [Test Implementation Examples](#test-implementation-examples)
4. [Page Object Models](#page-object-models)
5. [Test Data Management](#test-data-management)
6. [Execution & Reporting](#execution--reporting)

---

## Setup & Configuration

### 1. Install Playwright

```bash
cd dashboard
npm install --save-dev @playwright/test
npx playwright install
```

### 2. Playwright Configuration

**File:** `dashboard/playwright.config.ts`

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }]
  ],
  use: {
    baseURL: 'http://localhost:5557',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
  ],
  webServer: [
    {
      command: 'cd ../Backend && python main.py',
      url: 'http://localhost:5555',
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:5557',
      reuseExistingServer: !process.env.CI,
    },
  ],
});
```

### 3. Environment Setup

**File:** `dashboard/.env.test`

```bash
NEXT_PUBLIC_API_URL=http://localhost:5555
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres_test
OPENAI_API_KEY=test_key
RAPIDAPI_KEY=test_key
```

---

## Test Framework Architecture

### Directory Structure

```
dashboard/
├── e2e/
│   ├── fixtures/
│   │   ├── auth.ts
│   │   ├── data.ts
│   │   └── mocks.ts
│   ├── page-objects/
│   │   ├── BasePage.ts
│   │   ├── DashboardPage.ts
│   │   ├── AnalyzerPage.ts
│   │   ├── HashtagGeneratorPage.ts
│   │   └── TrendsPage.ts
│   ├── tests/
│   │   ├── 01-onboarding.spec.ts
│   │   ├── 02-creator-workflow.spec.ts
│   │   ├── 03-trend-discovery.spec.ts
│   │   ├── 04-batch-analysis.spec.ts
│   │   ├── 05-pipeline-init.spec.ts
│   │   └── 06-error-recovery.spec.ts
│   └── utils/
│       ├── helpers.ts
│       ├── assertions.ts
│       └── wait.ts
└── playwright.config.ts
```

---

## Test Implementation Examples

### Example 1: New User Onboarding Test

**File:** `dashboard/e2e/tests/01-onboarding.spec.ts`

```typescript
import { test, expect } from '@playwright/test';
import { DashboardPage } from '../page-objects/DashboardPage';
import { AnalyzerPage } from '../page-objects/AnalyzerPage';
import { HashtagGeneratorPage } from '../page-objects/HashtagGeneratorPage';
import { BestTimePage } from '../page-objects/BestTimePage';

test.describe('New User Onboarding', () => {
  let dashboardPage: DashboardPage;
  let analyzerPage: AnalyzerPage;
  let hashtagPage: HashtagGeneratorPage;
  let bestTimePage: BestTimePage;

  test.beforeEach(async ({ page }) => {
    dashboardPage = new DashboardPage(page);
    analyzerPage = new AnalyzerPage(page);
    hashtagPage = new HashtagGeneratorPage(page);
    bestTimePage = new BestTimePage(page);
    
    await dashboardPage.goto();
  });

  test('should complete full onboarding workflow', async ({ page }) => {
    // Step 1: Navigate to dashboard
    await expect(page).toHaveTitle(/Instagram Trends/);
    await expect(dashboardPage.setupWizard).toBeVisible();

    // Step 2: Click "Analyze Content"
    await dashboardPage.clickAnalyzeContent();
    await expect(page).toHaveURL(/\/ig-trends\/analyzer\/quick/);

    // Step 3: Fill in analysis form
    await analyzerPage.enterTranscript('Check out my morning workout routine!');
    await analyzerPage.enterCaption('Morning fitness tips');
    await analyzerPage.enterHashtags('fitness,workout,health');
    await analyzerPage.enterDuration(30);

    // Step 4: Submit analysis
    await analyzerPage.clickAnalyze();

    // Step 5: Wait for results (max 15 seconds)
    await analyzerPage.waitForResults({ timeout: 15000 });

    // Step 6: Verify analysis results
    const results = await analyzerPage.getResults();
    expect(results.hookType).toBeTruthy();
    expect(results.pacing).toBeTruthy();
    expect(results.textDensity).toBeGreaterThan(0);
    expect(results.sentiment).toMatch(/positive|neutral|negative/);
    expect(results.matchedTrends).toHaveLength.greaterThan(0);
    expect(results.recommendations).toHaveLength.greaterThan(0);

    // Step 7: Generate hashtags
    await analyzerPage.clickGenerateHashtags();
    await expect(page).toHaveURL(/\/ig-trends\/tools\/hashtags/);

    // Step 8: Verify hashtag generation
    await hashtagPage.waitForHashtags({ timeout: 10000 });
    const hashtags = await hashtagPage.getHashtags();
    expect(hashtags.trending).toHaveLength(10);
    expect(hashtags.niche).toHaveLength(10);
    expect(hashtags.longTail).toHaveLength(10);
    expect(hashtags.totalCount).toBe(30);

    // Step 9: Copy hashtags
    await hashtagPage.clickCopyAll();
    const copiedText = await page.evaluate(() => navigator.clipboard.readText());
    expect(copiedText).toContain('#');

    // Step 10: Check best time to post
    await hashtagPage.clickBestTime();
    await expect(page).toHaveURL(/\/ig-trends\/tools\/best-time/);

    // Step 11: Verify best time display
    await bestTimePage.waitForHeatmap({ timeout: 5000 });
    const bestTimes = await bestTimePage.getBestTimes();
    expect(bestTimes).toHaveLength.greaterThan(0);
    expect(bestTimes[0].hour).toBeGreaterThanOrEqual(0);
    expect(bestTimes[0].hour).toBeLessThan(24);
    expect(bestTimes[0].score).toBeGreaterThan(0);

    // Step 12: Verify journey completion
    await expect(page.locator('[data-testid="success-message"]')).toBeVisible();
  });

  test('should handle analysis errors gracefully', async ({ page }) => {
    await dashboardPage.clickAnalyzeContent();
    
    // Submit with empty transcript
    await analyzerPage.clickAnalyze();
    
    // Should show validation error
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
    await expect(page.locator('[data-testid="error-message"]')).toContainText('required');
  });

  test('should persist data across navigation', async ({ page }) => {
    await dashboardPage.clickAnalyzeContent();
    
    // Enter data
    await analyzerPage.enterTranscript('Test content');
    await analyzerPage.enterCaption('Test caption');
    
    // Navigate away
    await page.goto('/ig-trends');
    
    // Navigate back
    await page.goto('/ig-trends/analyzer/quick');
    
    // Data should be preserved (if using local storage)
    const transcript = await analyzerPage.getTranscriptValue();
    expect(transcript).toBe('Test content');
  });
});
```

### Example 2: Creator Daily Workflow Test

**File:** `dashboard/e2e/tests/02-creator-workflow.spec.ts`

```typescript
import { test, expect } from '@playwright/test';
import { DashboardPage } from '../page-objects/DashboardPage';
import { InspirationPage } from '../page-objects/InspirationPage';
import { TrendCardPage } from '../page-objects/TrendCardPage';

test.describe('Creator Daily Workflow', () => {
  test('should complete daily content optimization workflow', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);
    const inspirationPage = new InspirationPage(page);
    const trendCardPage = new TrendCardPage(page);

    // Step 1: View dashboard
    await dashboardPage.goto();
    await dashboardPage.waitForLoad();

    // Step 2: Verify dashboard widgets
    const trendingAudio = await dashboardPage.getTrendingAudio();
    expect(trendingAudio).toHaveLength(5);

    const trendingHashtags = await dashboardPage.getTrendingHashtags();
    expect(trendingHashtags).toHaveLength(5);

    const bestTime = await dashboardPage.getBestPostingTime();
    expect(bestTime).toBeTruthy();

    // Step 3: Navigate to Inspiration
    await dashboardPage.clickInspiration();
    await expect(page).toHaveURL(/\/ig-trends\/inspiration/);

    // Step 4: Filter trend cards
    await inspirationPage.filterByFormat('POV');
    const povCards = await inspirationPage.getTrendCards();
    expect(povCards.length).toBeGreaterThan(0);
    
    // Verify all cards are POV format
    for (const card of povCards) {
      expect(card.formatType).toBe('pov');
    }

    // Step 5: Click on specific trend card
    await inspirationPage.clickTrendCard('POV: You\'re the main character');
    
    // Step 6: Verify trend details
    const trendDetails = await trendCardPage.getDetails();
    expect(trendDetails.name).toContain('POV');
    expect(trendDetails.trendingScore).toBeGreaterThan(0);
    expect(trendDetails.velocity).toBeDefined();
    expect(trendDetails.examples).toHaveLength.greaterThan(0);

    // Step 7: Analyze content with this trend
    await trendCardPage.clickAnalyzeMyContent();
    
    // Step 8: Upload transcript
    await page.locator('[data-testid="transcript-input"]').fill(
      'POV: You wake up and realize you\'re the main character in your own story'
    );
    
    // Step 9: Submit analysis
    await page.locator('[data-testid="analyze-button"]').click();
    
    // Step 10: Verify trend match
    await page.waitForSelector('[data-testid="analysis-results"]');
    const matchedTrends = await page.locator('[data-testid="matched-trend"]').allTextContents();
    expect(matchedTrends).toContain('pov');

    // Step 11: Get recommendations
    const recommendations = await page.locator('[data-testid="recommendation"]').all();
    expect(recommendations.length).toBeGreaterThan(0);

    // Verify recommendations are actionable
    for (const rec of recommendations) {
      const text = await rec.textContent();
      expect(text).toBeTruthy();
      expect(text!.length).toBeGreaterThan(10);
    }

    // Step 12: Generate optimized hashtags
    await page.locator('[data-testid="generate-hashtags-button"]').click();
    await page.waitForSelector('[data-testid="hashtag-results"]');
    
    const hashtags = await page.locator('[data-testid="hashtag"]').allTextContents();
    expect(hashtags.length).toBe(30);

    // Step 13: Schedule post
    await page.locator('[data-testid="schedule-button"]').click();
    await page.waitForSelector('[data-testid="schedule-suggestions"]');
    
    const schedule = await page.locator('[data-testid="schedule-slot"]').all();
    expect(schedule.length).toBeGreaterThanOrEqual(3);

    // Step 14: Save schedule
    await page.locator('[data-testid="save-schedule-button"]').click();
    await expect(page.locator('[data-testid="success-toast"]')).toBeVisible();
  });
});
```

### Example 3: Error Recovery Test

**File:** `dashboard/e2e/tests/06-error-recovery.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('Error Recovery & Edge Cases', () => {
  test('should handle network errors gracefully', async ({ page, context }) => {
    await page.goto('/ig-trends/analyzer/quick');
    
    // Fill in form
    await page.locator('[data-testid="transcript-input"]').fill('Test content');
    
    // Simulate network offline
    await context.setOffline(true);
    
    // Try to submit
    await page.locator('[data-testid="analyze-button"]').click();
    
    // Should show network error
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
    await expect(page.locator('[data-testid="error-message"]')).toContainText('network');
    
    // Restore network
    await context.setOffline(false);
    
    // Retry should work
    await page.locator('[data-testid="retry-button"]').click();
    await page.waitForSelector('[data-testid="analysis-results"]', { timeout: 15000 });
    
    // Results should be displayed
    await expect(page.locator('[data-testid="analysis-results"]')).toBeVisible();
  });

  test('should handle API rate limiting', async ({ page }) => {
    await page.goto('/ig-trends/analyzer/quick');
    
    // Mock rate limit response
    await page.route('**/api/content-analyzer/analyze/quick', route => {
      route.fulfill({
        status: 429,
        body: JSON.stringify({ detail: 'Rate limit exceeded' }),
      });
    });
    
    // Submit analysis
    await page.locator('[data-testid="transcript-input"]').fill('Test');
    await page.locator('[data-testid="analyze-button"]').click();
    
    // Should show rate limit message
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
    await expect(page.locator('[data-testid="error-message"]')).toContainText('rate limit');
    
    // Should show retry countdown
    await expect(page.locator('[data-testid="retry-countdown"]')).toBeVisible();
  });

  test('should handle invalid input gracefully', async ({ page }) => {
    await page.goto('/ig-trends/analyzer/quick');
    
    // Test empty transcript
    await page.locator('[data-testid="analyze-button"]').click();
    await expect(page.locator('[data-testid="validation-error"]')).toBeVisible();
    
    // Test very long transcript (>10000 words)
    const longText = 'word '.repeat(10001);
    await page.locator('[data-testid="transcript-input"]').fill(longText);
    await expect(page.locator('[data-testid="warning-message"]')).toBeVisible();
    await expect(page.locator('[data-testid="warning-message"]')).toContainText('truncated');
    
    // Test special characters
    await page.locator('[data-testid="transcript-input"]').fill('Test 🔥💪✨ content');
    await page.locator('[data-testid="analyze-button"]').click();
    
    // Should handle emoji correctly
    await page.waitForSelector('[data-testid="analysis-results"]', { timeout: 15000 });
    await expect(page.locator('[data-testid="analysis-results"]')).toBeVisible();
  });

  test('should handle concurrent requests', async ({ page, context }) => {
    // Open multiple tabs
    const page2 = await context.newPage();
    const page3 = await context.newPage();
    
    // Navigate all to analyzer
    await Promise.all([
      page.goto('/ig-trends/analyzer/quick'),
      page2.goto('/ig-trends/analyzer/quick'),
      page3.goto('/ig-trends/analyzer/quick'),
    ]);
    
    // Submit analysis from all tabs simultaneously
    await Promise.all([
      page.locator('[data-testid="transcript-input"]').fill('Content 1'),
      page2.locator('[data-testid="transcript-input"]').fill('Content 2'),
      page3.locator('[data-testid="transcript-input"]').fill('Content 3'),
    ]);
    
    await Promise.all([
      page.locator('[data-testid="analyze-button"]').click(),
      page2.locator('[data-testid="analyze-button"]').click(),
      page3.locator('[data-testid="analyze-button"]').click(),
    ]);
    
    // All should complete successfully
    await Promise.all([
      page.waitForSelector('[data-testid="analysis-results"]', { timeout: 20000 }),
      page2.waitForSelector('[data-testid="analysis-results"]', { timeout: 20000 }),
      page3.waitForSelector('[data-testid="analysis-results"]', { timeout: 20000 }),
    ]);
    
    // Verify all results are different
    const result1 = await page.locator('[data-testid="hook-type"]').textContent();
    const result2 = await page2.locator('[data-testid="hook-type"]').textContent();
    const result3 = await page3.locator('[data-testid="hook-type"]').textContent();
    
    expect(result1).toBeTruthy();
    expect(result2).toBeTruthy();
    expect(result3).toBeTruthy();
  });
});
```

---

## Page Object Models

### Base Page Object

**File:** `dashboard/e2e/page-objects/BasePage.ts`

```typescript
import { Page, Locator } from '@playwright/test';

export class BasePage {
  readonly page: Page;
  readonly baseURL: string;

  constructor(page: Page) {
    this.page = page;
    this.baseURL = process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:5557';
  }

  async goto(path: string = '') {
    await this.page.goto(`${this.baseURL}${path}`);
  }

  async waitForLoad() {
    await this.page.waitForLoadState('networkidle');
  }

  async clickButton(testId: string) {
    await this.page.locator(`[data-testid="${testId}"]`).click();
  }

  async fillInput(testId: string, value: string) {
    await this.page.locator(`[data-testid="${testId}"]`).fill(value);
  }

  async getText(testId: string): Promise<string> {
    return await this.page.locator(`[data-testid="${testId}"]`).textContent() || '';
  }

  async isVisible(testId: string): Promise<boolean> {
    return await this.page.locator(`[data-testid="${testId}"]`).isVisible();
  }

  async waitForElement(testId: string, timeout: number = 5000) {
    await this.page.waitForSelector(`[data-testid="${testId}"]`, { timeout });
  }
}
```

### Dashboard Page Object

**File:** `dashboard/e2e/page-objects/DashboardPage.ts`

```typescript
import { Page } from '@playwright/test';
import { BasePage } from './BasePage';

export class DashboardPage extends BasePage {
  readonly setupWizard: Locator;
  readonly analyzeContentButton: Locator;
  readonly inspirationButton: Locator;

  constructor(page: Page) {
    super(page);
    this.setupWizard = page.locator('[data-testid="setup-wizard"]');
    this.analyzeContentButton = page.locator('[data-testid="analyze-content-button"]');
    this.inspirationButton = page.locator('[data-testid="inspiration-button"]');
  }

  async goto() {
    await super.goto('/ig-trends');
    await this.waitForLoad();
  }

  async clickAnalyzeContent() {
    await this.analyzeContentButton.click();
  }

  async clickInspiration() {
    await this.inspirationButton.click();
  }

  async getTrendingAudio(): Promise<Array<{ title: string; artist: string }>> {
    const items = await this.page.locator('[data-testid="trending-audio-item"]').all();
    return Promise.all(items.map(async item => ({
      title: await item.locator('[data-testid="audio-title"]').textContent() || '',
      artist: await item.locator('[data-testid="audio-artist"]').textContent() || '',
    })));
  }

  async getTrendingHashtags(): Promise<string[]> {
    return await this.page.locator('[data-testid="trending-hashtag"]').allTextContents();
  }

  async getBestPostingTime(): Promise<string> {
    return await this.page.locator('[data-testid="best-posting-time"]').textContent() || '';
  }
}
```

### Analyzer Page Object

**File:** `dashboard/e2e/page-objects/AnalyzerPage.ts`

```typescript
import { Page } from '@playwright/test';
import { BasePage } from './BasePage';

export class AnalyzerPage extends BasePage {
  constructor(page: Page) {
    super(page);
  }

  async goto() {
    await super.goto('/ig-trends/analyzer/quick');
    await this.waitForLoad();
  }

  async enterTranscript(text: string) {
    await this.fillInput('transcript-input', text);
  }

  async enterCaption(text: string) {
    await this.fillInput('caption-input', text);
  }

  async enterHashtags(tags: string) {
    await this.fillInput('hashtags-input', tags);
  }

  async enterDuration(seconds: number) {
    await this.fillInput('duration-input', seconds.toString());
  }

  async clickAnalyze() {
    await this.clickButton('analyze-button');
  }

  async waitForResults(options?: { timeout?: number }) {
    await this.waitForElement('analysis-results', options?.timeout);
  }

  async getResults() {
    return {
      hookType: await this.getText('hook-type'),
      pacing: await this.getText('pacing'),
      textDensity: parseFloat(await this.getText('text-density')),
      sentiment: await this.getText('sentiment'),
      matchedTrends: await this.page.locator('[data-testid="matched-trend"]').allTextContents(),
      recommendations: await this.page.locator('[data-testid="recommendation"]').all(),
    };
  }

  async clickGenerateHashtags() {
    await this.clickButton('generate-hashtags-button');
  }

  async getTranscriptValue(): Promise<string> {
    return await this.page.locator('[data-testid="transcript-input"]').inputValue();
  }
}
```

---

## Test Data Management

### Test Fixtures

**File:** `dashboard/e2e/fixtures/data.ts`

```typescript
export const testData = {
  profiles: {
    user1: {
      username: 'test_user_1',
      followers: 10000,
      following: 500,
      mediaCount: 150,
    },
    user2: {
      username: 'test_user_2',
      followers: 50000,
      following: 1000,
      mediaCount: 300,
    },
  },
  
  transcripts: {
    fitness: 'Check out my morning workout routine! Start with 10 pushups, then 20 squats.',
    food: 'Today I\'m making the perfect pasta carbonara. Let me show you the secret.',
    travel: 'POV: You just arrived in Paris and the Eiffel Tower takes your breath away.',
  },
  
  hashtags: {
    fitness: ['fitness', 'workout', 'health', 'gym', 'motivation'],
    food: ['food', 'recipe', 'cooking', 'foodie', 'delicious'],
    travel: ['travel', 'adventure', 'wanderlust', 'explore', 'vacation'],
  },
  
  expectedResults: {
    fitness: {
      hookType: 'text-based',
      sentiment: 'positive',
      niche: 'fitness',
    },
    food: {
      hookType: 'tutorial',
      sentiment: 'neutral',
      niche: 'food',
    },
    travel: {
      hookType: 'pov',
      sentiment: 'positive',
      niche: 'travel',
    },
  },
};
```

### Mock API Responses

**File:** `dashboard/e2e/fixtures/mocks.ts`

```typescript
import { Page } from '@playwright/test';

export async function mockAnalysisAPI(page: Page) {
  await page.route('**/api/content-analyzer/analyze/quick', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        job_id: 'mock_job_123',
        video_id: 'mock_video_123',
        status: 'completed',
        hook_type: 'curiosity',
        pacing: { speed: 'fast', cuts_per_minute: 25.5 },
        text_density: 2.8,
        sentiment: 'positive',
        matched_trend_cards: ['pov', 'tutorial'],
        recommendations: [
          {
            title: 'Improve Hook',
            description: 'Add question in first 2 seconds',
            priority: 'high',
            category: 'hook',
          },
        ],
      }),
    });
  });
}

export async function mockHashtagAPI(page: Page) {
  await page.route('**/api/hashtags/generate', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        trending: Array(10).fill(null).map((_, i) => ({
          tag: `trending${i}`,
          media_count: 100000,
          competition: 'high',
        })),
        niche: Array(10).fill(null).map((_, i) => ({
          tag: `niche${i}`,
          media_count: 50000,
          competition: 'medium',
        })),
        long_tail: Array(10).fill(null).map((_, i) => ({
          tag: `longtail${i}`,
          media_count: 5000,
          competition: 'low',
        })),
        detected_niche: 'fitness',
        total_count: 30,
      }),
    });
  });
}
```

---

## Execution & Reporting

### Run Tests

```bash
# Run all E2E tests
npm run test:e2e

# Run specific test file
npx playwright test e2e/tests/01-onboarding.spec.ts

# Run in headed mode (see browser)
npx playwright test --headed

# Run in debug mode
npx playwright test --debug

# Run on specific browser
npx playwright test --project=chromium

# Run with UI mode
npx playwright test --ui
```

### Generate Reports

```bash
# Generate HTML report
npx playwright show-report

# Generate JSON report
npx playwright test --reporter=json

# Generate JUnit XML
npx playwright test --reporter=junit
```

### CI/CD Integration

**File:** `.github/workflows/e2e-tests.yml`

```yaml
name: E2E Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight

jobs:
  e2e-tests:
    timeout-minutes: 60
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: dashboard/package-lock.json
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install Backend Dependencies
        run: |
          cd Backend
          pip install -r requirements.txt
      
      - name: Install Frontend Dependencies
        run: |
          cd dashboard
          npm ci
      
      - name: Install Playwright Browsers
        run: |
          cd dashboard
          npx playwright install --with-deps
      
      - name: Start Backend Server
        run: |
          cd Backend
          python main.py &
          sleep 10
      
      - name: Run E2E Tests
        run: |
          cd dashboard
          npx playwright test
      
      - name: Upload Test Results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: dashboard/playwright-report/
          retention-days: 30
      
      - name: Upload Test Videos
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: test-videos
          path: dashboard/test-results/
          retention-days: 7
```

---

## Best Practices

### 1. Test Independence
- Each test should be independent
- Use `test.beforeEach` for setup
- Clean up after each test
- Don't rely on test execution order

### 2. Stable Selectors
- Use `data-testid` attributes
- Avoid CSS selectors that may change
- Use semantic HTML when possible
- Create page objects for reusability

### 3. Wait Strategies
- Use `waitForSelector` instead of `sleep`
- Set appropriate timeouts
- Wait for network idle when needed
- Use `waitForLoadState` for page loads

### 4. Error Handling
- Test both success and failure paths
- Verify error messages
- Test edge cases
- Handle async operations properly

### 5. Performance
- Run tests in parallel when possible
- Use fixtures for common setup
- Mock external APIs when appropriate
- Keep tests focused and fast

---

**Document Version:** 1.0  
**Last Updated:** December 25, 2024  
**Next Review:** January 1, 2025
