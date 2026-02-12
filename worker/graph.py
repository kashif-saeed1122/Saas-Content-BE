import asyncio
import json
from typing import TypedDict, List, Dict, Optional

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from scraper import scrape_urls
from db_sync import save_research_data, finalize_article_in_db
from search_tool import search_tool

# High-capability model for Analysis and Writing
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

class AgentState(TypedDict):
    article_id: str
    raw_query: str
    topic: str
    category: str
    target_length: int
    source_count: int
    urls: List[str]
    source_data: List[Dict]
    seo_brief: Dict
    final_content: str
    error: Optional[str]

# --- Nodes ---

async def search_node(state: AgentState):
    """Search for sources using the approved title as query"""
    print(f"--- 🕵️ Searching for: {state['topic']} ---")
    
    results = search_tool.invoke(state["topic"])
    
    # CRITICAL: Stop if no sources found
    if not results or len(results) == 0:
        error_msg = f"❌ ABORT: No articles found for '{state['topic']}'. Cannot generate content without sources."
        print(error_msg)
        raise Exception(error_msg)
    
    # Respect source_count constraint
    top_results = results[:state['source_count']]
    print(f"✅ Found {len(top_results)} sources to scrape")
    return {"urls": [r['url'] for r in top_results], "source_data": top_results}

async def scraper_node(state: AgentState):
    """Deep scrape the found sources"""
    print(f"--- 🕷️ Deep Scraping {len(state['urls'])} Sources ---")
    scraped = await scrape_urls(state["urls"])
    
    enhanced_sources = []
    for original in state["source_data"]:
        match = next((s for s in scraped if s['url'] == original['url']), None)
        if match and match.get('status') == 'success':
            original['full_content'] = match['content']
            enhanced_sources.append(original)
            
    if not enhanced_sources:
        error_msg = "❌ ABORT: Failed to extract content from all sources."
        print(error_msg)
        raise Exception(error_msg)
        
    save_research_data(state['article_id'], enhanced_sources)
    return {"source_data": enhanced_sources}

async def analyzer_node(state: AgentState):
    """Analyze sources and create comprehensive SEO brief with extensive outline"""
    print(f"--- 🧠 Analyzing {len(state['source_data'])} Sources for Deep Insights ---")
    
    # Build structured context from ALL sources
    dossier_context = ""
    for i, src in enumerate(state['source_data']):
        dossier_context += f"""
        <source id="{i+1}">
            <url>{src['url']}</url>
            <title>{src['title']}</title>
            <content>
            {src.get('full_content', 'No content available')[:15000]}
            </content>
        </source>
        """

    prompt = f"""
You are an elite SEO Research Strategist and Content Architect. You have been given {len(state['source_data'])} complete source articles to analyze.

ARTICLE TITLE: {state['topic']}
CATEGORY: {state['category']}
TARGET LENGTH: {state['target_length']} words

YOUR MISSION:
1. READ EVERY SOURCE COMPLETELY - Extract ALL unique facts, statistics, expert quotes, case studies, and insights
2. IDENTIFY TOP SEO KEYWORDS - Find 15-20 high-value keywords and phrases that will rank well in search
3. CREATE AN EXTENSIVE, DETAILED OUTLINE - This outline will guide a professional writer to create a comprehensive {state['target_length']}-word article

OUTLINE REQUIREMENTS:
- The outline must be EXTENSIVE and DETAILED - each section should have 3-5 specific points
- Each point must reference which sources support it (e.g., [Source 1, 3])
- Include specific facts, statistics, or insights to be covered in each section
- Structure should flow logically from introduction through body sections to conclusion
- For a {state['target_length']}-word article, create 5-8 main sections with detailed subsections
- Each section heading should be specific and actionable (not generic)

KEYWORD EXTRACTION RULES:
- Focus on keywords that appear frequently across multiple sources
- Include long-tail keywords (3-5 word phrases)
- Prioritize keywords relevant to search intent
- Include both primary keywords (high volume) and semantic keywords

RETURN ONLY THIS JSON STRUCTURE (no markdown, no extra text):
{{
    "keywords": [
        "primary keyword 1",
        "primary keyword 2",
        "long-tail keyword phrase",
        "semantic keyword",
        ... (15-20 total)
    ],
    "detailed_outline": [
        {{
            "level": 1,
            "heading": "Introduction: [Specific hook/angle]",
            "points": [
                "Open with compelling statistic or question that hooks readers [Source X]",
                "Establish the problem/opportunity this article addresses [Source Y]",
                "Preview the unique insights readers will gain [Sources X, Z]"
            ],
            "citations": [1, 2, 3]
        }},
        {{
            "level": 1,
            "heading": "[Main Topic/Section 1 - Be Specific]",
            "subsections": [
                {{
                    "level": 2,
                    "heading": "[Specific Subtopic 1.1]",
                    "points": [
                        "Specific fact or insight from research [Source X]",
                        "Supporting data point or example [Source Y]",
                        "Expert perspective or counterpoint [Source Z]"
                    ],
                    "citations": [1, 2]
                }},
                {{
                    "level": 2,
                    "heading": "[Specific Subtopic 1.2]",
                    "points": [
                        "Key insight with specific detail [Source X]",
                        "Real-world example or case study [Source Y]"
                    ],
                    "citations": [2, 3]
                }}
            ]
        }},
        {{
            "level": 1,
            "heading": "[Main Topic/Section 2 - Be Specific]",
            "subsections": [
                {{
                    "level": 2,
                    "heading": "[Specific Subtopic 2.1]",
                    "points": [
                        "Detailed point with data [Source X]",
                        "Supporting evidence or example [Source Y]"
                    ],
                    "citations": [1, 4]
                }}
            ]
        }},
        ... (Continue for 5-8 main sections total),
        {{
            "level": 1,
            "heading": "Conclusion: [Specific takeaway/call-to-action]",
            "points": [
                "Synthesize key insights from the article",
                "Provide actionable next steps for readers",
                "End with forward-looking perspective or call-to-action"
            ],
            "citations": [1, 2, 3, 4, 5]
        }}
    ],
    "strategy": "This article will rank well because: [explain unique value proposition, comprehensive coverage of topic, use of data-backed insights, addressing search intent, etc.]"
}}

CRITICAL: 
- Use ALL {len(state['source_data'])} sources - cite each source at least once
- Be SPECIFIC in section headings (not "Understanding X" but "Why X Matters for Y in 2025")
- Include concrete details in points (not "discuss benefits" but "how X increases Y by Z%")
- Create an outline so detailed that a writer can create a comprehensive article just by following it

RESEARCH SOURCES:
{dossier_context}

Now analyze these sources deeply and return the comprehensive JSON brief:
"""
    
    try:
        response = await llm.ainvoke(prompt)
        content = response.content.strip()
        
        # Clean up markdown code blocks if present
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()
        
        brief = json.loads(content)
        
        print(f"✅ Generated outline with {len(brief.get('detailed_outline', []))} main sections")
        print(f"✅ Extracted {len(brief.get('keywords', []))} SEO keywords")
        
        return {"seo_brief": brief}
    except Exception as e:
        print(f"⚠️ Error parsing analyzer response: {e}")
        # Fallback brief
        return {"seo_brief": {
            "keywords": [],
            "detailed_outline": [],
            "strategy": "Comprehensive coverage"
        }}

