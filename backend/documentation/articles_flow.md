## 3. DATA FLOW
# 3.1 Single Article Generation Flow
User Request → FastAPI → Create Article (DB)
                    ↓
                SQS Queue
                    ↓
            Lambda Worker
                    ↓
        [Research → Scrape → Analyze → Write]
                    ↓
            Update Article (DB)
                    ↓
        POST /internal/article-complete
                    ↓
            FastAPI receives callback
                    ↓
        Update tokens_used (DB)
                    ↓
    Trigger webhook_post (Celery)
                    ↓
        POST to user's webhook URL
                    ↓
            Update status = 'posted'

## 3.2 Campaign Generation Flow
User creates campaign → FastAPI validates credits
                              ↓
                    Campaign created (DB)
                              ↓
                    Celery Beat (hourly check)
                              ↓
            Match current time vs posting_times
                              ↓
                Generate titles via AI
                              ↓
            Create articles with scheduled_at
                              ↓
                    Queue to SQS
                              ↓
                Lambda generates articles
                              ↓
            Callback to /internal/article-complete
                              ↓
                Trigger webhook posting
                              ↓
            POST to campaign webhook URL


## 3.3 Webhook Delivery Flow
Article status = 'completed'
        ↓
Celery Beat checks every 60s
        ↓
Find articles where:
  - status = 'completed'
  - webhook_integration_id NOT NULL
  - posted_at IS NULL
  - scheduled_at <= NOW() OR NULL
        ↓
For each article:
  - Fetch webhook_integration
  - Build payload (id, title, content, category)
  - Add X-Webhook-Signature (HMAC-SHA256)
  - Add X-API-Key from user
  - POST to webhook_url
        ↓
Success:
  - status = 'posted'
  - posted_at = NOW()
  - campaign.articles_posted += 1
        ↓
Failure (retry < 3):
  - posting_attempt_count += 1
  - last_posting_error = error message
  - Retry after 5 minutes