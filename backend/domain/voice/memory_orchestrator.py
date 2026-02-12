"""
Memory Orchestrator - Agentic CRUD Operations for Voice Memory

Multi-agent pipeline:
1. EXTRACTION AGENT - Extracts raw information from conversation
2. REASONING AGENT - Analyzes intent, determines action type (CREATE/UPDATE/DELETE)
3. VALIDATION AGENT - Validates planned actions, checks for conflicts
4. EXECUTOR - Executes validated CRUD operations

This approach ensures accuracy and reduces errors from single-pass extraction.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from enum import Enum
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class ActionType(Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    NO_ACTION = "no_action"


class EntityType(Enum):
    CONNECTION = "connection"
    INTEREST = "interest"
    FACT = "fact"


@dataclass
class MemoryAction:
    """Represents a validated action to be executed"""
    action_type: ActionType
    entity_type: EntityType
    entity_data: Dict[str, Any]
    confidence: float
    reasoning: str
    validated: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type.value,
            "entity_type": self.entity_type.value,
            "entity_data": self.entity_data,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "validated": self.validated
        }


@dataclass
class OrchestrationResult:
    """Result of the orchestration pipeline"""
    success: bool
    actions_planned: List[MemoryAction] = field(default_factory=list)
    actions_executed: List[MemoryAction] = field(default_factory=list)
    actions_rejected: List[Tuple[MemoryAction, str]] = field(default_factory=list)
    extraction_raw: Dict[str, Any] = field(default_factory=dict)
    reasoning_output: str = ""
    validation_output: str = ""
    errors: List[str] = field(default_factory=list)


class MemoryOrchestrator:
    """
    Orchestrates memory CRUD operations using multi-agent pipeline.
    
    Pipeline:
    1. Extract → 2. Reason → 3. Validate → 4. Execute
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, openai_client: Any):
        self.db = db
        self.openai = openai_client
        self.min_confidence = 0.7  # Minimum confidence to execute action
    
    async def process_conversation(
        self, 
        user_id: str, 
        avatar_id: str,
        conversation: str,
        session_id: str = "",
        s3_key: str = "",
        duration_seconds: int = 0,
    ) -> OrchestrationResult:
        """
        Main entry point - processes conversation through the full pipeline.
        
        Enhanced pipeline:
        1. Extract → 2. Reason → 3. Validate → 4. Execute
        5. Personality Extraction (parallel)
        6. Conversation Indexing (parallel)
        7. Knowledge Gap Update (parallel)
        
        Args:
            user_id: User's ID
            avatar_id: Avatar's ID
            conversation: The conversation text to process
            session_id: Voice session ID (for conversation index)
            s3_key: S3 key for the full transcript
            duration_seconds: Duration of the conversation
            
        Returns:
            OrchestrationResult with all planned and executed actions
        """
        result = OrchestrationResult(success=False)
        
        try:
            # Step 1: EXTRACTION
            logger.info("🔍 Step 1: Extraction Agent running...")
            extraction = await self._extraction_agent(conversation)
            result.extraction_raw = extraction
            
            if not extraction:
                result.errors.append("Extraction returned empty")
                return result
            
            # Step 2: REASONING
            logger.info("🧠 Step 2: Reasoning Agent running...")
            actions, reasoning = await self._reasoning_agent(conversation, extraction, user_id)
            result.actions_planned = actions
            result.reasoning_output = reasoning
            
            if not actions:
                logger.info("No actions identified")
                result.success = True
                # Even with no CRUD actions, still run personality extraction + indexing
                await self._run_post_pipeline(
                    user_id, avatar_id, conversation,
                    session_id, s3_key, duration_seconds, extraction
                )
                return result
            
            # Step 3: VALIDATION
            logger.info("✅ Step 3: Validation Agent running...")
            validated_actions, rejected, validation_output = await self._validation_agent(
                actions, user_id
            )
            result.validation_output = validation_output
            result.actions_rejected = rejected
            
            # Step 4: EXECUTION
            logger.info("⚡ Step 4: Executor running...")
            executed = await self._execute_actions(validated_actions, user_id, avatar_id)
            result.actions_executed = executed
            
            # Step 5-7: POST-PIPELINE (personality extraction + indexing + knowledge gaps)
            logger.info("🧬 Step 5-7: Post-pipeline (personality + index + gaps)...")
            await self._run_post_pipeline(
                user_id, avatar_id, conversation,
                session_id, s3_key, duration_seconds, extraction
            )
            
            result.success = True
            logger.info(f"✅ Orchestration complete: {len(executed)} actions executed")
            
        except Exception as e:
            logger.error(f"Orchestration error: {e}")
            result.errors.append(str(e))
        
        return result
    
    async def _run_post_pipeline(
        self,
        user_id: str,
        avatar_id: str,
        conversation: str,
        session_id: str,
        s3_key: str,
        duration_seconds: int,
        extraction: Dict[str, Any],
    ):
        """
        Post-pipeline: personality extraction, conversation indexing, knowledge gap update,
        and post insight thread status update.
        Runs in parallel for speed. Failures here don't block the main pipeline.
        """
        import asyncio
        tasks = []
        
        # 5. Personality Extraction Agent
        tasks.append(self._personality_extraction_agent(user_id, conversation, extraction))
        
        # 6. Conversation Indexing
        if session_id:
            tasks.append(self._index_conversation(
                user_id, avatar_id, session_id, s3_key,
                conversation, extraction, duration_seconds
            ))
        
        # 7. Knowledge Gap Update
        tasks.append(self._update_knowledge_gaps(user_id, conversation))
        
        # 8. Post Insight Thread Status Update
        if session_id:
            tasks.append(self._update_post_insight_threads(user_id, session_id, conversation))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                logger.warning(f"Post-pipeline task {i} failed: {r}")
    
    # =========================================================================
    # AGENT 5: PERSONALITY EXTRACTION
    # =========================================================================
    
    async def _personality_extraction_agent(
        self, user_id: str, conversation: str, extraction: Dict[str, Any]
    ):
        """
        Extract personality signals from the conversation:
        - Communication style patterns
        - Emotional tendencies
        - Values revealed through conversation
        - Decision-making patterns
        
        Stores in graph_nodes as 'trait' and 'value' types.
        """
        try:
            prompt = """You are a PERSONALITY EXTRACTION agent. Analyze this conversation to extract personality signals about the USER (not the AI).

Focus on:
1. TRAITS: How do they communicate? Are they direct/indirect? Confident/uncertain? Analytical/intuitive? Warm/reserved?
2. VALUES: What do they seem to care about? What priorities emerge?
3. EMOTIONAL PATTERNS: How do they express emotions? What makes them animated?
4. COMMUNICATION STYLE: Sentence length, vocabulary level, use of humor, storytelling tendency

IMPORTANT: Only extract what is CLEARLY demonstrated in the conversation. Don't infer from nothing.

Conversation:
---
{conversation}
---

Already extracted entities for context:
{extraction}

Return JSON:
{{
  "traits": [
    {{"label": "trait name", "evidence": "brief quote/observation", "confidence": 0.0-1.0}}
  ],
  "values": [
    {{"label": "value name", "evidence": "brief observation", "confidence": 0.0-1.0}}
  ],
  "emotional_signals": [
    {{"trigger": "what caused the emotion", "emotion": "joy|excitement|concern|frustration|etc", "intensity": 0.0-1.0}}
  ],
  "style_notes": {{
    "formality": "casual|mixed|formal",
    "humor_frequency": "none|occasional|frequent",
    "storytelling": true/false,
    "vocabulary_level": "simple|moderate|sophisticated"
  }}
}}"""
            
            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Extract personality signals precisely."},
                    {"role": "user", "content": prompt.format(
                        conversation=conversation,
                        extraction=json.dumps(extraction, indent=2)[:2000]
                    )}
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            result = json.loads(response.choices[0].message.content)
            now = datetime.now(timezone.utc)
            
            # Store traits in graph_nodes
            for trait in result.get("traits", []):
                if trait.get("confidence", 0) < 0.6:
                    continue
                label = trait.get("label", "").lower().strip()
                if not label:
                    continue
                
                existing = await self.db.graph_nodes.find_one({
                    "user_id": user_id, "node_type": "trait", "label": label
                })
                if existing:
                    await self.db.graph_nodes.update_one(
                        {"_id": existing["_id"]},
                        {"$inc": {"mention_count": 1}, "$set": {"updated_at": now}}
                    )
                else:
                    await self.db.graph_nodes.insert_one({
                        "id": f"trait_{user_id}_{label.replace(' ', '_')}",
                        "user_id": user_id,
                        "node_type": "trait",
                        "label": label,
                        "display_label": label.title(),
                        "strength": trait.get("confidence", 0.7),
                        "properties": {"evidence": trait.get("evidence", ""), "source": "conversation"},
                        "mention_count": 1,
                        "created_at": now,
                        "updated_at": now,
                    })
            
            # Store values
            for value in result.get("values", []):
                if value.get("confidence", 0) < 0.6:
                    continue
                label = value.get("label", "").lower().strip()
                if not label:
                    continue
                
                existing = await self.db.graph_nodes.find_one({
                    "user_id": user_id, "node_type": "value", "label": label
                })
                if existing:
                    await self.db.graph_nodes.update_one(
                        {"_id": existing["_id"]},
                        {"$inc": {"mention_count": 1}, "$set": {"updated_at": now}}
                    )
                else:
                    await self.db.graph_nodes.insert_one({
                        "id": f"value_{user_id}_{label.replace(' ', '_')}",
                        "user_id": user_id,
                        "node_type": "value",
                        "label": label,
                        "display_label": label.title(),
                        "strength": value.get("confidence", 0.7),
                        "properties": {"evidence": value.get("evidence", ""), "source": "conversation"},
                        "mention_count": 1,
                        "created_at": now,
                        "updated_at": now,
                    })
            
            logger.info(f"Personality extraction: {len(result.get('traits', []))} traits, {len(result.get('values', []))} values for {user_id}")
            
        except Exception as e:
            logger.error(f"Personality extraction error: {e}")
    
    # =========================================================================
    # STEP 6: CONVERSATION INDEXING
    # =========================================================================
    
    async def _index_conversation(
        self,
        user_id: str,
        avatar_id: str,
        session_id: str,
        s3_key: str,
        conversation: str,
        extraction: Dict[str, Any],
        duration_seconds: int,
    ):
        """Index this conversation for future recall searches."""
        try:
            # Build summary from extraction data
            topics = []
            people = []
            for interest in extraction.get("interests", []):
                t = interest.get("topic", "")
                if t:
                    topics.append(t)
            for person in extraction.get("people", []):
                n = person.get("name", "")
                if n:
                    people.append(n)
            
            # Generate a concise summary
            summary_prompt = f"""Summarize this conversation in 1-2 sentences (what was discussed, key points):
---
{conversation[:3000]}
---

Also extract 2-3 notable quotes from the USER (not the AI).

Return JSON:
{{"summary": "...", "key_quotes": ["...", "..."], "emotional_tone": "happy|sad|neutral|excited|contemplative|anxious"}}"""
            
            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Summarize conversations concisely."},
                    {"role": "user", "content": summary_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            summary_data = json.loads(response.choices[0].message.content)
            
            from domain.voice.conversation_recall import ConversationRecallService
            recall_service = ConversationRecallService(self.db)
            
            await recall_service.index_conversation(
                user_id=user_id,
                avatar_id=avatar_id,
                session_id=session_id,
                s3_key=s3_key,
                summary=summary_data.get("summary", ""),
                topics=topics,
                people_mentioned=people,
                emotional_tone=summary_data.get("emotional_tone", "neutral"),
                key_quotes=summary_data.get("key_quotes", []),
                duration_seconds=duration_seconds,
            )
            
        except Exception as e:
            logger.error(f"Conversation indexing error: {e}")
    
    # =========================================================================
    # STEP 7: KNOWLEDGE GAP UPDATE
    # =========================================================================
    
    async def _update_knowledge_gaps(self, user_id: str, conversation: str):
        """Update knowledge gap coverage based on what was revealed in conversation."""
        try:
            from domain.avatar.personality.knowledge_gaps import KnowledgeGapTracker
            tracker = KnowledgeGapTracker(self.db)
            
            # Increment conversation count
            await tracker.increment_conversation_count(user_id)
            
            # Determine which categories this conversation touched
            category_keywords = {
                "life_narrative": ["grew up", "childhood", "story", "career", "history", "started"],
                "values_beliefs": ["believe", "important", "value", "passionate", "feel strongly"],
                "communication_style": ["disagree", "argue", "conflict", "express"],
                "social_patterns": ["friends", "family", "people", "inner circle", "social"],
                "interests_passions": ["love", "hobby", "passionate", "obsessed", "into"],
                "emotional_patterns": ["happy", "frustrated", "upset", "excited", "anxious"],
                "daily_life": ["morning", "routine", "typical day", "everyday", "wake up"],
                "humor_personality": ["funny", "joke", "laugh", "humor", "silly"],
            }
            
            conv_lower = conversation.lower()
            for category, keywords in category_keywords.items():
                if any(kw in conv_lower for kw in keywords):
                    await tracker.update_coverage(user_id, category, delta=0.05)
                    
        except Exception as e:
            logger.error(f"Knowledge gap update error: {e}")
    
    # =========================================================================
    # STEP 8: POST INSIGHT THREAD STATUS UPDATE
    # =========================================================================
    
    async def _update_post_insight_threads(self, user_id: str, session_id: str, conversation: str):
        """
        After a voice conversation, check if any 'raised' post insight threads
        were discussed or deflected. Update their status accordingly.
        
        This ensures:
        - Discussed threads get a user response summary stored
        - Deflected threads are never raised proactively again
        - Both retain knowledge for reactive engagement
        """
        try:
            from domain.avatar.personality.post_insights import PostInsightAnalyzer
            analyzer = PostInsightAnalyzer(self.db, self.openai)
            await analyzer.update_thread_statuses(
                user_id=user_id,
                session_id=session_id,
                conversation_text=conversation,
                openai_client=self.openai,
            )
            logger.info(f"Post insight thread statuses updated for {user_id}, session {session_id}")
        except Exception as e:
            logger.error(f"Post insight thread update error: {e}")
    
    # =========================================================================
    # AGENT 1: EXTRACTION
    # =========================================================================
    
    async def _extraction_agent(self, conversation: str) -> Dict[str, Any]:
        """
        Extraction Agent - Extracts raw entities from conversation.
        
        This agent focuses ONLY on extraction, not interpretation.
        """
        prompt = """You are an EXTRACTION agent. Your ONLY job is to extract entities mentioned in the conversation.

DO NOT interpret or infer. Extract ONLY what is EXPLICITLY stated.

Extract these entity types:
1. PEOPLE - Anyone mentioned (name, relationship to user, any details)
2. INTERESTS - Topics, hobbies, activities the user expresses interest in
3. FACTS - Factual information about the user (job, location, etc.)
4. STATEMENTS - Any statements that might indicate corrections or changes

For each entity, note:
- The exact quote from the conversation
- Whether it seems like new information, a correction, or a removal
- Any uncertainty

Conversation:
---
{conversation}
---

Return JSON:
{{
  "people": [
    {{"name": "...", "relationship": "...", "quote": "exact quote", "seems_like": "new|correction|removal", "details": "..."}}
  ],
  "interests": [
    {{"topic": "...", "quote": "exact quote", "seems_like": "new|correction|removal", "sentiment": "positive|negative"}}
  ],
  "facts": [
    {{"fact": "...", "quote": "exact quote", "seems_like": "new|correction|removal"}}
  ],
  "correction_signals": [
    {{"quote": "...", "type": "name_correction|relationship_correction|interest_removal|fact_update"}}
  ]
}}"""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an extraction agent. Extract entities precisely."},
                    {"role": "user", "content": prompt.format(conversation=conversation)}
                ],
                response_format={"type": "json_object"},
                temperature=0.1  # Low temperature for precise extraction
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Extraction agent error: {e}")
            return {}
    
    # =========================================================================
    # AGENT 2: REASONING
    # =========================================================================
    
    async def _reasoning_agent(
        self, 
        conversation: str,
        extraction: Dict[str, Any],
        user_id: str
    ) -> Tuple[List[MemoryAction], str]:
        """
        Reasoning Agent - Analyzes extraction and determines actions.
        
        This agent reasons about:
        - Is this new information or an update?
        - Is the user correcting something?
        - Is the user removing something?
        - What's the confidence level?
        """
        # Get existing user data for context
        existing_data = await self._get_existing_data(user_id)
        
        prompt = """You are a REASONING agent. Analyze the extraction and determine what ACTIONS to take.

Your job is to:
1. Compare extracted entities with existing user data
2. Determine if each entity is CREATE, UPDATE, or DELETE
3. Identify corrections (user fixing previous mistakes)
4. Assign confidence scores (0.0-1.0)
5. Provide clear reasoning for each action

EXISTING USER DATA:
{existing_data}

EXTRACTED ENTITIES:
{extraction}

ORIGINAL CONVERSATION:
{conversation}

For each entity, determine:
- entity_type: MUST be one of: "connection" (for people), "interest" (for hobbies/topics), "fact" (for info about user)
- action: "create" (new), "update" (modify existing), "delete" (remove), "no_action"
- confidence: 0.0-1.0 (how certain are you?)
- reasoning: Why this action?

IMPORTANT RULES:
- entity_type must EXACTLY match: "connection", "interest", or "fact" (NOT "people"!)
- CREATE: Only for genuinely new information that is CLEARLY stated
- UPDATE: When user explicitly corrects something ("not X, it's Y", "actually...")
- DELETE: When user explicitly removes something ("I don't have", "not my", "no longer")
- Confidence < 0.7 means uncertain - be conservative
- If user is UNSURE or UNCERTAIN (uses words like "maybe", "might", "I think", "can't remember"), set confidence LOW (0.3-0.5)

Return JSON:
{{
  "actions": [
    {{
      "entity_type": "connection|interest|fact",
      "action": "create|update|delete|no_action",
      "data": {{}},
      "confidence": 0.9,
      "reasoning": "..."
    }}
  ],
  "overall_reasoning": "Summary of analysis..."
}}"""

        try:
            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a reasoning agent. Analyze carefully and be conservative with changes."},
                    {"role": "user", "content": prompt.format(
                        existing_data=json.dumps(existing_data, indent=2),
                        extraction=json.dumps(extraction, indent=2),
                        conversation=conversation
                    )}
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Convert to MemoryAction objects
            actions = []
            for a in result.get("actions", []):
                if a.get("action") == "no_action":
                    continue
                
                # Map 'people' to 'connection' (common LLM output)
                entity_type_str = a.get("entity_type", "fact")
                if entity_type_str == "people" or entity_type_str == "person":
                    entity_type_str = "connection"
                
                try:
                    entity_type = EntityType(entity_type_str)
                except ValueError:
                    logger.warning(f"Unknown entity type: {entity_type_str}, defaulting to fact")
                    entity_type = EntityType.FACT
                    
                action = MemoryAction(
                    action_type=ActionType(a.get("action", "no_action")),
                    entity_type=entity_type,
                    entity_data=a.get("data", {}),
                    confidence=a.get("confidence", 0.5),
                    reasoning=a.get("reasoning", "")
                )
                actions.append(action)
            
            return actions, result.get("overall_reasoning", "")
            
        except Exception as e:
            logger.error(f"Reasoning agent error: {e}")
            return [], str(e)
    
    async def _get_existing_data(self, user_id: str) -> Dict[str, Any]:
        """Get existing user data for reasoning context"""
        try:
            # Get user connections
            user = await self.db.users.find_one(
                {"id": user_id},
                {"connections": 1, "name": 1}
            )
            connections = user.get("connections", []) if user else []
            
            # Get interests from graph_nodes
            interests = await self.db.graph_nodes.find({
                "user_id": user_id,
                "node_type": "interest"
            }).to_list(50)
            
            # Get facts/preferences from graph_nodes
            facts = await self.db.graph_nodes.find({
                "user_id": user_id,
                "node_type": "preference"
            }).to_list(50)
            
            return {
                "connections": [
                    {"name": c.get("name"), "relationship": c.get("relationship")}
                    for c in connections[:10]
                ],
                "interests": [i.get("label") for i in interests[:10]],
                "facts": [f.get("full_text") or f.get("label") for f in facts[:10]]
            }
        except Exception as e:
            logger.error(f"Error getting existing data: {e}")
            return {"connections": [], "interests": [], "facts": []}
    
    # =========================================================================
    # AGENT 3: VALIDATION
    # =========================================================================
    
    async def _validation_agent(
        self,
        actions: List[MemoryAction],
        user_id: str
    ) -> Tuple[List[MemoryAction], List[Tuple[MemoryAction, str]], str]:
        """
        Validation Agent - Validates actions before execution.
        
        Checks:
        - Confidence threshold
        - Logical consistency
        - No dangerous deletions
        - Data integrity
        """
        validated = []
        rejected = []
        validation_notes = []
        
        for action in actions:
            # Check 1: Confidence threshold
            if action.confidence < self.min_confidence:
                rejected.append((action, f"Confidence {action.confidence:.2f} below threshold {self.min_confidence}"))
                validation_notes.append(f"❌ Rejected {action.entity_type.value} {action.action_type.value}: Low confidence")
                continue
            
            # Check 2: Required data present
            if not self._validate_required_data(action):
                rejected.append((action, "Missing required data"))
                validation_notes.append(f"❌ Rejected {action.entity_type.value}: Missing required fields")
                continue
            
            # Check 3: Dangerous deletion protection (only delete if very confident)
            if action.action_type == ActionType.DELETE and action.confidence < 0.85:
                rejected.append((action, f"DELETE requires confidence >= 0.85, got {action.confidence:.2f}"))
                validation_notes.append(f"⚠️ Rejected DELETE {action.entity_type.value}: Confidence too low for deletion")
                continue
            
            # Check 4: Update target exists (for updates)
            if action.action_type == ActionType.UPDATE:
                exists = await self._check_entity_exists(user_id, action)
                if not exists:
                    # Convert to CREATE instead
                    action.action_type = ActionType.CREATE
                    validation_notes.append(f"⚠️ Converted UPDATE to CREATE: Target not found")
            
            # Passed all checks
            action.validated = True
            validated.append(action)
            validation_notes.append(f"✅ Validated {action.action_type.value} {action.entity_type.value}")
        
        validation_output = "\n".join(validation_notes)
        return validated, rejected, validation_output
    
    def _validate_required_data(self, action: MemoryAction) -> bool:
        """Check if action has required data fields"""
        data = action.entity_data
        
        if action.entity_type == EntityType.CONNECTION:
            return bool(data.get("name"))
        elif action.entity_type == EntityType.INTEREST:
            return bool(data.get("topic"))
        elif action.entity_type == EntityType.FACT:
            return bool(data.get("fact"))
        
        return True
    
    async def _check_entity_exists(self, user_id: str, action: MemoryAction) -> bool:
        """Check if entity exists for updates"""
        try:
            if action.entity_type == EntityType.CONNECTION:
                name = action.entity_data.get("name", "")
                user = await self.db.users.find_one(
                    {"id": user_id, "connections.name": {"$regex": f"^{name}$", "$options": "i"}}
                )
                return user is not None
            
            elif action.entity_type == EntityType.INTEREST:
                topic = action.entity_data.get("topic", "").lower()
                node = await self.db.graph_nodes.find_one({
                    "user_id": user_id,
                    "node_type": "interest",
                    "label": topic
                })
                return node is not None
            
            elif action.entity_type == EntityType.FACT:
                # Facts are harder to match exactly
                return True  # Assume exists for facts
                
        except Exception as e:
            logger.error(f"Error checking entity existence: {e}")
            return False
        
        return False
    
    # =========================================================================
    # EXECUTOR
    # =========================================================================
    
    async def _execute_actions(
        self,
        actions: List[MemoryAction],
        user_id: str,
        avatar_id: str
    ) -> List[MemoryAction]:
        """Execute validated actions"""
        executed = []
        now = datetime.now(timezone.utc)
        
        for action in actions:
            if not action.validated:
                continue
            
            try:
                if action.entity_type == EntityType.CONNECTION:
                    await self._execute_connection_action(action, user_id, now)
                elif action.entity_type == EntityType.INTEREST:
                    await self._execute_interest_action(action, user_id, now)
                elif action.entity_type == EntityType.FACT:
                    await self._execute_fact_action(action, user_id, now)
                
                executed.append(action)
                logger.info(f"Executed: {action.action_type.value} {action.entity_type.value}")
                
            except Exception as e:
                logger.error(f"Error executing action: {e}")
        
        return executed
    
    async def _execute_connection_action(
        self,
        action: MemoryAction,
        user_id: str,
        now: datetime
    ):
        """Execute connection CREATE/UPDATE/DELETE
        
        Stores in both:
        1. users.connections - for memory/prompt
        2. graph_nodes - for frontend display
        """
        data = action.entity_data
        name = data.get("name", "").strip()
        relationship = data.get("relationship", "").strip()
        
        if action.action_type == ActionType.CREATE:
            # Store in users.connections
            await self.db.users.update_one(
                {"id": user_id},
                {
                    "$push": {
                        "connections": {
                            "name": name,
                            "relationship": relationship,
                            "details": data.get("details", ""),
                            "context": data.get("context", []),
                            "mentioned_count": 1,
                            "last_mentioned": now.isoformat(),
                            "source": "conversation"
                        }
                    }
                },
                upsert=True
            )
            
            # Also store in graph_nodes for frontend display
            node_id = f"connection_{user_id}_{name.lower().replace(' ', '_')}"
            existing_conn = await self.db.graph_nodes.find_one({
                "user_id": user_id, "node_type": "connection", "label": name.lower()
            })
            
            if existing_conn:
                await self.db.graph_nodes.update_one(
                    {"_id": existing_conn["_id"]},
                    {
                        "$set": {
                            "properties.relationship": relationship,
                            "properties.source": "conversation",
                            "updated_at": now
                        },
                        "$inc": {"mention_count": 1}
                    }
                )
            else:
                await self.db.graph_nodes.insert_one({
                    "id": node_id,
                    "user_id": user_id,
                    "node_type": "connection",
                    "label": name.lower(),
                    "display_label": name.title(),
                    "properties": {
                        "source": "conversation",
                        "service": "voice",
                        "relationship": relationship,
                        "details": data.get("details", "")
                    },
                    "strength": 0.8,
                    "mention_count": 1,
                    "created_at": now,
                    "updated_at": now
                })
            
        elif action.action_type == ActionType.UPDATE:
            update_fields = {"connections.$.last_mentioned": now.isoformat()}
            if relationship:
                update_fields["connections.$.relationship"] = relationship
            if data.get("details"):
                update_fields["connections.$.details"] = data.get("details")
            
            # Check if we're correcting a name
            corrects = data.get("corrects", "")
            if corrects:
                # Update old name to new name in users.connections
                await self.db.users.update_one(
                    {"id": user_id, "connections.name": {"$regex": f"^{corrects}$", "$options": "i"}},
                    {
                        "$set": {
                            "connections.$.name": name,
                            **update_fields
                        },
                        "$inc": {"connections.$.mentioned_count": 1}
                    }
                )
                # Update graph_nodes - rename
                await self.db.graph_nodes.update_one(
                    {"user_id": user_id, "node_type": "connection", "label": corrects.lower()},
                    {
                        "$set": {
                            "label": name.lower(),
                            "display_label": name.title(),
                            "properties.relationship": relationship,
                            "updated_at": now
                        },
                        "$inc": {"mention_count": 1}
                    }
                )
            else:
                await self.db.users.update_one(
                    {"id": user_id, "connections.name": {"$regex": f"^{name}$", "$options": "i"}},
                    {
                        "$set": update_fields,
                        "$inc": {"connections.$.mentioned_count": 1}
                    }
                )
                # Update graph_nodes
                await self.db.graph_nodes.update_one(
                    {"user_id": user_id, "node_type": "connection", "label": name.lower()},
                    {
                        "$set": {
                            "properties.relationship": relationship,
                            "properties.source": "conversation",
                            "updated_at": now
                        },
                        "$inc": {"mention_count": 1}
                    }
                )
            
        elif action.action_type == ActionType.DELETE:
            # Delete from users.connections
            await self.db.users.update_one(
                {"id": user_id},
                {"$pull": {"connections": {"name": {"$regex": f"^{name}$", "$options": "i"}}}}
            )
            # Delete from graph_nodes
            await self.db.graph_nodes.delete_one({
                "user_id": user_id,
                "node_type": "connection",
                "label": name.lower()
            })
    
    async def _execute_interest_action(
        self,
        action: MemoryAction,
        user_id: str,
        now: datetime
    ):
        """Execute interest CREATE/UPDATE/DELETE"""
        data = action.entity_data
        topic = data.get("topic", "").strip().lower()
        
        if action.action_type == ActionType.CREATE:
            node_id = f"interest_{user_id}_{topic.replace(' ', '_')}"
            # Check if exists first to avoid $inc/$setOnInsert conflict
            existing = await self.db.graph_nodes.find_one({
                "user_id": user_id, "node_type": "interest", "label": topic
            })
            
            if existing:
                # Update existing
                await self.db.graph_nodes.update_one(
                    {"_id": existing["_id"]},
                    {
                        "$set": {
                            "properties.source": "conversation",
                            "updated_at": now
                        },
                        "$inc": {"mention_count": 1}
                    }
                )
            else:
                # Insert new
                await self.db.graph_nodes.insert_one({
                    "id": node_id,
                    "user_id": user_id,
                    "node_type": "interest",
                    "label": topic,
                    "display_label": topic.title(),
                    "strength": data.get("strength", 0.7),
                    "properties": {"source": "conversation", "service": "voice"},
                    "mention_count": 1,
                    "created_at": now,
                    "updated_at": now
                })
            
        elif action.action_type == ActionType.UPDATE:
            corrects = data.get("corrects", "").lower()
            if corrects:
                # Rename interest
                await self.db.graph_nodes.update_one(
                    {"user_id": user_id, "node_type": "interest", "label": corrects},
                    {
                        "$set": {
                            "label": topic,
                            "display_label": topic.title(),
                            "updated_at": now,
                            "properties.source": "conversation"
                        },
                        "$inc": {"mention_count": 1}
                    }
                )
            else:
                # Just update strength
                await self.db.graph_nodes.update_one(
                    {"user_id": user_id, "node_type": "interest", "label": topic},
                    {
                        "$set": {"updated_at": now, "properties.source": "conversation"},
                        "$inc": {"mention_count": 1}
                    }
                )
            
        elif action.action_type == ActionType.DELETE:
            await self.db.graph_nodes.delete_one({
                "user_id": user_id,
                "node_type": "interest",
                "label": topic
            })
    
    async def _execute_fact_action(
        self,
        action: MemoryAction,
        user_id: str,
        now: datetime
    ):
        """Execute fact CREATE/UPDATE/DELETE"""
        data = action.entity_data
        fact_text = data.get("fact", "").strip()
        label = " ".join(fact_text.split()[:4]).lower()
        
        if action.action_type == ActionType.CREATE:
            node_id = f"preference_{user_id}_{label.replace(' ', '_')}"
            # Check if exists first
            existing = await self.db.graph_nodes.find_one({
                "user_id": user_id, "node_type": "preference", "label": label
            })
            
            if existing:
                # Update existing
                await self.db.graph_nodes.update_one(
                    {"_id": existing["_id"]},
                    {
                        "$set": {
                            "full_text": fact_text,
                            "display_label": fact_text[:50],
                            "properties.source": "conversation",
                            "updated_at": now
                        }
                    }
                )
            else:
                # Insert new
                await self.db.graph_nodes.insert_one({
                    "id": node_id,
                    "user_id": user_id,
                    "node_type": "preference",
                    "label": label,
                    "display_label": fact_text[:50],
                    "full_text": fact_text,
                    "strength": data.get("confidence", 0.8),
                    "properties": {"source": "conversation", "service": "voice"},
                    "created_at": now,
                    "updated_at": now
                })
            
        elif action.action_type == ActionType.UPDATE:
            corrects = data.get("corrects", "")
            if corrects:
                corrects_label = " ".join(corrects.split()[:4]).lower()
                await self.db.graph_nodes.update_one(
                    {"user_id": user_id, "node_type": "preference", "label": {"$regex": corrects_label, "$options": "i"}},
                    {
                        "$set": {
                            "label": label,
                            "display_label": fact_text[:50],
                            "full_text": fact_text,
                            "updated_at": now,
                            "properties.source": "conversation"
                        }
                    }
                )
            
        elif action.action_type == ActionType.DELETE:
            await self.db.graph_nodes.delete_one({
                "user_id": user_id,
                "node_type": "preference",
                "label": {"$regex": label, "$options": "i"}
            })
