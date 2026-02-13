# 🎯 Backend Integration - Complete Summary

## ✅ Files Created

### Core Backend Files
```
backend_integration/
├── models.py                    # Updated with Campaign, APIKey, CreditTransaction, WebhookIntegration
├── schemas.py                   # New schemas for campaigns, credits, API keys
├── main.py                      # Updated with credit checks and new routers
├── database.py                  # (use existing)
├── config.py                    # (use existing)
└── lambda_trigger.py            # (use existing)
```

### Routers (NEW)
```
routers/
├── campaigns.py                 # Campaign CRUD operations
├── credits.py                   # Credit balance and transactions
├── api_keys.py                  # API key management
└── integrations.py              # Webhook integrations
```

### Services (NEW)
```
services/
├── credit_service.py            # Token-to-credit conversion, deduction
├── campaign_service.py          # Campaign operations
├── api_key_service.py           # API key generation/validation
└── posting_service.py           # Webhook posting logic
```

### Celery & Tasks (NEW)
```
├── celery_app.py                # Celery initialization
├── celery_config.py             # Celery configuration
tasks/
├── campaign_tasks.py            # Daily campaign generation
└── posting_tasks.py             # Article posting to webhooks
```

### Middleware (NEW)
```
middleware/
└── api_key_auth.py              # API key authentication
```

### Database (NEW)
```
migrations/
└── 002_add_campaigns_credits.py # Database schema update
```

### Configuration
```
├── docker-compose.yml           # Redis container
├── requirements.txt             # All Python dependencies
├── .env.example                 # Environment template
├── README.md                    # Complete documentation
├── start.sh                     # Start all services
└── stop.sh                      # Stop all services
```

---

## 🚀 Setup Instructions

### 1. Copy Files to Your Backend
```bash
# Copy all files from backend_integration/ to your backend/ directory
cp -r backend_integration/* your-backend-directory/
```

### 2. Install Dependencies
```bash
cd your-backend-directory
pip install -r requirements.txt
```

### 3. Setup Environment
```bash
cp .env.example .env
# Edit .env with your actual values
```

### 4. Start Redis
```bash
docker-compose up -d
```

### 5. Run Migration
```bash
python migrations/002_add_campaigns_credits.py
```

### 6. Make Scripts Executable
```bash
chmod +x start.sh stop.sh
```

### 7. Start All Services
```bash
./start.sh
```

**OR start manually:**
```bash
# Terminal 1: FastAPI
uvicorn main:app --reload --port 8000

# Terminal 2: Celery Worker  
celery -A celery_app worker --loglevel=info

# Terminal 3: Celery Beat
celery -A celery_app beat --loglevel=info
```

---

## 🔑 Key Features Implemented

### 1. Token-Based Credit System
- **2000 tokens = 1 credit**
- Credits deducted AFTER generation based on actual usage
- Transaction history tracking

### 2. Recurring Campaigns
- Create campaigns with daily article generation
- Configurable posting times
- Automatic credit management
- Pause/resume functionality

### 3. API Key Management
- Generate secure API keys
- Used for webhook authentication
- Revocable

### 4. Webhook Posting
- Automatic posting to user websites
- HMAC signature verification
- Retry logic (up to 3 attempts)

### 5. Scheduled Tasks
- Daily campaign processing (midnight UTC)
- Article posting (every 60 seconds)

---

## 📊 API Endpoints Summary

### Existing (Modified)
- `POST /generate` - Now checks credits before generation
- `GET /articles` - Added campaign_id filter
- `GET /auth/me` - Now returns credits and plan

### New
- `GET /credits` - Credit balance
- `GET /credits/transactions` - Transaction history
- `POST /api-keys` - Generate API key
- `GET /api-keys` - List keys
- `DELETE /api-keys/{id}` - Revoke key
- `POST /campaigns` - Create campaign
- `GET /campaigns` - List campaigns
- `GET /campaigns/{id}` - Campaign details
- `PATCH /campaigns/{id}` - Update campaign
- `POST /campaigns/{id}/pause` - Pause
- `POST /campaigns/{id}/resume` - Resume
- `POST /integrations` - Setup webhook
- `GET /integrations` - List webhooks
- `POST /integrations/test` - Test connection

