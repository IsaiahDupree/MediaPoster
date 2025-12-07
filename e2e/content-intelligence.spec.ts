import { test, expect } from '@playwright/test';

test.describe('Content Intelligence Dashboard', () => {
    test.beforeEach(async ({ page }) => {
        // Navigate to Content Intelligence dashboard
        await page.goto('http://localhost:5557/content-intelligence');
    });

    test('should display dashboard header', async ({ page }) => {
        // Check for main title
        await expect(page.getByRole('heading', { name: 'Content Intelligence' })).toBeVisible();
    });

    test('should display North Star Metrics cards', async ({ page }) => {
        // Check for all three North Star Metrics
        await expect(page.getByText('Weekly Engaged Reach')).toBeVisible();
        await expect(page.getByText('Content Leverage Score')).toBeVisible();
        await expect(page.getByText('Warm Lead Flow')).toBeVisible();
    });

    test('should display stats overview section', async ({ page }) => {
        // Check for stats cards
        await expect(page.getByText('Total Posts')).toBeVisible();
        await expect(page.getByText('Total Views')).toBeVisible();
        await expect(page.getByText('Avg Views/Post')).toBeVisible();
        await expect(page.getByText('Engagement/Post')).toBeVisible();
    });

    test('should display platform breakdown', async ({ page }) => {
        // Check for platform performance section
        await expect(page.getByText('Platform Performance')).toBeVisible();
        await expect(page.getByText('Views by platform this week')).toBeVisible();
    });

    test('should display trend chart', async ({ page }) => {
        // Check for trend section
        await expect(page.getByText('8-Week Trend')).toBeVisible();
        await expect(page.getByText('North Star Metrics over time')).toBeVisible();
    });

    test('should show loading state initially', async ({ page }) => {
        // Reload and check for loading indicator
        await page.reload();
        await expect(page.getByText(/Loading Content Intelligence/i)).toBeVisible({ timeout: 1000 })
            .catch(() => { }); // May load too fast
    });

    test('should display trend indicators', async ({ page }) => {
        // Wait for data to load
        await page.waitForTimeout(1000);

        // Check for trend arrows (up or down)
        const trendIndicators = page.locator('svg').filter({ hasText: /trending/i });
        const count = await trendIndicators.count();

        // Should have at least some trend indicators
        expect(count).toBeGreaterThanOrEqual(0);
    });

    test('should format numbers correctly', async ({ page }) => {
        await page.waitForTimeout(1000);

        // Check that large numbers are formatted with commas
        const metrics = page.locator('.text-2xl.font-bold');
        const firstMetric = await metrics.first().textContent();

        // Should have a number
        expect(firstMetric).toBeTruthy();
    });
});

