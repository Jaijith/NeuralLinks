"""
Analysis MCP Tools
Tools for analyzing conversations and creating leads
"""

import logging
import json
import uuid
from typing import Dict, List, Any
from datetime import datetime, timezone
from .tools import WorkflowBaseTool

logger = logging.getLogger(__name__)


class AnalyzeConversationTool(WorkflowBaseTool):
    """Analyze a conversation for quality and engagement signals"""
    
    name = "analyze_conversation"
    description = "Analyze a conversation to assess quality and extract insights"
    
    schema = {
        "type": "object",
        "properties": {
            "conversation_id": {
                "type": "string",
                "description": "Conversation to analyze"
            }
        },
        "required": ["conversation_id"]
    }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        conversation_id = kwargs.get("conversation_id")
        
        conversation = await self.db.agent_conversations.find_one({"id": conversation_id})
        
        if not conversation:
            return {"success": False, "error": "Conversation not found"}
        
        messages = conversation.get("messages", [])
        
        # Basic metrics
        total_messages = len(messages)
        avatar_messages = len([m for m in messages if m.get("sender") == avatar_id])
        other_messages = total_messages - avatar_messages
        
        # Calculate response rate
        response_rate = other_messages / avatar_messages if avatar_messages > 0 else 0
        
        # Default analysis
        analysis = {
            "engagement_level": "low" if response_rate < 0.5 else "medium" if response_rate < 1.0 else "high",
            "sentiment": "neutral",
            "key_topics": [],
            "engagement_signals": [],
            "summary": f"Conversation with {total_messages} messages"
        }
        
        # Use LLM for deeper analysis if available
        if messages and self.openai_client and len(messages) >= 2:
            conversation_text = "\n".join([
                f"{m.get('sender', 'unknown')[:8]}: {m.get('content', '')}"
                for m in messages[-10:]  # Last 10 messages
            ])
            
            prompt = f"""Analyze this conversation and return JSON with these fields:
- engagement_level: "low", "medium", or "high"
- sentiment: "negative", "neutral", or "positive"
- key_topics: array of main discussion topics
- engagement_signals: array of positive signals (e.g., "asked follow-up questions", "shared personal info")
- summary: brief 1-2 sentence summary

Conversation:
{conversation_text}

Return only valid JSON."""

            try:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    max_tokens=300
                )
                analysis = json.loads(response.choices[0].message.content)
            except Exception as e:
                logger.error(f"LLM analysis failed: {e}")
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "metrics": {
                "total_messages": total_messages,
                "avatar_messages": avatar_messages,
                "other_messages": other_messages,
                "response_rate": round(response_rate, 2)
            },
            "analysis": analysis
        }


