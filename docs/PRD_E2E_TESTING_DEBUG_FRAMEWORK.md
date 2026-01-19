# PRD: E2E Testing Framework with Debug Logging

**Version:** 1.0  
**Date:** January 19, 2026  
**Status:** Proposed  
**Priority:** High  
**Estimated Effort:** 2 weeks

---

## Executive Summary

Establish a comprehensive End-to-End (E2E) testing framework with structured console logging for debugging. This ensures all features are testable, failures are easily diagnosable, and developers can trace issues through complete user workflows.

---

## Problem Statement

### Current State
- Inconsistent test coverage across features
- Debugging requires manual log inspection
- No standardized logging format
- E2E tests lack visibility into failures
- No correlation between frontend and backend logs

### Developer Pain Points
1. Hard to reproduce reported bugs
2. Unclear where failures occur in workflows
3. No structured debug output
4. Tests pass/fail without context
5. Manual debugging is time-consuming

---

## Goals & Success Metrics

### Goals
1. 90%+ E2E test coverage for critical paths
2. Structured console logging with trace IDs
3. Automatic screenshot/video on failure
4. Easy-to-read test reports
5. Debug mode for verbose logging

### Success Metrics

| Metric | Target |
|--------|--------|
| Critical path coverage | > 90% |
| Avg debug time | < 15 min |
| Flaky test rate | < 2% |
| Test run time | < 10 min for full suite |

---

## Features

### Phase 1: Logging Infrastructure (Week 1)

#### 1.1 Structured Console Logger

```typescript
// lib/logger.ts

export enum LogLevel {
  DEBUG = 'DEBUG',
  INFO = 'INFO',
  WARN = 'WARN',
  ERROR = 'ERROR',
  TEST = 'TEST'
}

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  traceId: string;
  component: string;
  action: string;
  data?: Record<string, any>;
  duration?: number;
  error?: Error;
}

export class DebugLogger {
  private traceId: string;
  private component: string;
  
  constructor(component: string, traceId?: string) {
    this.component = component;
    this.traceId = traceId || this.generateTraceId();
  }
  
  log(level: LogLevel, action: string, data?: any): void {
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      traceId: this.traceId,
      component: this.component,
      action,
      data
    };
    
    console.log(this.format(entry));
  }
  
  // Convenience methods
  debug(action: string, data?: any) { this.log(LogLevel.DEBUG, action, data); }
  info(action: string, data?: any) { this.log(LogLevel.INFO, action, data); }
  warn(action: string, data?: any) { this.log(LogLevel.WARN, action, data); }
  error(action: string, error: Error, data?: any) {
    this.log(LogLevel.ERROR, action, { ...data, error: error.message, stack: error.stack });
  }
  test(action: string, data?: any) { this.log(LogLevel.TEST, action, data); }
  
  // Timing helper
  time(action: string): () => void {
    const start = Date.now();
    this.debug(`${action} - START`);
    return () => {
      const duration = Date.now() - start;
      this.debug(`${action} - END`, { duration: `${duration}ms` });
    };
  }
  
  private format(entry: LogEntry): string {
    const emoji = {
      DEBUG: '🔍',
      INFO: 'ℹ️',
      WARN: '⚠️',
      ERROR: '❌',
      TEST: '🧪'
    }[entry.level];
    
    return `${emoji} [${entry.timestamp}] [${entry.traceId}] [${entry.component}] ${entry.action}${
      entry.data ? ` | ${JSON.stringify(entry.data)}` : ''
    }`;
  }
  
  private generateTraceId(): string {
    return `trace_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}
```

#### 1.2 Backend Python Logger

```python
# Backend/utils/debug_logger.py

import logging
import json
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Any
from functools import wraps

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    TEST = "TEST"