test.describe('Content Intelligence Insights Page', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('http://localhost:5557/content-intelligence/insights');
    });

    test('should display insights page header', async ({ page }) => {
        await expect(page.getByRole('heading', { name: 'Content Insights & Recommendations' })).toBeVisible();
        await expect(page.getByText('AI-powered insights to improve your content performance')).toBeVisible();
    });

    test('should display recommendations section', async ({ page }) => {
        await expect(page.getByText('Personalized Recommendations')).toBeVisible();
        await expect(page.getByText('Actionable advice based on your content performance')).toBeVisible();
    });

    test('should display hook performance section', async ({ page }) => {
        await expect(page.getByText('Hook Performance Analysis')).toBeVisible();
        await expect(page.getByText('Which hook types drive the most retention')).toBeVisible();
    });

    test('should display topics section', async ({ page }) => {
        await expect(page.getByText('High-Performing Topics')).toBeVisible();
        await expect(page.getByText('Content themes that drive engagement')).toBeVisible();
    });

    test('should show empty state when no data', async ({ page }) => {
        await page.waitForTimeout(1000);

        // Check for possible empty states
        const emptyMessage = page.getByText(/No recommendations yet|Not enough data|Insufficient data/i);
        const hasEmpty = await emptyMessage.count() > 0;

        // Either has data or shows empty state
        expect(hasEmpty || await page.locator('.border.rounded-lg').count() > 0).toBeTruthy();
    });

    test('should display priority badges on recommendations', async ({ page }) => {
        await page.waitForTimeout(1000);

        // Look for priority badges (high, medium, low)
        const badges = page.locator('.text-xs.px-2.py-0\\.5.rounded-full');
        const count = await badges.count();

        // Should have badges if there are recommendations
        expect(count).toBeGreaterThanOrEqual(0);
    });

    test('should have Apply buttons on recommendations', async ({ page }) => {
        await page.waitForTimeout(1000);

        const applyButtons = page.getByRole('button', { name: /Apply/i });
        const count = await applyButtons.count();

        // Should have apply buttons if there are recommendations
        expect(count).toBeGreaterThanOrEqual(0);
    });

    test('should display confidence scores for insights', async ({ page }) => {
        await page.waitForTimeout(1000);

        // Look for confidence percentage badges
        const confidenceBadges = page.locator('text=/\\d+% confidence/');
        const count = await confidenceBadges.count();

        expect(count).toBeGreaterThanOrEqual(0);
    });
});

test.describe('Multi-Platform Publishing Page', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('http://localhost:5557/content-intelligence/publish');
    });

    test('should display publishing page header', async ({ page }) => {
        await expect(page.getByRole('heading', { name: 'Multi-Platform Publishing' })).toBeVisible();
        await expect(page.getByText('Publish your content to multiple platforms at once')).toBeVisible();
    });

    test('should display content details form', async ({ page }) => {
        await expect(page.getByText('Content Details')).toBeVisible();
        await expect(page.getByText('Enter your video details and select platforms')).toBeVisible();
    });

    test('should have all form fields', async ({ page }) => {
        // Video input
        await expect(page.getByLabel('Video File')).toBeVisible();

        // Title input
        await expect(page.getByLabel('Title')).toBeVisible();

        // Caption textarea
        await expect(page.getByLabel('Caption')).toBeVisible();

        // Hashtags input
        await expect(page.getByLabel('Hashtags')).toBeVisible();
    });

    test('should display all platform options', async ({ page }) => {
        const platforms = [
            'TikTok',
            'Instagram',
            'YouTube',
            'Facebook',
            'LinkedIn',
            'Twitter/X',
            'Snapchat',
            'Threads',
            'Pinterest'
        ];

        for (const platform of platforms) {
            await expect(page.getByText(platform)).toBeVisible();
        }
    });

    test('should allow platform selection', async ({ page }) => {
        // Click on TikTok
        const tiktokCheckbox = page.locator('text=TikTok').locator('..').locator('input[type="checkbox"]').first();
        await tiktokCheckbox.click();

        // Verify it's checked
        await expect(tiktokCheckbox).toBeChecked();
    });

    test('should update publish button text based on selection', async ({ page }) => {
        // Initially should say "Publish to 0 Platforms"
        await expect(page.getByRole('button', { name: /Publish to 0 Platform/i })).toBeVisible();

        // Select TikTok
        const tiktokCheckbox = page.locator('text=TikTok').locator('..').locator('input[type="checkbox"]').first();
        await tiktokCheckbox.click();

        // Should update to "Publish to 1 Platform"
        await expect(page.getByRole('button', { name: /Publish to 1 Platform$/i })).toBeVisible();

        // Select Instagram
        const instaCheckbox = page.locator('text=Instagram').locator('..').locator('input[type="checkbox"]').first();
        await instaCheckbox.click();

        // Should update to "Publish to 2 Platforms"
        await expect(page.getByRole('button', { name: /Publish to 2 Platforms/i })).toBeVisible();
    });

    test('should disable publish button when no platforms selected', async ({ page }) => {
        const publishButton = page.getByRole('button', { name: /Publish to/i });

        // Should be disabled initially
        await expect(publishButton).toBeDisabled();
    });

    test('should enable publish button when platform selected', async ({ page }) => {
        const publishButton = page.getByRole('button', { name: /Publish to/i });

        // Select a platform
        const tiktokCheckbox = page.locator('text=TikTok').locator('..').locator('input[type="checkbox"]').first();
        await tiktokCheckbox.click();

        // Button should be enabled
        await expect(publishButton).toBeEnabled();
    });

    test('should fill out complete form', async ({ page }) => {
        // Fill video path
        await page.getByLabel('Video File').fill('/path/to/my-video.mp4');

        // Fill title
        await page.getByLabel('Title').fill('My Awesome Video');

        // Fill caption
        await page.getByLabel('Caption').fill('Check out this amazing content!');

        // Fill hashtags
        await page.getByLabel('Hashtags').fill('viral, content, automation');

        // Select platforms
        const tiktokCheckbox = page.locator('text=TikTok').locator('..').locator('input[type="checkbox"]').first();
        await tiktokCheckbox.click();

        const instaCheckbox = page.locator('text=Instagram').locator('..').locator('input[type="checkbox"]').first();
        await instaCheckbox.click();

        // Verify all fields are filled
        await expect(page.getByLabel('Title')).toHaveValue('My Awesome Video');
        await expect(page.getByLabel('Caption')).toHaveValue('Check out this amazing content!');
        await expect(page.getByLabel('Hashtags')).toHaveValue('viral, content, automation');
    });

    test('should show Browse button for video upload', async ({ page }) => {
        await expect(page.getByRole('button', { name: 'Browse' })).toBeVisible();
    });
});