class CreateLeadTool(WorkflowBaseTool):
    """Create a lead from a qualified match"""
    
    name = "create_lead"
    description = "Create a lead entry from a qualified match"
    
    schema = {
        "type": "object",
        "properties": {
            "mission_id": {
                "type": "string",
                "description": "Mission this lead belongs to"
            },
            "target_user_id": {
                "type": "string",
                "description": "The matched user"
            },
            "score": {
                "type": "integer",
                "description": "Match score (0-100)"
            },
            "score_breakdown": {
                "type": "object",
                "description": "Score breakdown by factor"
            },
            "conversation_id": {
                "type": "string",
                "description": "Associated conversation ID"
            },
            "insights": {
                "type": "object",
                "description": "Match insights and details"
            }
        },
        "required": ["mission_id", "target_user_id", "score"]
    }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        mission_id = kwargs.get("mission_id")
        target_id = kwargs.get("target_user_id")
        score = kwargs.get("score")
        score_breakdown = kwargs.get("score_breakdown", {})
        conversation_id = kwargs.get("conversation_id")
        insights = kwargs.get("insights", {})
        
        logger.info(f"📝 Creating lead: mission={mission_id[:8]}, target={target_id[:8]}, score={score}")
        
        # Get target user info
        target_user = await self.db.users.find_one({"id": target_id})
        
        if not target_user:
            return {"success": False, "error": "Target user not found"}
        
        # Get conversation summary if exists
        conversation_summary = {}
        if conversation_id:
            conv = await self.db.agent_conversations.find_one({"id": conversation_id})
            if conv:
                messages = conv.get("messages", [])
                conversation_summary = {
                    "message_count": len(messages),
                    "last_message_at": messages[-1].get("timestamp") if messages else None,
                    "sentiment": "neutral"
                }
        
        # Get shared interests
        avatar_interests = set(await self._get_interests(avatar_id))
        target_interests = set(await self._get_interests(target_id))
        shared_interests = list(avatar_interests & target_interests)
        
        # Determine priority
        priority = "high" if score >= 85 else "medium" if score >= 70 else "low"
        
        # Create lead
        now = datetime.now(timezone.utc)
        lead_id = str(uuid.uuid4())
        lead = {
            "id": lead_id,
            "mission_id": mission_id,
            "user_id": avatar_id,
            "target_user_id": target_id,
            "target_avatar_name": target_user.get("avatar_name", "Unknown"),
            "target_real_name": target_user.get("name"),
            "target_picture": target_user.get("avatar_picture", target_user.get("picture")),
            "target_archetype": target_user.get("avatar_archetype"),
            "score": score,
            "score_breakdown": score_breakdown,
            "match_details": {
                "shared_interests": shared_interests[:10],
                "connection_points": insights.get("connection_points", []),
                "compatibility_reasons": insights.get("compatibility_reasons", [])
            },
            "conversation": {
                "conversation_id": conversation_id,
                **conversation_summary
            },
            "status": "new",
            "priority": priority,
            "insights": insights.get("insights", []),
            "suggested_actions": [
                f"Start a conversation about {shared_interests[0]}" if shared_interests else "Send a friendly introduction",
                "Check their recent posts for talking points"
            ],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        await self.db.mission_leads.insert_one(lead)
        
        # Log activity
        await self._log_activity(avatar_id, "create_lead", {
            "lead_id": lead_id,
            "mission_id": mission_id,
            "target_id": target_id,
            "score": score
        })
        
        return {
            "success": True,
            "lead_id": lead_id,
            "lead": lead
        }


class GenerateSummaryTool(WorkflowBaseTool):
    """Generate a summary of mission results"""
    
    name = "generate_summary"
    description = "Generate a summary of mission execution and results"
    
    schema = {
        "type": "object",
        "properties": {
            "mission_id": {
                "type": "string",
                "description": "Mission to summarize"
            }
        },
        "required": ["mission_id"]
    }
    
    async def _execute_action(self, avatar_id: str, **kwargs) -> Dict[str, Any]:
        mission_id = kwargs.get("mission_id")
        
        # Get mission
        mission = await self.db.missions.find_one({"id": mission_id})
        if not mission:
            return {"success": False, "error": "Mission not found"}
        
        # Get leads
        leads = await self.db.mission_leads.find({"mission_id": mission_id}).to_list(100)
        
        # Calculate stats
        total_leads = len(leads)
        avg_score = sum(l.get("score", 0) for l in leads) / total_leads if total_leads > 0 else 0
        
        # Get top interests
        all_interests = []
        for lead in leads:
            all_interests.extend(lead.get("match_details", {}).get("shared_interests", []))
        interest_counts = {}
        for i in all_interests:
            interest_counts[i] = interest_counts.get(i, 0) + 1
        top_interests = sorted(interest_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Count by priority
        high_priority = len([l for l in leads if l.get("priority") == "high"])
        medium_priority = len([l for l in leads if l.get("priority") == "medium"])
        
        summary = {
            "total_leads": total_leads,
            "avg_match_score": round(avg_score, 1),
            "top_interest_matches": [i[0] for i in top_interests],
            "high_priority_leads": high_priority,
            "medium_priority_leads": medium_priority,
            "insights": [
                f"Found {total_leads} potential matches",
                f"Average compatibility score: {round(avg_score)}%",
                f"{high_priority} high-priority leads ready for follow-up"
            ]
        }
        
        if top_interests:
            summary["insights"].append(f"Top shared interest: {top_interests[0][0]}")
        
        # Update mission with summary
        now = datetime.now(timezone.utc)
        await self.db.missions.update_one(
            {"id": mission_id},
            {
                "$set": {
                    "results_summary": summary,
                    "updated_at": now.isoformat()
                }
            }
        )
        
        return {
            "success": True,
            "mission_id": mission_id,
            "summary": summary
        }

