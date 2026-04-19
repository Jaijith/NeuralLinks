"""
Memory API Routes — Dual-Memory Architecture endpoints.

Provides:
- Manual consolidation triggers (admin)
- STM observation stats (debug)
- Consolidation status and history
- Memory overview (STM + LTM combined view)
- Evidence log lookup per entity
- Consolidation run history
- Scheduler status + threshold checks
"""

from fastapi import APIRouter, HTTPException, Query, Request
from datetime import datetime, timezone
from typing import Optional
import logging

from core.database import get_database
from core.auth import require_auth

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.post("/consolidate")
async def trigger_consolidation(request: Request):
    """
    Manually trigger consolidation for the authenticated user.
    Runs the full STM → LTM pipeline: Classification Agent decisions are already
    in STM, this runs the Consolidation Agent to reason and apply to LTM.
    """
    try:
        user = await require_auth(request)
        db = get_database()

        from app.globals import openai_client
        from domain.memory.consolidation_pipeline import ConsolidationPipeline

        pipeline = ConsolidationPipeline(db, openai_client)
        stats = await pipeline.run_for_user(user.id)

        return {
            "success": True,
            "stats": stats,
            "message": f"Consolidation complete for user {user.id[:8]}...",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Manual consolidation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/consolidate/all")
async def trigger_consolidation_all(request: Request):
    """
    Trigger consolidation for ALL users with unconsolidated observations.
    Admin-only endpoint.
    """
    try:
        user = await require_auth(request)
        db = get_database()

        from app.globals import openai_client
        from domain.memory.consolidation_pipeline import ConsolidationPipeline

        pipeline = ConsolidationPipeline(db, openai_client)
        results = await pipeline.run_for_all_users()

        return {
            "success": True,
            "users_processed": len(results),
            "results": results,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch consolidation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stm/stats")
async def get_stm_stats(request: Request):
    """
    Get STM observation stats for the authenticated user.
    """
    try:
        user = await require_auth(request)
        db = get_database()

        total = await db.stm_observations.count_documents({"user_id": user.id})
        unconsolidated = await db.stm_observations.count_documents(
            {"user_id": user.id, "consolidated": False}
        )
        consolidated = total - unconsolidated

        # Get entity type breakdown
        pipeline = [
            {"$match": {"user_id": user.id, "consolidated": False}},
            {"$group": {"_id": "$entity_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]
        by_type = {}
        async for doc in db.stm_observations.aggregate(pipeline):
            by_type[doc["_id"]] = doc["count"]

        # Recent observations
        recent = await db.stm_observations.find(
            {"user_id": user.id},
            {"_id": 0, "entity_label": 1, "entity_type": 1,
             "observation_subtype": 1, "confidence": 1,
             "source": 1, "observed_at": 1, "consolidated": 1}
        ).sort("observed_at", -1).limit(20).to_list(20)

        return {
            "total_observations": total,
            "unconsolidated": unconsolidated,
            "consolidated": consolidated,
            "by_entity_type": by_type,
            "recent": recent,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"STM stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ltm/stats")
async def get_ltm_stats(request: Request):
    """
    Get LTM (graph_nodes) Bayesian stats for the authenticated user.
    """
    try:
        user = await require_auth(request)
        db = get_database()

        total = await db.graph_nodes.count_documents({"user_id": user.id})
        bayesian = await db.graph_nodes.count_documents(
            {"user_id": user.id, "belief_alpha": {"$exists": True}}
        )

        # Status breakdown
        pipeline = [
            {"$match": {"user_id": user.id}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]
        by_status = {}
        async for doc in db.graph_nodes.aggregate(pipeline):
            by_status[doc["_id"] or "legacy"] = doc["count"]

        # Type breakdown
        pipeline2 = [
            {"$match": {"user_id": user.id}},
            {"$group": {"_id": "$node_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]
        by_type = {}
        async for doc in db.graph_nodes.aggregate(pipeline2):
            by_type[doc["_id"]] = doc["count"]

        # Top nodes by salience
        top = await db.graph_nodes.find(
            {"user_id": user.id, "salience": {"$exists": True}},
            {"_id": 0, "label": 1, "node_type": 1, "salience": 1,
             "belief_strength": 1, "status": 1,
             "narrative_descriptor": 1, "evidence_count": 1}
        ).sort("salience", -1).limit(15).to_list(15)

        return {
            "total_nodes": total,
            "bayesian_enhanced": bayesian,
            "by_status": by_status,
            "by_type": by_type,
            "top_by_salience": top,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LTM stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/overview")
async def get_memory_overview(request: Request):
    """
    Combined STM + LTM overview with timeline and visualization data.
    """
    try:
        user = await require_auth(request)
        from app.globals import graph_service
        overview = await graph_service.get_memory_overview(user.id)
        return {"success": True, **overview}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Memory overview error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evidence/{label}")
async def get_entity_evidence(request: Request, label: str):
    """
    Full evidence log for a specific entity label.
    Returns the LTM node data + all STM observations for this entity.
    """
    try:
        user = await require_auth(request)
        db = get_database()

        label_lower = label.lower().strip()

        ltm_node = await db.graph_nodes.find_one(
            {"user_id": user.id, "label": label_lower},
            {"_id": 0},
        )

        stm_observations = await db.stm_observations.find(
            {"user_id": user.id, "entity_label": label_lower},
            {"_id": 0},
        ).sort("observed_at", -1).to_list(100)

        if not ltm_node and not stm_observations:
            raise HTTPException(
                status_code=404,
                detail=f"No evidence found for entity '{label}'",
            )

        return {
            "entity_label": label_lower,
            "ltm_node": ltm_node,
            "stm_observations": stm_observations,
            "stm_count": len(stm_observations),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Evidence lookup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/consolidation-log")
async def get_consolidation_log(
    request: Request,
    limit: int = Query(default=10, ge=1, le=50),
):
    """
    Recent consolidation run history.
    """
    try:
        await require_auth(request)
        db = get_database()

        runs = await db.consolidation_runs.find(
            {}, {"_id": 0}
        ).sort("completed_at", -1).limit(limit).to_list(limit)

        return {"runs": runs, "count": len(runs)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Consolidation log error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scheduler/status")
async def get_scheduler_status(request: Request):
    """
    Current scheduler status: last runs, pending observations, threshold info.
    """
    try:
        await require_auth(request)
        db = get_database()

        from app.globals import openai_client
        from domain.memory.consolidation_scheduler import ConsolidationScheduler

        scheduler = ConsolidationScheduler(db, openai_client)
        status = await scheduler.get_schedule_status()
        return {"success": True, **status}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scheduler status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/consolidate/threshold")
async def trigger_threshold_check(request: Request):
    """
    Check if the authenticated user has crossed the high-activity threshold
    and trigger early consolidation if so.
    """
    try:
        user = await require_auth(request)
        db = get_database()

        from app.globals import openai_client
        from domain.memory.consolidation_scheduler import ConsolidationScheduler

        scheduler = ConsolidationScheduler(db, openai_client)
        result = await scheduler.check_and_run_threshold(user_id=user.id)
        return {"success": True, **result}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Threshold consolidation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/decay")
async def trigger_salience_decay(request: Request):
    """
    Manually trigger salience decay for the authenticated user.
    """
    try:
        user = await require_auth(request)
        db = get_database()

        from domain.memory.salience_decay import SalienceDecayService

        service = SalienceDecayService(db)
        stats = await service.decay_user(user.id)
        return {"success": True, **stats}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Salience decay error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