class DebugLogger:
    def __init__(self, component: str, trace_id: Optional[str] = None):
        self.component = component
        self.trace_id = trace_id or f"trace_{int(time.time())}_{uuid.uuid4().hex[:9]}"
        self.logger = logging.getLogger(component)
    
    def log(self, level: LogLevel, action: str, data: Optional[dict] = None):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level.value,
            "trace_id": self.trace_id,
            "component": self.component,
            "action": action,
            "data": data
        }
        
        emoji = {
            "DEBUG": "🔍",
            "INFO": "ℹ️",
            "WARN": "⚠️",
            "ERROR": "❌",
            "TEST": "🧪"
        }[level.value]
        
        message = f"{emoji} [{entry['timestamp']}] [{self.trace_id}] [{self.component}] {action}"
        if data:
            message += f" | {json.dumps(data)}"
        
        print(message)
        return entry
    
    def debug(self, action: str, data: Optional[dict] = None):
        return self.log(LogLevel.DEBUG, action, data)
    
    def info(self, action: str, data: Optional[dict] = None):
        return self.log(LogLevel.INFO, action, data)
    
    def warn(self, action: str, data: Optional[dict] = None):
        return self.log(LogLevel.WARN, action, data)
    
    def error(self, action: str, error: Exception, data: Optional[dict] = None):
        error_data = {
            **(data or {}),
            "error": str(error),
            "error_type": type(error).__name__
        }
        return self.log(LogLevel.ERROR, action, error_data)
    
    def test(self, action: str, data: Optional[dict] = None):
        return self.log(LogLevel.TEST, action, data)

