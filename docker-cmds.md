docker run -p 9000:8080 `
      --add-host host.docker.internal:host-gateway `
      -e OPENAI_API_KEY="sk-..." `
      -e CUSTOM_SEARCH_KEY="" `
      -e GOOGLE_CSE_ID="" `
      -e DATABASE_URL="postgresql://postgres:password@host.docker.internal:5432/seo_db" `
      seo-worker

## powershell cmd
Invoke-RestMethod -Uri "http://127.0.0.1:8000/generate" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"username": "dev_user", "topic": "Python vs Javascript", "category": "Tech"}'


## CMD 
curl -X POST "http://127.0.0.1:8000/generate" ^
 -H "Content-Type: application/json" ^
 -d "{\"username\": \"dev_user\", \"topic\": \"Python vs Javascript\", \"category\": \"Tech\"}"


docker build -t seo-worker .
