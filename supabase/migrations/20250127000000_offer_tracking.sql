-- Migration 015: Offer Traffic Tracking (ARCH-005)
-- ================================================
-- Creates tables for tracking offer traffic, conversions, and analytics.
-- Used by OfferTracker service for campaign ROI measurement.

-- Campaigns table: Track offer campaigns
CREATE TABLE IF NOT EXISTS offer_campaigns (
    id BIGSERIAL PRIMARY KEY,
    campaign_name VARCHAR(200) UNIQUE NOT NULL,
    offer_url TEXT NOT NULL,
    offer_description TEXT,
    utm_campaign VARCHAR(200) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    ended_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'active',
    metadata JSONB DEFAULT '{}',

    CONSTRAINT valid_status CHECK (status IN ('active', 'paused', 'completed', 'cancelled'))
);

-- Traffic table: Track clicks/visits to offer URLs
CREATE TABLE IF NOT EXISTS offer_traffic (
    id BIGSERIAL PRIMARY KEY,
    utm_campaign VARCHAR(200) NOT NULL,
    utm_source VARCHAR(100) NOT NULL DEFAULT 'twitter',
    utm_medium VARCHAR(100) NOT NULL DEFAULT 'social',
    utm_content VARCHAR(200),
    utm_term VARCHAR(200),

    -- User identification
    user_id VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    referrer TEXT,

    -- Geolocation (optional)
    country_code VARCHAR(2),
    region VARCHAR(100),
    city VARCHAR(100),

    -- Device info
    device_type VARCHAR(50), -- mobile, desktop, tablet
    browser VARCHAR(100),
    os VARCHAR(100),

    -- Timestamps
    clicked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Additional metadata
    metadata JSONB DEFAULT '{}'
);

-- Indexes for offer_traffic
CREATE INDEX IF NOT EXISTS idx_offer_traffic_campaign ON offer_traffic(utm_campaign);
CREATE INDEX IF NOT EXISTS idx_offer_traffic_clicked_at ON offer_traffic(clicked_at);
CREATE INDEX IF NOT EXISTS idx_offer_traffic_source ON offer_traffic(utm_source);
CREATE INDEX IF NOT EXISTS idx_offer_traffic_content ON offer_traffic(utm_content);
CREATE INDEX IF NOT EXISTS idx_offer_traffic_ip ON offer_traffic(ip_address);

-- Conversions table: Track conversion events (purchases, signups, etc.)
CREATE TABLE IF NOT EXISTS offer_conversions (
    id BIGSERIAL PRIMARY KEY,
    utm_campaign VARCHAR(200) NOT NULL,
    utm_content VARCHAR(200),

    -- Conversion details
    conversion_type VARCHAR(100) NOT NULL, -- purchase, signup, trial, demo, contact, etc.
    user_id VARCHAR(100),

    -- Financial data
    revenue DECIMAL(10, 2),
    currency VARCHAR(3) DEFAULT 'USD',

    -- Attribution
    traffic_id BIGINT REFERENCES offer_traffic(id) ON DELETE SET NULL,
    attributed_at TIMESTAMP WITH TIME ZONE,
    attribution_window_hours INTEGER DEFAULT 72, -- How long after click did conversion happen

    -- Timestamps
    converted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Additional conversion data
    conversion_data JSONB DEFAULT '{}'
);

-- Indexes for offer_conversions
CREATE INDEX IF NOT EXISTS idx_offer_conversions_campaign ON offer_conversions(utm_campaign);
CREATE INDEX IF NOT EXISTS idx_offer_conversions_converted_at ON offer_conversions(converted_at);
CREATE INDEX IF NOT EXISTS idx_offer_conversions_type ON offer_conversions(conversion_type);
CREATE INDEX IF NOT EXISTS idx_offer_conversions_traffic_id ON offer_conversions(traffic_id);

