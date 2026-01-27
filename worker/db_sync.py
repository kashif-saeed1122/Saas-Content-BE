import os
import json
from sqlalchemy import create_engine, text
from config import Config

def save_research_data(article_id: str, sources: list):
    """Saves raw scraped content into the source_contents table."""
    engine = create_engine(Config.DB_URL)
    try:
        with engine.connect() as conn:
            for src in sources:
                stmt = text("""
                    INSERT INTO source_contents (id, article_id, url, title, full_content, source_origin)
                    VALUES (gen_random_uuid(), :article_id, :url, :title, :content, :origin)
                """)
                conn.execute(stmt, {
                    "article_id": article_id,
                    "url": src['url'],
                    "title": src['title'],
                    "content": src.get('full_content', ''),
                    "origin": src.get('source_origin', 'Search')
                })
            conn.commit()
    except Exception as e:
        print(f"Error saving research: {e}")

def finalize_article_in_db(article_id: str, content: str, seo_brief: dict):
    """Updates the article and saves the brief."""
    engine = create_engine(Config.DB_URL)
    try:
        with engine.connect() as conn:
            # 1. Save SEO Brief
            conn.execute(text("""
                INSERT INTO seo_briefs (id, article_id, keywords, outline, strategy)
                VALUES (gen_random_uuid(), :a_id, :keywords, :outline, :strategy)
            """), {
                "a_id": article_id,
                "keywords": json.dumps(seo_brief.get('keywords', [])),
                "outline": json.dumps(seo_brief.get('detailed_outline', {})),
                "strategy": seo_brief.get('strategy', '')
            })
            
            # 2. Update Article Status
            # Logic: If scheduled_at > now, status is 'scheduled', else 'completed'
            conn.execute(text("""
                UPDATE articles 
                SET content = :content,
                    status = CASE 
                        WHEN scheduled_at > NOW() THEN 'scheduled' 
                        ELSE 'completed' 
                    END
                WHERE id = :id
            """), {"content": content, "id": article_id})
            
            conn.commit()
    except Exception as e:
        print(f"Error finalizing: {e}")