async def writer_node(state: AgentState):
    """Write expert-level, human content following the detailed outline"""
    print(f"--- ✍️ Writing Expert-Level {state['target_length']}-Word Article ---")
    
    # Convert outline to readable format
    outline_str = json.dumps(state['seo_brief']['detailed_outline'], indent=2)
    keywords_str = ', '.join(state['seo_brief'].get('keywords', [])[:15])
    
    prompt = f"""
You are a professional content writer with 10+ years of experience in {state['category']}. Write a comprehensive, engaging article that reads like it was written by a human expert - NOT an AI.

ARTICLE DETAILS:
Title: {state['topic']}
Category: {state['category']}
Target Length: {state['target_length']} words (±5%)
SEO Keywords: {keywords_str}

DETAILED OUTLINE TO FOLLOW:
{outline_str}

CRITICAL WRITING RULES - READ CAREFULLY:

1. WRITE LIKE A HUMAN EXPERT:
   - Use natural, conversational language (as if explaining to a colleague)
   - Vary sentence length: mix short punchy sentences with longer explanatory ones
   - Use active voice predominantly (passive voice < 10%)
   - Include personal insights and expert perspectives
   - Add smooth transitions between sections ("Here's what this means...", "The key takeaway here...", "But here's the interesting part...")

2. VOCABULARY & STYLE:
   - Use sophisticated but accessible vocabulary (avoid pretentious jargon)
   - Be specific and concrete (not vague or generic)
   - Avoid AI clichés completely: NO "delve into", "landscape", "revolutionize", "game-changer", "cutting-edge", "unlock", "leverage", "robust", "seamless", "in today's digital age"
   - Use power words that engage: "discover", "proven", "essential", "critical", "transform" (but sparingly)

3. REDUCE ADJECTIVES & ADVERBS:
   - Limit adjective use to 1 per sentence maximum
   - Cut adverbs by 80% - show don't tell (not "very important" but "critical to success")
   - Use strong nouns and verbs instead of weak ones with modifiers

4. CREATE READER HOOKS:
   - Start with a compelling question, statistic, or scenario
   - Use subheadings that promise value ("How to...", "Why X Matters", "The Truth About...")
   - Include surprising facts or counterintuitive insights
   - Add rhetorical questions to engage readers
   - Use "you" to make it personal

5. STRUCTURE & FLOW:
   - Follow the outline EXACTLY - every section, every point
   - Each paragraph = one clear idea (3-5 sentences max)
   - Use transitions to connect ideas naturally
   - Build logical progression (problem → solution, general → specific)

6. DATA & EVIDENCE:
   - Include specific statistics and facts from the research
   - Use concrete examples and case studies
   - Reference expert insights naturally (not "According to experts" but weave them in)
   - Cite numbers precisely (not "many companies" but "73% of Fortune 500 companies")

7. FORMATTING:
   - Use Markdown headings (## for main sections, ### for subsections)
   - Bold key terms sparingly (1-2 per section max)
   - Short paragraphs for readability
   - Use bullet points only when listing distinct items

8. TONE:
   - Professional but approachable
   - Confident without being arrogant
   - Helpful and educational
   - Authentic and trustworthy

WHAT TO AVOID:
❌ Overly complex sentences
❌ Passive constructions ("it is believed that" → "experts believe")
❌ Filler words (very, really, quite, just, actually)
❌ Redundancy (saying the same thing twice)
❌ Generic statements without evidence
❌ AI-sounding phrases
❌ Excessive use of "the fact that", "in order to", "it is important to note"

EXAMPLE OF GOOD VS BAD WRITING:

BAD (AI-like): "In today's rapidly evolving digital landscape, it is increasingly important for businesses to leverage cutting-edge technologies in order to stay competitive and unlock new opportunities for growth."

GOOD (Human expert): "Companies that ignore new technology fall behind. Simple as that. The question isn't whether to adopt AI tools - it's which ones work for your specific goals."

Now write the complete article following these rules. Make it sound like a knowledgeable human expert wrote it, not an AI. Hit exactly {state['target_length']} words.

Write in Markdown format starting with the title:
"""
    
    try:
        response = await llm.ainvoke(prompt)
        content = response.content.strip()
        
        # Ensure it starts with a heading
        if not content.startswith("#"):
            content = f"# {state['topic']}\n\n{content}"
        
        word_count = len(content.split())
        print(f"✅ Generated {word_count} words (target: {state['target_length']})")
        
        return {"final_content": content}
    except Exception as e:
        print(f"❌ Error in writer node: {e}")
        return {"final_content": f"# {state['topic']}\n\nError generating content.", "error": str(e)}