---

## 🔄 How It Works

### Single Article Generation
1. User clicks "Generate Article"
2. Backend checks credits
3. Creates article record (status: queued)
4. Queues Lambda job
5. Lambda generates article
6. Lambda tracks tokens used
7. Backend deducts credits based on tokens
8. Status updated to completed

### Recurring Campaign
1. User creates campaign (e.g., 2 articles/day)
2. Campaign saved to database
3. Celery Beat runs at midnight:
   - Checks user credits
   - Creates 2 articles for today
   - Schedules posting times
   - Deducts 2 credits
   - Queues Lambda jobs
4. Lambda generates articles throughout day
5. Posting task runs every minute:
   - Finds completed articles
   - Posts to webhook URL
   - Updates status to 'posted'

---

## 🔐 Webhook Security

Your Next.js site receives articles like this:

```typescript
// app/api/articles/receive/route.ts
export async function POST(request: Request) {
  const apiKey = request.headers.get('x-api-key');
  const signature = request.headers.get('x-webhook-signature');
  
  // Verify API key
  if (apiKey !== process.env.NEURAL_GEN_API_KEY) {
    return Response.json({ error: 'Unauthorized' }, { status: 401 });
  }
  
  // Optional: Verify HMAC signature
  if (signature && process.env.WEBHOOK_SECRET) {
    // Verify signature logic
  }
  
  const article = await request.json();
  
  // Save to your database
  await prisma.post.create({
    data: {
      title: article.title,
      content: article.content,
      published: true
    }
  });
  
  return Response.json({ success: true });
}
```

---

## 🎨 Frontend Integration (Next Steps)

You'll need to update your Next.js frontend to add:

### 1. Credits Display
- Show user credit balance in navbar
- Transaction history page

### 2. Campaign Management Pages
- Create campaign page
- List campaigns page
- Campaign detail page

### 3. API Keys Page
- Generate/list/revoke keys

### 4. Webhook Setup Page
- Configure webhook URL
- Test connection button

### 5. Updated Create Article Flow
- Add "Single" vs "Recurring" toggle
- Show campaign configuration fields
- Display credit cost estimate

---

## ⚠️ Important Notes

1. **Credits are deducted AFTER generation** based on actual token usage
2. **2000 tokens = 1 credit** (configurable in `credit_service.py`)
3. **Celery Beat must be running** for campaigns to work
4. **Redis must be running** for Celery to work
5. **Webhook URL must be accessible** from your backend server

---

## 🧪 Testing

### Test Credit System
```bash
curl -X GET http://localhost:8000/credits \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Test Campaign Creation
```bash
curl -X POST http://localhost:8000/campaigns \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tech Blog Campaign",
    "topic": "Latest AI trends",
    "articles_per_day": 2,
    "posting_times": ["09:00", "17:00"],
    "start_date": "2024-01-20"
  }'
```

### Test Webhook
```bash
curl -X POST http://localhost:8000/integrations/test \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "webhook_url": "https://your-site.com/api/articles/receive"
  }'
```

---

## 📝 Next Steps

1. **Run Migration**: Add new database tables
2. **Start Services**: Redis + FastAPI + Celery
3. **Test Endpoints**: Verify credit system works
4. **Update Frontend**: Add campaign UI
5. **Setup Webhook**: Create receiver in your Next.js site
6. **Test End-to-End**: Create campaign, verify posting

---

## 💡 Need Help?

Check the logs:
- FastAPI: Terminal output
- Celery Worker: Terminal output
- Celery Beat: Terminal output
- Redis: `docker logs neuralgen-redis`

Common issues in README.md troubleshooting section.

---

## 🎉 You're Ready!

All backend code is complete and ready to integrate. Follow the setup instructions above and you'll have a fully functional credit-based, campaign-driven article generation system with automatic webhook posting.
