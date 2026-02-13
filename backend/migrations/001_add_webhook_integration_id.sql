-- Add webhook_integration_id to articles and campaigns
ALTER TABLE articles 
ADD COLUMN webhook_integration_id UUID REFERENCES webhook_integrations(id) ON DELETE SET NULL;

ALTER TABLE campaigns 
ADD COLUMN webhook_integration_id UUID REFERENCES webhook_integrations(id) ON DELETE SET NULL;

-- Add indexes for performance
CREATE INDEX idx_articles_webhook_integration ON articles(webhook_integration_id);
CREATE INDEX idx_campaigns_webhook_integration ON campaigns(webhook_integration_id);
CREATE INDEX idx_articles_scheduled_posting ON articles(status, scheduled_at, webhook_integration_id);
CREATE INDEX idx_campaigns_status_dates ON campaigns(status, start_date, end_date);