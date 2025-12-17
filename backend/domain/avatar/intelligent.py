"""
Intelligent Avatar Module
Handles avatar behavior powered by Graph RAG and LLM
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timezone
from openai import AsyncOpenAI, AsyncAzureOpenAI
from motor.motor_asyncio import AsyncIOMotorDatabase
from domain.graph.rag import GraphRAG
import uuid


class IntelligentAvatar:
    """Avatar with Graph RAG-powered intelligence"""
    
    def __init__(self, db: AsyncIOMotorDatabase, llm_client: Union[AsyncOpenAI, AsyncAzureOpenAI, None], 
                 model: str, graph_rag: GraphRAG):
        self.db = db
        self.llm_client = llm_client
        self.model = model  # Model name for OpenAI
        self.graph_rag = graph_rag
    
    async def generate_avatar_post(self, user_id: str, post_type: str = "general") -> Dict[str, Any]:
        """
        Generate an intelligent avatar post based on user's knowledge graph
        """
        if not self.llm_client:
            return {"error": "LLM not configured"}
        
        # Get user data
        user = await self.db.users.find_one({"id": user_id})
        if not user:
            return {"error": "User not found"}
        
        # Get graph context
        context = await self.graph_rag.get_relevant_context(user_id, "post_generation")
        avatar_profile = await self.graph_rag.get_avatar_personality_profile(user_id)
        
        # Generate post based on type
        if post_type == "interest":
            prompt = f"""{avatar_profile}

{context}

Generate a social media post (100-150 words) from the avatar's perspective sharing something about one of your interests. Be authentic, engaging, and true to your personality. Include a relevant question to encourage interaction.

Return ONLY the post text, no quotes or explanations."""
        
        elif post_type == "thought":
            prompt = f"""{avatar_profile}

{context}

Generate a thoughtful social media post (80-120 words) sharing an insight or reflection that aligns with your values and personality. Be genuine and relatable.

Return ONLY the post text, no quotes or explanations."""
        
        elif post_type == "experience":
            prompt = f"""{avatar_profile}

{context}

Generate a social media post (100-150 words) sharing a recent experience or activity related to your interests. Be descriptive and engaging.

Return ONLY the post text, no quotes or explanations."""
        
        else:  # general
            prompt = f"""{avatar_profile}

{context}

Generate an engaging social media post (80-150 words) from the avatar's perspective. Choose to share an interest, thought, or experience. Be authentic and true to your personality.

Return ONLY the post text, no quotes or explanations."""
        
        try:
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=250
            )
            
            post_content = response.choices[0].message.content.strip()
            
            # Remove quotes if present
            if post_content.startswith('"') and post_content.endswith('"'):
                post_content = post_content[1:-1]
            
            return {
                "content": post_content,
                "type": post_type,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {"error": f"Post generation failed: {str(e)}"}
    
    async def generate_chat_response(self, user_id: str, other_user_id: str, 
                                    conversation_history: List[Dict[str, str]],
                                    last_message: str) -> Dict[str, Any]:
        """
        Generate intelligent avatar chat response using Graph RAG
        """
        if not self.llm_client:
            return {"error": "LLM not configured"}
        
        # Get user data
        user = await self.db.users.find_one({"id": user_id})
        if not user:
            return {"error": "User not found"}
        
        # Get graph context
        avatar_profile = await self.graph_rag.get_avatar_personality_profile(user_id)
        conversation_context = await self.graph_rag.get_conversation_context(user_id, other_user_id)
        
        # Build conversation history for context
        history_text = ""
        for msg in conversation_history[-5:]:  # Last 5 messages
            sender = "You" if msg.get("sender_id") == user_id else "Them"
            history_text += f"{sender}: {msg.get('content', '')}\n"
        
        prompt = f"""{avatar_profile}

{conversation_context}

Recent conversation:
{history_text}
Them: {last_message}