-- Campaign Analytics: Pre-aggregated campaign metrics (updated periodically)
CREATE TABLE IF NOT EXISTS campaign_analytics (
    id BIGSERIAL PRIMARY KEY,
    utm_campaign VARCHAR(200) NOT NULL,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Traffic metrics
    total_clicks INTEGER DEFAULT 0,
    unique_clicks INTEGER DEFAULT 0,
    unique_ips INTEGER DEFAULT 0,

    -- Conversion metrics
    total_conversions INTEGER DEFAULT 0,
    conversion_rate DECIMAL(5, 2) DEFAULT 0, -- Percentage

    -- Revenue metrics
    total_revenue DECIMAL(10, 2) DEFAULT 0,
    avg_order_value DECIMAL(10, 2) DEFAULT 0,

    -- ROI metrics
    estimated_cost DECIMAL(10, 2) DEFAULT 0,
    profit DECIMAL(10, 2) DEFAULT 0,
    roi_percentage DECIMAL(8, 2) DEFAULT 0,

    -- Content variant performance
    top_performing_content VARCHAR(200),
    top_content_conversions INTEGER DEFAULT 0,

    -- Updated timestamp
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE (utm_campaign, period_start, period_end)
);

-- Indexes for campaign_analytics
CREATE INDEX IF NOT EXISTS idx_campaign_analytics_campaign ON campaign_analytics(utm_campaign);
CREATE INDEX IF NOT EXISTS idx_campaign_analytics_period ON campaign_analytics(period_start, period_end);

-- Function to calculate attribution for conversions
CREATE OR REPLACE FUNCTION calculate_conversion_attribution()
RETURNS TRIGGER AS $$
DECLARE
    matching_traffic_id BIGINT;
    click_time TIMESTAMP WITH TIME ZONE;
BEGIN
    -- Try to find matching traffic record within attribution window
    SELECT id, clicked_at INTO matching_traffic_id, click_time
    FROM offer_traffic
    WHERE utm_campaign = NEW.utm_campaign
      AND (NEW.user_id IS NOT NULL AND user_id = NEW.user_id)
      AND clicked_at <= NEW.converted_at
      AND clicked_at >= NEW.converted_at - INTERVAL '72 hours'
    ORDER BY clicked_at DESC
    LIMIT 1;

    IF matching_traffic_id IS NOT NULL THEN
        NEW.traffic_id := matching_traffic_id;
        NEW.attributed_at := click_time;
        NEW.attribution_window_hours := EXTRACT(EPOCH FROM (NEW.converted_at - click_time)) / 3600;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-calculate attribution on conversion insert
CREATE TRIGGER conversion_attribution_trigger
    BEFORE INSERT ON offer_conversions
    FOR EACH ROW
    EXECUTE FUNCTION calculate_conversion_attribution();

-- Function to update campaign analytics (call periodically)
CREATE OR REPLACE FUNCTION update_campaign_analytics(
    p_campaign VARCHAR(200),
    p_period_start TIMESTAMP WITH TIME ZONE,
    p_period_end TIMESTAMP WITH TIME ZONE
)
RETURNS VOID AS $$
DECLARE
    v_total_clicks INTEGER;
    v_unique_clicks INTEGER;
    v_unique_ips INTEGER;
    v_total_conversions INTEGER;
    v_total_revenue DECIMAL(10, 2);
    v_conversion_rate DECIMAL(5, 2);
    v_avg_order_value DECIMAL(10, 2);
    v_estimated_cost DECIMAL(10, 2);
    v_profit DECIMAL(10, 2);
    v_roi_percentage DECIMAL(8, 2);
    v_top_content VARCHAR(200);
    v_top_content_conversions INTEGER;