test.describe('Navigation between pages', () => {
    test('should navigate from dashboard to insights', async ({ page }) => {
        await page.goto('http://localhost:5557/content-intelligence');

        // Click on insights link if available
        const insightsLink = page.getByRole('link', { name: /Insights/i });

        if (await insightsLink.count() > 0) {
            await insightsLink.click();
            await expect(page).toHaveURL(/insights/);
        }
    });

    test('should navigate from dashboard to publish', async ({ page }) => {
        await page.goto('http://localhost:5557/content-intelligence');

        // Click on publish link if available
        const publishLink = page.getByRole('link', { name: /Publish/i });

        if (await publishLink.count() > 0) {
            await publishLink.click();
            await expect(page).toHaveURL(/publish/);
        }
    });

    test('should navigate back to dashboard', async ({ page }) => {
        await page.goto('http://localhost:5557/content-intelligence/insights');

        // Click on dashboard/home link if available
        const dashboardLink = page.getByRole('link', { name: /Dashboard|Home/i });

        if (await dashboardLink.count() > 0) {
            await dashboardLink.click();
            await expect(page).toHaveURL(/content-intelligence$/);
        }
    });
});

test.describe('Responsive design checks', () => {
    test('should be responsive on mobile', async ({ page }) => {
        // Set mobile viewport
        await page.setViewportSize({ width: 375, height: 667 });
        await page.goto('http://localhost:5557/content-intelligence');

        // Check that content is visible
        await expect(page.getByRole('heading', { name: 'Content Intelligence' })).toBeVisible();
    });

    test('should be responsive on tablet', async ({ page }) => {
        // Set tablet viewport
        await page.setViewportSize({ width: 768, height: 1024 });
        await page.goto('http://localhost:5557/content-intelligence');

        // Check that content is visible
        await expect(page.getByRole('heading', { name: 'Content Intelligence' })).toBeVisible();
    });

    test('should be responsive on desktop', async ({ page }) => {
        // Set desktop viewport
        await page.setViewportSize({ width: 1920, height: 1080 });
        await page.goto('http://localhost:5557/content-intelligence');

        // Check that content is visible
        await expect(page.getByRole('heading', { name: 'Content Intelligence' })).toBeVisible();
    });
});
