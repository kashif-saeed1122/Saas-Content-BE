"""
Title Generation Agent
Converts user descriptions into multiple distinct article title ideas
"""
import os
from typing import List
from langchain_openai import ChatOpenAI
import json

# Use GPT-4 for high-quality title generation
llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.8, api_key=os.getenv("OPENAI_API_KEY"))

async def generate_titles(description: str, count: int = 1) -> List[str]:
    """
    Generate multiple distinct article titles from a description.
    
    Args:
        description: The user's topic description
        count: Number of titles to generate (1-5)
    
    Returns:
        List of title strings
    """
    
    prompt = f"""You are an expert content strategist and SEO specialist.

Given this topic description: "{description}"

Generate {count} UNIQUE and DISTINCT article title ideas. Each title should:
1. Approach the topic from a DIFFERENT angle or perspective
2. Be compelling, SEO-friendly, and click-worthy
3. Be 50-80 characters long
4. Include power words when appropriate
5. Be specific and actionable

CRITICAL: Each title must be SIGNIFICANTLY different from the others. Don't just rephrase - explore different aspects, audiences, or approaches to the topic.

Return ONLY a JSON array of title strings, nothing else:
["Title 1", "Title 2", "Title 3"]
"""
    
    try:
        response = await llm.ainvoke(prompt)
        content = response.content.strip()
        
        # Clean up markdown code blocks if present
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()
        
        titles = json.loads(content)
        
        # Ensure we got the right number
        if len(titles) != count:
            titles = titles[:count]  # Trim if too many
            
        return titles
        
    except Exception as e:
        print(f"Error generating titles: {e}")
        # Fallback to basic titles
        return [f"{description} - Angle {i+1}" for i in range(count)]