Generate a natural, engaging response (30-80 words) that:
1. Reflects your personality and interests
2. Builds on shared interests when relevant
3. Asks thoughtful questions to continue the conversation
4. Is warm, authentic, and shows genuine interest

Return ONLY the response text, no labels or quotes."""
        
        try:
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=150
            )
            
            response_content = response.choices[0].message.content.strip()
            
            # Remove "You:" prefix if present
            if response_content.startswith("You:"):
                response_content = response_content[4:].strip()
            
            return {
                "content": response_content,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {"error": f"Response generation failed: {str(e)}"}
    
    async def generate_avatar_profile_bio(self, user_id: str) -> Dict[str, Any]:
        """
        Generate avatar bio based on graph data
        """
        if not self.llm_client:
            return {"error": "LLM not configured"}
        
        # Get graph context
        context = await self.graph_rag.get_user_context(user_id, max_nodes=15)
        
        interests = [item["label"] for item in context.get("interests", [])[:8]]
        traits = [item["label"] for item in context.get("traits", [])[:4]]
        values = [item["label"] for item in context.get("values", [])[:3]]
        
        prompt = f"""Generate an avatar bio (80-120 words) for a dating profile based on these characteristics:

Interests: {', '.join(interests) if interests else 'exploring new things'}
Personality: {', '.join(traits) if traits else 'friendly, open-minded'}
Values: {', '.join(values) if values else 'authenticity, connection'}

The bio should be:
- Written in first person
- Engaging and authentic
- Show personality and uniqueness
- Mention key interests naturally
- End with a conversation starter

Return ONLY the bio text, no quotes."""
        
        try:
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=200
            )
            
            bio = response.choices[0].message.content.strip()
            
            if bio.startswith('"') and bio.endswith('"'):
                bio = bio[1:-1]
            
            return {
                "bio": bio,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {"error": f"Bio generation failed: {str(e)}"}
    
    async def suggest_conversation_starters(self, user_id: str, other_user_id: str, 
                                           count: int = 3) -> List[str]:
        """
        Generate conversation starter suggestions based on shared interests
        """
        if not self.llm_client:
            return ["Hey! How's your day going?"]
        
        # Get compatibility info
        compatibility = await self.graph_rag.calculate_compatibility(user_id, other_user_id)
        shared = compatibility.get("shared_interests", [])
        
        if not shared:
            return [
                "Hey! What are you most passionate about these days?",
                "Hi! I'd love to know more about your interests.",
                "Hello! What's something that always makes you smile?"
            ]
        
        prompt = f"""Generate {count} natural conversation starters based on these shared interests: {', '.join(shared[:5])}

Each starter should:
- Be casual and friendly
- Reference a shared interest naturally
- Be open-ended to encourage conversation
- Be 10-20 words

Return ONLY the conversation starters, one per line, no numbering or quotes."""
        
        try:
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=150
            )
            
            starters = response.choices[0].message.content.strip().split('\n')
            starters = [s.strip() for s in starters if s.strip()][:count]
            
            return starters if starters else ["Hey! What are you up to?"]
            
        except Exception:
            return ["Hey! How's it going?"]
    
    async def generate_match_explanation(self, user_id: str, match_user_id: str) -> str:
        """
        Generate explanation for why two users are a good match
        """
        compatibility = await self.graph_rag.calculate_compatibility(user_id, match_user_id)
        
        shared_interests = compatibility.get("shared_interests", [])
        shared_values = compatibility.get("shared_values", [])
        score = compatibility.get("compatibility_score", 0)
        
        if score < 30:
            explanation = "You both have unique perspectives that could lead to interesting conversations. "
        elif score < 60:
            explanation = f"You share some common ground: {', '.join(shared_interests[:3])}. "
        else:
            explanation = f"Great match! You both enjoy {', '.join(shared_interests[:3])}. "
        
        if shared_values:
            explanation += f"You also value {', '.join(shared_values[:2])}."
        
        return explanation