BEGIN
    -- Calculate traffic metrics
    SELECT
        COUNT(*),
        COUNT(DISTINCT COALESCE(user_id, ip_address::TEXT)),
        COUNT(DISTINCT ip_address)
    INTO v_total_clicks, v_unique_clicks, v_unique_ips
    FROM offer_traffic
    WHERE utm_campaign = p_campaign
      AND clicked_at BETWEEN p_period_start AND p_period_end;

    -- Calculate conversion metrics
    SELECT
        COUNT(*),
        COALESCE(SUM(revenue), 0)
    INTO v_total_conversions, v_total_revenue
    FROM offer_conversions
    WHERE utm_campaign = p_campaign
      AND converted_at BETWEEN p_period_start AND p_period_end;

    -- Calculate rates
    v_conversion_rate := CASE
        WHEN v_unique_clicks > 0 THEN (v_total_conversions::DECIMAL / v_unique_clicks * 100)
        ELSE 0
    END;

    v_avg_order_value := CASE
        WHEN v_total_conversions > 0 THEN (v_total_revenue / v_total_conversions)
        ELSE 0
    END;

    -- Calculate ROI (assuming $0.10 per click)
    v_estimated_cost := v_total_clicks * 0.10;
    v_profit := v_total_revenue - v_estimated_cost;
    v_roi_percentage := CASE
        WHEN v_estimated_cost > 0 THEN (v_profit / v_estimated_cost * 100)
        ELSE 0
    END;

    -- Find top-performing content variant
    SELECT
        utm_content,
        COUNT(c.id)
    INTO v_top_content, v_top_content_conversions
    FROM offer_traffic t
    LEFT JOIN offer_conversions c
        ON t.utm_campaign = c.utm_campaign
        AND t.utm_content = c.utm_content
        AND c.converted_at BETWEEN p_period_start AND p_period_end
    WHERE t.utm_campaign = p_campaign
      AND t.clicked_at BETWEEN p_period_start AND p_period_end
    GROUP BY utm_content
    ORDER BY COUNT(c.id) DESC
    LIMIT 1;

    -- Insert or update analytics record
    INSERT INTO campaign_analytics (
        utm_campaign, period_start, period_end,
        total_clicks, unique_clicks, unique_ips,
        total_conversions, conversion_rate,
        total_revenue, avg_order_value,
        estimated_cost, profit, roi_percentage,
        top_performing_content, top_content_conversions,
        calculated_at
    ) VALUES (
        p_campaign, p_period_start, p_period_end,
        v_total_clicks, v_unique_clicks, v_unique_ips,
        v_total_conversions, v_conversion_rate,
        v_total_revenue, v_avg_order_value,
        v_estimated_cost, v_profit, v_roi_percentage,
        v_top_content, v_top_content_conversions,
        NOW()
    )
    ON CONFLICT (utm_campaign, period_start, period_end)
    DO UPDATE SET
        total_clicks = EXCLUDED.total_clicks,
        unique_clicks = EXCLUDED.unique_clicks,
        unique_ips = EXCLUDED.unique_ips,
        total_conversions = EXCLUDED.total_conversions,
        conversion_rate = EXCLUDED.conversion_rate,
        total_revenue = EXCLUDED.total_revenue,
        avg_order_value = EXCLUDED.avg_order_value,
        estimated_cost = EXCLUDED.estimated_cost,
        profit = EXCLUDED.profit,
        roi_percentage = EXCLUDED.roi_percentage,
        top_performing_content = EXCLUDED.top_performing_content,
        top_content_conversions = EXCLUDED.top_content_conversions,
        calculated_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE offer_campaigns IS 'ARCH-005: Offer campaign metadata and configuration';
COMMENT ON TABLE offer_traffic IS 'ARCH-005: Click/visit tracking for offer URLs';
COMMENT ON TABLE offer_conversions IS 'ARCH-005: Conversion events with revenue tracking';
COMMENT ON TABLE campaign_analytics IS 'ARCH-005: Pre-aggregated campaign performance metrics';
COMMENT ON FUNCTION calculate_conversion_attribution() IS 'ARCH-005: Auto-attribute conversions to traffic sources';
COMMENT ON FUNCTION update_campaign_analytics(VARCHAR, TIMESTAMP WITH TIME ZONE, TIMESTAMP WITH TIME ZONE) IS 'ARCH-005: Calculate and update campaign analytics';