def timed(logger: DebugLogger, action: str):
    """Decorator for timing function execution"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger.debug(f"{action} - START")
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = (time.time() - start) * 1000
                logger.debug(f"{action} - END", {"duration_ms": round(duration, 2)})
                return result
            except Exception as e:
                duration = (time.time() - start) * 1000
                logger.error(f"{action} - FAILED", e, {"duration_ms": round(duration, 2)})
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger.debug(f"{action} - START")
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start) * 1000
                logger.debug(f"{action} - END", {"duration_ms": round(duration, 2)})
                return result
            except Exception as e:
                duration = (time.time() - start) * 1000
                logger.error(f"{action} - FAILED", e, {"duration_ms": round(duration, 2)})
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator
```

### Phase 2: E2E Test Framework (Week 1-2)

#### 2.1 Playwright Test Setup

```typescript
// e2e/utils/test-utils.ts

import { test as base, Page, expect } from '@playwright/test';
import { DebugLogger } from './debug-logger';

// Extended test with logging
export const test = base.extend<{
  logger: DebugLogger;
  tracedPage: Page;
}>({
  logger: async ({}, use, testInfo) => {
    const logger = new DebugLogger('E2E', `test_${testInfo.testId}`);
    logger.test('TEST_START', { 
      title: testInfo.title,
      file: testInfo.file 
    });
    
    await use(logger);
    
    logger.test('TEST_END', { 
      status: testInfo.status,
      duration: testInfo.duration 
    });
  },
  
  tracedPage: async ({ page, logger }, use) => {
    // Log all console messages
    page.on('console', msg => {
      logger.debug('CONSOLE', { 
        type: msg.type(), 
        text: msg.text() 
      });
    });
    
    // Log all network requests
    page.on('request', request => {
      logger.debug('REQUEST', { 
        method: request.method(),
        url: request.url() 
      });
    });
    
    // Log all network responses
    page.on('response', response => {
      logger.debug('RESPONSE', { 
        status: response.status(),
        url: response.url() 
      });
    });
    
    // Log page errors
    page.on('pageerror', error => {
      logger.error('PAGE_ERROR', error);
    });
    
    await use(page);
  }
});

export { expect };
```

#### 2.2 Test Helper Functions

```typescript
// e2e/utils/helpers.ts

import { Page, expect } from '@playwright/test';
import { DebugLogger } from './debug-logger';

export class TestHelpers {
  constructor(
    private page: Page,
    private logger: DebugLogger
  ) {}
  
  async login(email: string, password: string): Promise<void> {
    const endTimer = this.logger.time('LOGIN_FLOW');
    
    try {
      this.logger.debug('Navigating to login page');
      await this.page.goto('/login');
      
      this.logger.debug('Filling credentials', { email });
      await this.page.fill('[data-testid="email-input"]', email);
      await this.page.fill('[data-testid="password-input"]', password);
      
      this.logger.debug('Submitting login form');
      await this.page.click('[data-testid="login-button"]');
      
      this.logger.debug('Waiting for redirect');
      await this.page.waitForURL('/dashboard');
      
      this.logger.info('Login successful', { email });
    } catch (error) {
      this.logger.error('Login failed', error as Error, { email });
      await this.captureDebugInfo('login_failure');
      throw error;
    } finally {
      endTimer();
    }
  }
  
  async navigateTo(path: string): Promise<void> {
    this.logger.debug('NAVIGATE', { path });
    await this.page.goto(path);
    await this.page.waitForLoadState('networkidle');
    this.logger.debug('NAVIGATION_COMPLETE', { path, url: this.page.url() });
  }
  
  async clickAndWait(selector: string, waitFor?: string): Promise<void> {
    this.logger.debug('CLICK', { selector });
    await this.page.click(selector);
    
    if (waitFor) {
      this.logger.debug('WAITING_FOR', { selector: waitFor });
      await this.page.waitForSelector(waitFor);
    }
  }
  
  async fillForm(fields: Record<string, string>): Promise<void> {
    this.logger.debug('FILL_FORM', { fields: Object.keys(fields) });
    
    for (const [selector, value] of Object.entries(fields)) {
      await this.page.fill(selector, value);
      this.logger.debug('FIELD_FILLED', { selector, valueLength: value.length });
    }
  }
  
  async assertVisible(selector: string, message?: string): Promise<void> {
    this.logger.debug('ASSERT_VISIBLE', { selector });
    await expect(this.page.locator(selector)).toBeVisible();
    this.logger.debug('ASSERTION_PASSED', { selector, message });
  }
  
  async assertText(selector: string, expectedText: string): Promise<void> {
    this.logger.debug('ASSERT_TEXT', { selector, expected: expectedText });
    await expect(this.page.locator(selector)).toHaveText(expectedText);
    this.logger.debug('ASSERTION_PASSED', { selector });
  }
  
  async captureDebugInfo(name: string): Promise<void> {
    const timestamp = Date.now();
    
    // Screenshot
    const screenshotPath = `debug/${name}_${timestamp}.png`;
    await this.page.screenshot({ path: screenshotPath, fullPage: true });
    this.logger.info('SCREENSHOT_CAPTURED', { path: screenshotPath });
    
    // HTML snapshot
    const html = await this.page.content();
    this.logger.debug('HTML_SNAPSHOT', { length: html.length });
    
    // Console logs
    this.logger.debug('PAGE_STATE', {
      url: this.page.url(),
      title: await this.page.title()
    });
  }
  
  async waitForAPI(urlPattern: string | RegExp): Promise<any> {
    this.logger.debug('WAITING_FOR_API', { pattern: urlPattern.toString() });
    
    const response = await this.page.waitForResponse(
      resp => resp.url().match(urlPattern) !== null
    );
    
    const data = await response.json().catch(() => null);
    this.logger.debug('API_RESPONSE', { 
      status: response.status(),
      url: response.url(),
      hasData: !!data 
    });
    
    return data;
  }
}
```

### Phase 3: E2E Test Suites (Week 2)

#### 3.1 Critical Path Tests

```typescript
// e2e/critical-paths/auth.spec.ts

import { test, expect } from '../utils/test-utils';
import { TestHelpers } from '../utils/helpers';

test.describe('Authentication Flow', () => {
  test('complete signup → login → logout flow', async ({ tracedPage, logger }) => {
    const helpers = new TestHelpers(tracedPage, logger);
    
    logger.test('SCENARIO_START', { name: 'Complete Auth Flow' });
    
    // Step 1: Signup
    logger.info('Step 1: Signup');
    await helpers.navigateTo('/signup');
    await helpers.fillForm({
      '[data-testid="name-input"]': 'Test User',
      '[data-testid="email-input"]': `test_${Date.now()}@example.com`,
      '[data-testid="password-input"]': 'SecurePass123!'
    });
    await helpers.clickAndWait(
      '[data-testid="signup-button"]',
      '[data-testid="dashboard"]'
    );
    logger.info('Signup completed');
    
    // Step 2: Verify dashboard access
    logger.info('Step 2: Verify Dashboard');
    await helpers.assertVisible('[data-testid="user-menu"]');
    await helpers.assertVisible('[data-testid="posts-section"]');
    
    // Step 3: Logout
    logger.info('Step 3: Logout');
    await helpers.clickAndWait(
      '[data-testid="user-menu"]',
      '[data-testid="logout-button"]'
    );
    await tracedPage.click('[data-testid="logout-button"]');
    await tracedPage.waitForURL('/login');
    
    logger.test('SCENARIO_COMPLETE', { name: 'Complete Auth Flow', status: 'passed' });
  });
});
```

```typescript
// e2e/critical-paths/post-creation.spec.ts

import { test, expect } from '../utils/test-utils';
import { TestHelpers } from '../utils/helpers';

test.describe('Post Creation Flow', () => {
  test.beforeEach(async ({ tracedPage, logger }) => {
    const helpers = new TestHelpers(tracedPage, logger);
    await helpers.login('test@example.com', 'password123');
  });
  
  test('create and schedule a post', async ({ tracedPage, logger }) => {
    const helpers = new TestHelpers(tracedPage, logger);
    
    logger.test('SCENARIO_START', { name: 'Create and Schedule Post' });
    
    // Navigate to composer
    logger.info('Step 1: Open composer');
    await helpers.navigateTo('/posts/new');
    
    // Fill post content
    logger.info('Step 2: Fill content');
    await helpers.fillForm({
      '[data-testid="post-content"]': 'Test post content #testing'
    });
    
    // Select platforms
    logger.info('Step 3: Select platforms');
    await tracedPage.click('[data-testid="platform-tiktok"]');
    await tracedPage.click('[data-testid="platform-instagram"]');
    
    // Set schedule
    logger.info('Step 4: Set schedule');
    await tracedPage.click('[data-testid="schedule-toggle"]');
    await tracedPage.fill('[data-testid="schedule-date"]', '2026-01-25');
    await tracedPage.fill('[data-testid="schedule-time"]', '14:00');
    
    // Submit
    logger.info('Step 5: Submit post');
    await helpers.clickAndWait(
      '[data-testid="submit-post"]',
      '[data-testid="success-message"]'
    );
    
    // Verify
    logger.info('Step 6: Verify scheduled');
    await helpers.navigateTo('/calendar');
    await helpers.assertVisible('[data-testid="scheduled-post"]');
    
    logger.test('SCENARIO_COMPLETE', { name: 'Create and Schedule Post', status: 'passed' });
  });
  
  test('post with media upload', async ({ tracedPage, logger }) => {
    const helpers = new TestHelpers(tracedPage, logger);
    
    logger.test('SCENARIO_START', { name: 'Post with Media' });
    
    await helpers.navigateTo('/posts/new');
    
    // Upload media
    logger.info('Uploading media file');
    const fileInput = tracedPage.locator('[data-testid="media-upload"]');
    await fileInput.setInputFiles('e2e/fixtures/test-video.mp4');
    
    // Wait for upload
    logger.debug('Waiting for upload completion');
    await tracedPage.waitForSelector('[data-testid="upload-complete"]', {
      timeout: 30000
    });
    
    // Fill and submit
    await helpers.fillForm({
      '[data-testid="post-content"]': 'Video post test'
    });
    await tracedPage.click('[data-testid="platform-tiktok"]');
    await helpers.clickAndWait(
      '[data-testid="submit-post"]',
      '[data-testid="success-message"]'
    );
    
    logger.test('SCENARIO_COMPLETE', { name: 'Post with Media', status: 'passed' });
  });
});
```

```typescript
// e2e/critical-paths/analytics.spec.ts

import { test, expect } from '../utils/test-utils';
import { TestHelpers } from '../utils/helpers';

test.describe('Analytics Dashboard', () => {
  test('view analytics with data', async ({ tracedPage, logger }) => {
    const helpers = new TestHelpers(tracedPage, logger);
    
    logger.test('SCENARIO_START', { name: 'Analytics View' });
    
    await helpers.login('test@example.com', 'password123');
    
    // Navigate to analytics
    logger.info('Loading analytics page');
    await helpers.navigateTo('/analytics');
    
    // Wait for data load
    logger.debug('Waiting for analytics data');
    const apiData = await helpers.waitForAPI(/\/api\/analytics/);
    logger.debug('Analytics data received', { 
      hasData: !!apiData,
      metrics: apiData?.metrics?.length 
    });
    
    // Verify charts render
    logger.info('Verifying chart components');
    await helpers.assertVisible('[data-testid="engagement-chart"]');
    await helpers.assertVisible('[data-testid="followers-chart"]');
    await helpers.assertVisible('[data-testid="top-posts"]');
    
    // Test date range filter
    logger.info('Testing date filter');
    await tracedPage.click('[data-testid="date-range-selector"]');
    await tracedPage.click('[data-testid="range-30d"]');
    await helpers.waitForAPI(/\/api\/analytics/);
    
    logger.test('SCENARIO_COMPLETE', { name: 'Analytics View', status: 'passed' });
  });
});
```

#### 3.2 Feature-Specific E2E Tests

```typescript
// e2e/features/community-inbox.spec.ts

import { test, expect } from '../utils/test-utils';
import { TestHelpers } from '../utils/helpers';

test.describe('Community Inbox', () => {
  test('view and reply to messages', async ({ tracedPage, logger }) => {
    const helpers = new TestHelpers(tracedPage, logger);
    
    logger.test('SCENARIO_START', { name: 'Community Inbox Flow' });
    
    await helpers.login('test@example.com', 'password123');
    await helpers.navigateTo('/inbox');
    
    // Wait for messages to load
    logger.info('Loading inbox messages');
    await helpers.waitForAPI(/\/api\/inbox\/messages/);
    
    // Click first message
    logger.info('Opening first message');
    await helpers.clickAndWait(
      '[data-testid="message-item"]:first-child',
      '[data-testid="message-detail"]'
    );
    
    // Get AI suggestions
    logger.info('Getting AI reply suggestions');
    await tracedPage.click('[data-testid="ai-suggest-button"]');
    await helpers.waitForAPI(/\/api\/inbox\/.*\/ai-suggestions/);
    await helpers.assertVisible('[data-testid="ai-suggestions"]');
    
    // Select suggestion and send
    logger.info('Sending reply');
    await tracedPage.click('[data-testid="suggestion-1"]');
    await helpers.clickAndWait(
      '[data-testid="send-reply"]',
      '[data-testid="reply-sent"]'
    );
    
    logger.test('SCENARIO_COMPLETE', { name: 'Community Inbox Flow', status: 'passed' });
  });
});
```

```typescript
// e2e/features/content-repurposing.spec.ts

import { test, expect } from '../utils/test-utils';
import { TestHelpers } from '../utils/helpers';

test.describe('Content Repurposing', () => {
  test('process video and generate clips', async ({ tracedPage, logger }) => {
    const helpers = new TestHelpers(tracedPage, logger);
    
    logger.test('SCENARIO_START', { name: 'Content Repurposing E2E' });
    
    await helpers.login('test@example.com', 'password123');
    await helpers.navigateTo('/repurpose/new');
    
    // Upload video
    logger.info('Uploading source video');
    const fileInput = tracedPage.locator('[data-testid="source-upload"]');
    await fileInput.setInputFiles('e2e/fixtures/long-video.mp4');
    
    // Wait for upload
    await tracedPage.waitForSelector('[data-testid="upload-complete"]', {
      timeout: 60000
    });
    logger.debug('Upload complete');
    
    // Start processing
    logger.info('Starting AI processing');
    await tracedPage.click('[data-testid="process-button"]');
    
    // Wait for processing (polling)
    logger.debug('Waiting for AI processing');
    let attempts = 0;
    while (attempts < 30) {
      const status = await tracedPage.locator('[data-testid="process-status"]').textContent();
      logger.debug('Processing status', { status, attempt: attempts });
      
      if (status === 'Complete') break;
      await tracedPage.waitForTimeout(2000);
      attempts++;
    }
    
    // Verify clips generated
    logger.info('Verifying generated clips');
    await helpers.assertVisible('[data-testid="clips-list"]');
    const clipCount = await tracedPage.locator('[data-testid="clip-item"]').count();
    logger.info('Clips generated', { count: clipCount });
    
    expect(clipCount).toBeGreaterThan(0);
    
    logger.test('SCENARIO_COMPLETE', { name: 'Content Repurposing E2E', status: 'passed' });
  });
});
```

### Phase 4: Debugging Tools

#### 4.1 Test Reporter with Console Output

```typescript
// e2e/reporters/debug-reporter.ts

import { Reporter, TestCase, TestResult, FullResult } from '@playwright/test/reporter';

class DebugReporter implements Reporter {
  private startTime: number = 0;
  
  onBegin(config: any, suite: any) {
    this.startTime = Date.now();
    console.log('\n' + '='.repeat(60));
    console.log('🧪 E2E TEST SUITE STARTING');
    console.log('='.repeat(60) + '\n');
  }
  
  onTestBegin(test: TestCase) {
    console.log(`\n▶️  Starting: ${test.title}`);
    console.log(`   File: ${test.location.file}:${test.location.line}`);
  }
  
  onTestEnd(test: TestCase, result: TestResult) {
    const emoji = {
      passed: '✅',
      failed: '❌',
      timedOut: '⏰',
      skipped: '⏭️'
    }[result.status] || '❓';
    
    console.log(`\n${emoji} ${test.title}`);
    console.log(`   Duration: ${result.duration}ms`);
    console.log(`   Status: ${result.status}`);
    
    if (result.status === 'failed') {
      console.log('\n   ─── Error Details ───');
      console.log(`   ${result.error?.message}`);
      console.log('\n   ─── Stack Trace ───');
      console.log(`   ${result.error?.stack?.split('\n').slice(0, 5).join('\n   ')}`);
      
      if (result.attachments.length > 0) {
        console.log('\n   ─── Attachments ───');
        result.attachments.forEach(a => {
          console.log(`   📎 ${a.name}: ${a.path}`);
        });
      }
    }
    
    // Print stdout/stderr
    if (result.stdout.length > 0) {
      console.log('\n   ─── Console Output ───');
      result.stdout.forEach(line => console.log(`   ${line}`));
    }
  }
  
  onEnd(result: FullResult) {
    const duration = Date.now() - this.startTime;
    
    console.log('\n' + '='.repeat(60));
    console.log('📊 TEST RESULTS SUMMARY');
    console.log('='.repeat(60));
    console.log(`   Total Duration: ${(duration / 1000).toFixed(2)}s`);
    console.log(`   Status: ${result.status}`);
    console.log('='.repeat(60) + '\n');
  }
}

export default DebugReporter;
```

#### 4.2 Playwright Config

```typescript
// playwright.config.ts

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 60000,
  retries: process.env.CI ? 2 : 0,
  
  reporter: [
    ['list'],
    ['./e2e/reporters/debug-reporter.ts'],
    ['html', { open: 'never' }],
    ['json', { outputFile: 'test-results/results.json' }]
  ],
  
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:5557',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry',
    
    // Debug mode
    headless: process.env.DEBUG ? false : true,
    slowMo: process.env.DEBUG ? 500 : 0,
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
      name: 'mobile',
      use: { ...devices['iPhone 13'] },
    },
  ],
  
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5557',
    reuseExistingServer: !process.env.CI,
  },
});
```

---

## Console Log Output Examples

### Successful Test Run
```
🧪 E2E TEST SUITE STARTING
============================================================

▶️  Starting: complete signup → login → logout flow
   File: e2e/critical-paths/auth.spec.ts:8

🧪 [2026-01-19T18:00:00.000Z] [test_abc123] [E2E] TEST_START | {"title":"complete signup → login → logout flow"}
ℹ️  [2026-01-19T18:00:00.100Z] [test_abc123] [E2E] Step 1: Signup
🔍 [2026-01-19T18:00:00.110Z] [test_abc123] [E2E] NAVIGATE | {"path":"/signup"}
🔍 [2026-01-19T18:00:00.500Z] [test_abc123] [E2E] NAVIGATION_COMPLETE | {"path":"/signup","url":"http://localhost:5557/signup"}
🔍 [2026-01-19T18:00:00.510Z] [test_abc123] [E2E] FILL_FORM | {"fields":["name","email","password"]}
🔍 [2026-01-19T18:00:00.800Z] [test_abc123] [E2E] CLICK | {"selector":"[data-testid=\"signup-button\"]"}
ℹ️  [2026-01-19T18:00:01.200Z] [test_abc123] [E2E] Signup completed
ℹ️  [2026-01-19T18:00:01.210Z] [test_abc123] [E2E] Step 2: Verify Dashboard
🔍 [2026-01-19T18:00:01.220Z] [test_abc123] [E2E] ASSERT_VISIBLE | {"selector":"[data-testid=\"user-menu\"]"}
🔍 [2026-01-19T18:00:01.230Z] [test_abc123] [E2E] ASSERTION_PASSED | {"selector":"[data-testid=\"user-menu\"]"}
🧪 [2026-01-19T18:00:02.000Z] [test_abc123] [E2E] SCENARIO_COMPLETE | {"name":"Complete Auth Flow","status":"passed"}

✅ complete signup → login → logout flow
   Duration: 2450ms
   Status: passed
```

### Failed Test Run
```
▶️  Starting: create and schedule a post
   File: e2e/critical-paths/post-creation.spec.ts:15

🧪 [2026-01-19T18:01:00.000Z] [test_def456] [E2E] TEST_START | {"title":"create and schedule a post"}
ℹ️  [2026-01-19T18:01:00.100Z] [test_def456] [E2E] Step 1: Open composer
🔍 [2026-01-19T18:01:00.110Z] [test_def456] [E2E] NAVIGATE | {"path":"/posts/new"}
❌ [2026-01-19T18:01:05.000Z] [test_def456] [E2E] NAVIGATION_ERROR | {"error":"Timeout waiting for navigation","url":"/posts/new"}
ℹ️  [2026-01-19T18:01:05.010Z] [test_def456] [E2E] SCREENSHOT_CAPTURED | {"path":"debug/navigation_failure_1705689665010.png"}

❌ create and schedule a post
   Duration: 5450ms
   Status: failed

   ─── Error Details ───
   Timeout 5000ms exceeded waiting for navigation to "/posts/new"

   ─── Stack Trace ───
      at TestHelpers.navigateTo (e2e/utils/helpers.ts:45:15)
      at Object.<anonymous> (e2e/critical-paths/post-creation.spec.ts:22:5)

   ─── Attachments ───
   📎 screenshot: test-results/create-and-schedule-a-post/screenshot.png
   📎 video: test-results/create-and-schedule-a-post/video.webm
```

---

## File Structure

```
e2e/
├── utils/
│   ├── test-utils.ts           # Extended test with logging
│   ├── debug-logger.ts         # Logging utilities
│   └── helpers.ts              # Test helper functions
├── reporters/
│   └── debug-reporter.ts       # Custom console reporter
├── fixtures/
│   ├── test-video.mp4          # Test media files
│   ├── test-image.jpg
│   └── users.json              # Test user data
├── critical-paths/
│   ├── auth.spec.ts            # Authentication tests
│   ├── post-creation.spec.ts   # Post creation tests
│   └── analytics.spec.ts       # Analytics tests
├── features/
│   ├── community-inbox.spec.ts
│   ├── content-repurposing.spec.ts
│   ├── link-in-bio.spec.ts
│   ├── media-discovery.spec.ts
│   └── voice-cloning.spec.ts
└── playwright.config.ts
```

---

## Running Tests

```bash
# Run all E2E tests
npm run test:e2e

# Run with debug logging (headed browser, slow motion)
DEBUG=1 npm run test:e2e

# Run specific test file
npm run test:e2e -- e2e/critical-paths/auth.spec.ts

# Run with trace on
npm run test:e2e -- --trace on

# View last test report
npx playwright show-report
```

---

## Implementation Timeline

| Day | Task |
|-----|------|
| 1-2 | Logger infrastructure (TS + Python) |
| 3-4 | Playwright setup, test utilities |
| 5-6 | Critical path tests (auth, posts, analytics) |
| 7-8 | Feature tests (inbox, repurposing) |
| 9-10 | Debug reporter, documentation |

---

**Document Owner:** Engineering Team  
**Last Updated:** January 19, 2026