# --- Graph Assembly ---
workflow = StateGraph(AgentState)

workflow.add_node("search", search_node)
workflow.add_node("scrape", scraper_node)
workflow.add_node("analyze", analyzer_node)
workflow.add_node("write", writer_node)

workflow.set_entry_point("search")
workflow.add_edge("search", "scrape")
workflow.add_edge("scrape", "analyze")
workflow.add_edge("analyze", "write")
workflow.add_edge("write", END)

app = workflow.compile()

def handler(event, context):
    """Lambda handler function"""
    body = event if "article_id" in event else json.loads(event.get("body", "{}"))
    
    approved_title = body["query"]
    
    initial_state = {
        "article_id": body["article_id"],
        "raw_query": approved_title,
        "topic": approved_title,
        "category": body.get("category", "General"),
        "target_length": body.get("target_length", 1500),
        "source_count": body.get("source_count", 5),
        "urls": [], 
        "source_data": [], 
        "seo_brief": {}, 
        "final_content": "", 
        "error": None
    }
    
    print(f"🚀 STARTING ARTICLE GENERATION")
    
    try:
        result = asyncio.run(app.ainvoke(initial_state))
        
        if result.get("error"):
            raise Exception(result["error"])
        
        if not result.get("final_content"):
            raise Exception("No content was generated")
        
        print(f"✅ ARTICLE GENERATION COMPLETE")
        
        finalize_article_in_db(
            result['article_id'], 
            result['final_content'], 
            result['seo_brief']
        )
        
        return {
            "statusCode": 200, 
            "body": json.dumps({
                "message": "Success",
                "article_id": result['article_id'],
                "word_count": len(result['final_content'].split())
            })
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ FATAL ERROR: {error_msg}")
        
        # Update article status to failed in database
        try:
            from sqlalchemy import create_engine, text
            from config import Config
            engine = create_engine(Config.DB_URL)
            with engine.connect() as conn:
                conn.execute(text("""
                    UPDATE articles 
                    SET status = 'failed', 
                        error_message = :error_msg,
                        updated_at = NOW()
                    WHERE id = :id
                """), {"id": initial_state['article_id'], "error_msg": error_msg})
                conn.commit()
                print(f"✅ Article {initial_state['article_id']} marked as FAILED in database")
        except Exception as db_error:
            print(f"❌ Failed to update database: {db_error}")
        
        return {
            "statusCode": 500, 
            "body": json.dumps({
                "error": error_msg,
                "article_id": initial_state['article_id']
            })
        }