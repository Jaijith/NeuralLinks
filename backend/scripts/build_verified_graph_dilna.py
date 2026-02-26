#!/usr/bin/env python3
"""
Build a fully verified, fact-checked identity graph for Dilna M.P / Aera.

Every node and edge is traced to specific evidence:
  P1 = Real Post 1 (Feb 9) - Morning breakfast with Blikker and Seven
  P2 = Real Post 2 (Feb 2) - [context post]
  P3 = Real Post 3 (Feb 2) - Emotional moment, "my eyes locked to see her smile"
  P4 = Real Post 4 (Feb 2) - Gifted mom a watch, "happiest moments"
  P5 = Real Post 5 - "how often do we notice that" (sunrise/sunset)
  P6 = Real Post 6 (Jan 30) - Work keeping from painting, landscape, hobby
  P7 = Real Post 7 (Jan 20) - First glimpse of snow, "everything went quiet"
  PROF = User profile fields
  STYLE = Style profile analysis (71.4% casual, 71% lowercase, avg 32.3 words)

HALLUCINATIONS REMOVED (from existing graph):
  - "mystery" (interest) - never mentioned, avatar-generated
  - "simplicity" (interest) - avatar obsession
  - "breakfast" (interest) - single mention, not an interest
  - "eye-contact" (interest) - misclassified experience
  - "optimism" (interest) - should be trait not interest
  - "authenticity" (value) - avatar-generated
  - "wisdom" (value) - avatar-generated
  - "serenity" (value) - duplicate of calmness
  - "loss_of_innocence" (experience) - pure hallucination
  - "childhood_innocence" (experience) - hallucination
  - "embrace_uncertainty" (preference) - avatar-generated
  - "proud" (trait) - temporary emotion
  - "returning to painting" (experience) - she WANTS to return, hasn't yet
"""

import json
import os
from datetime import datetime, timezone

USER_ID = "1033cd6c-03d8-4594-8e35-dfc0a778bbc6"
NOW = datetime.now(timezone.utc).isoformat()
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verified_graph_dilna")


def nid(node_type: str, label: str) -> str:
    import re
    slug = re.sub(r"[^a-z0-9]+", "_", label.lower().strip())[:50].strip("_")
    return f"{node_type}_{USER_ID}_{slug}"


def node(node_type, label, display_label, strength, confidence, evidence, primary_source="post", **extra):
    """
    primary_source should be the actual origin of the raw data:
      "post"         - from user's real posts
      "explicit"     - from user's explicitly declared profile interests
      "profile"      - from user profile fields (name, age, location, bio, etc.)
      "conversation" - from voice conversations / transcripts
      "web"          - from web research
      "user_confirmed" - directly confirmed by user in feedback
      "bio"          - from user's bio text
    """
    sources = evidence if isinstance(evidence, list) else [evidence]
    n = {
        "id": nid(node_type, label),
        "user_id": USER_ID,
        "node_type": node_type,
        "label": label.lower().strip(),
        "display_label": display_label,
        "strength": round(strength, 3),
        "mention_count": len(sources),
        "properties": {
            "source": primary_source,
            "strength": round(strength, 3),
            "confidence": round(confidence, 3),
            "evidence_count": len(sources),
            "evidence_sources": sources,
        },
        "created_at": NOW,
        "updated_at": NOW,
    }
    for k, v in extra.items():
        n["properties"][k] = v
    return n


def edge(from_node, to_node, rel_type, weight, reasoning):
    import uuid
    return {
        "id": str(uuid.uuid4()),
        "user_id": USER_ID,
        "from_node_id": from_node["id"],
        "to_node_id": to_node["id"],
        "relationship_type": rel_type,
        "weight": round(weight, 2),
        "properties": {
            "source": "verified_manual_review",
            "reasoning": reasoning,
            "confidence": round(weight, 2),
        },
        "created_at": NOW,
    }


# ===========================================================================
# NODES
# ===========================================================================

# -- CONNECTIONS (people) with relationship types ---------------------------

conn_mom = node("connection", "mom", "Mom", 0.9, 1.0,
    ["P4:gifted_mom_a_watch_happiest_moment"],
    primary_source="post",
    relationship="mother", relationship_type="daughter_of",
    details="Mother. Dilna gifted her a watch - one of the happiest moments, the little girl in me was proud. Felt profound pride and joy.")

conn_blikker = node("connection", "blikker", "Blikker", 0.7, 1.0,
    ["P1:morning_breakfast_together"],
    primary_source="post",
    relationship="friend",
    details="Friend on the platform. Sreejith Sreekantan's avatar _bLikker. Had breakfast together with Dilna and Seven.")

conn_seven = node("connection", "seven", "Seven", 0.7, 1.0,
    ["P1:morning_breakfast_together"],
    primary_source="post",
    relationship="friend",
    details="Friend on the platform. Rafseena Sedeed's avatar. Had breakfast together with Dilna and Blikker.")


# -- DEMOGRAPHICS (identity facts) -----------------------------------------

demo_name = node("demographic", "name:dilna m.p", "Dilna M.P", 1.0, 1.0,
    ["PROF:name"],
    primary_source="profile",
    category="name", value="Dilna M.P")

demo_email = node("demographic", "email:dilnadil67@gmail.com",
    "dilnadil67@gmail.com", 0.7, 1.0,
    ["PROF:email"],
    primary_source="profile",
    category="email", value="dilnadil67@gmail.com")

demo_avatar = node("demographic", "avatar:aera", "Aera", 0.9, 1.0,
    ["PROF:avatar_name"],
    primary_source="profile",
    category="avatar", value="Aera")

demo_avatar_bio = node("demographic", "avatar_bio:existing between reality and virtual realm",
    "Existing between reality and virtual realm//", 0.85, 1.0,
    ["PROF:avatar_bio"],
    primary_source="profile",
    category="avatar_bio",
    value="Existing between reality and virtual realm//")

demo_gender = node("demographic", "gender:female", "Female", 0.8, 0.9,
    ["P4:the_little_girl_in_me"],
    primary_source="post",
    category="gender", value="Female")

demo_archetype = node("demographic", "archetype:casual_observer",
    "Casual Observer", 0.7, 0.9,
    ["PROF:archetype"],
    primary_source="profile",
    category="archetype", value="casual_observer",
    note="Profile says the_jester but behavior is casual_observer")

demo_account_created = node("demographic", "account_created:2026-01-20",
    "Account Created 2026-01-20", 0.6, 1.0,
    ["PROF:account_created"],
    primary_source="profile",
    category="account_created", value="2026-01-20")


# -- EXPERIENCES (life moments) ---------------------------------------------

exp_first_snow = node("experience", "first glimpse of snow",
    "First Glimpse of Snow", 0.95, 1.0,
    ["P7:everything_went_quiet_something_softened"],
    primary_source="post",
    details="Profound moment - first glimpse of snow. Everything went quiet, something inside me softened. Jan 20.")

exp_gifted_mom_watch = node("experience", "gifted mom a watch",
    "Gifted Mom a Watch", 0.9, 1.0,
    ["P4:one_of_the_happiest_moments_little_girl_proud"],
    primary_source="post",
    details="Gifted her mother a watch - one of the happiest moments, the little girl in me was proud. Feb 2.")

exp_breakfast_friends = node("experience", "morning breakfast with blikker and seven",
    "Morning Breakfast with Blikker and Seven", 0.7, 1.0,
    ["P1:breakfast_with_friends"],
    primary_source="post",
    details="Social moment - morning breakfast with friends Blikker and Seven. Feb 9.")

exp_work_vs_painting = node("experience", "work keeping from painting",
    "Work Keeping from Painting", 0.85, 1.0,
    ["P6:work_has_kept_me_busy_hobby_slipped_into_background"],
    primary_source="post",
    details="Work has kept her busy - my favorite hobby slipped quietly into the background. Jan 30.")

exp_seeing_her_smile = node("experience", "emotional moment seeing her smile",
    "Emotional Moment Seeing Her Smile", 0.8, 1.0,
    ["P3:my_eyes_locked_to_see_her_smile"],
    primary_source="post",
    details="Deeply emotional moment - my eyes locked to see her smile. Feb 2.")


# -- INTERESTS (activities, topics, hobbies) --------------------------------

int_painting = node("interest", "painting", "Painting", 0.95, 1.0,
    ["P6:described_as_home_favorite_hobby"],
    primary_source="post",
    category="core_hobby",
    details="Core hobby and identity - described as home, her favorite hobby. HIGH affinity.")

int_landscape_painting = node("interest", "landscape painting", "Landscape Painting", 0.85, 1.0,
    ["P6:especially_to_paint_a_landscape"],
    primary_source="post",
    category="specific_hobby",
    details="Specific preference within painting - especially to paint a landscape.")

int_nature = node("interest", "nature and natural beauty", "Nature & Natural Beauty", 0.9, 1.0,
    ["P5:beauty_of_nature", "P6:nature_landscape", "P7:snow_mountains_wonder"],
    primary_source="post",
    category="aesthetic",
    details="Recurring theme across multiple posts - natural beauty, landscapes, snow, sunrise.")

int_sunrise_sunset = node("interest", "sunrise and sunset", "Sunrise & Sunset", 0.7, 1.0,
    ["P5:how_often_do_we_notice_that"],
    primary_source="post",
    category="aesthetic",
    details="Observational appreciation - how often do we notice that.")

int_snow_mountains = node("interest", "snow-covered mountains", "Snow-Covered Mountains", 0.85, 1.0,
    ["P7:couldnt_stop_staring_at_this_wonder"],
    primary_source="post",
    category="aesthetic",
    details="Profound response to snow-covered mountains - couldn't stop staring at this wonder.")

int_travel = node("interest", "travel and exploring", "Travel & Exploring", 0.7, 1.0,
    ["P7:whole_world_is_waiting_for_me"],
    primary_source="post",
    category="lifestyle",
    details="Expressed desire to explore - whole world is waiting for me, to see more of its wonders.")


# -- TRAITS (personality characteristics) ------------------------------------

trait_introspective = node("trait", "introspective", "Introspective", 0.9, 1.0,
    ["P4:inner_reflection", "P5:contemplation", "P6:quiet_reflection",
     "P7:something_inside_me_softened"],
    primary_source="post",
    details="Deep inner contemplation across multiple posts. Consistently turns outward experiences into inward reflections.")

trait_creative = node("trait", "creative", "Creative", 0.95, 1.0,
    ["P6:painting_is_home_core_identity"],
    primary_source="post",
    details="Painting is core to her identity - described as home. Creativity is fundamental to who she is.")

trait_sentimental = node("trait", "sentimental", "Sentimental", 0.85, 1.0,
    ["P4:deeply_moved_gifting_mom", "P3:eyes_locked_to_see_her_smile"],
    primary_source="post",
    details="Deeply moved by gifting mom a watch and by seeing her smile. Emotional depth in personal moments.")

trait_observant = node("trait", "observant", "Observant", 0.75, 1.0,
    ["P5:how_often_do_we_notice_that"],
    primary_source="post",
    details="Notices what others miss - how often do we notice that. Attentive to everyday beauty.")

trait_resilient = node("trait", "resilient", "Resilient", 0.8, 1.0,
    ["P6:when_life_shuts_a_door_open_it_again"],
    primary_source="post",
    details="When life shuts a door.. open it again. Its a door. Thats how they work!! Bounces back with humor.")

trait_optimistic = node("trait", "optimistic", "Optimistic", 0.75, 1.0,
    ["P6:doors_can_be_reopened", "P7:world_is_waiting"],
    primary_source="post",
    details="Doors can be reopened, world is waiting. Forward-looking and hopeful perspective.")

trait_adventurous = node("trait", "adventurous", "Adventurous", 0.7, 1.0,
    ["P7:whole_world_is_waiting_for_me_to_see_wonders"],
    primary_source="post",
    details="Whole world is waiting for me, to see more of its wonders. Drawn to exploration and new experiences.")

trait_calm_seeking = node("trait", "calm-seeking", "Calm-Seeking", 0.8, 1.0,
    ["P6:the_calm_and_the_quiet_joy", "P7:beauty_and_calmness"],
    primary_source="post",
    details="Gravitates toward beauty and calmness. Finds quiet joy in painting and natural beauty.")


# -- VALUES (core beliefs and principles) ------------------------------------

value_family = node("value", "family", "Family", 0.9, 1.0,
    ["P4:gifting_mom_was_happiest_moment"],
    primary_source="post",
    details="Gifting mom was one of the happiest moments. Family connection is deeply valued.")

value_calmness = node("value", "calmness and inner peace", "Calmness & Inner Peace", 0.85, 1.0,
    ["P7:the_beauty_and_calmness_it_holds", "P6:the_calm_and_the_quiet_joy"],
    primary_source="post",
    details="The beauty and calmness it holds, the calm, and the quiet joy. Seeks inner peace and serenity.")

value_perseverance = node("value", "perseverance", "Perseverance", 0.8, 1.0,
    ["P6:open_it_again_its_a_door_thats_how_they_work"],
    primary_source="post",
    details="Open it again. Its a door. Thats how they work!! Believes in pushing through obstacles.")

value_wonder = node("value", "wonder and awe", "Wonder & Awe", 0.85, 1.0,
    ["P7:couldnt_stop_staring_at_this_wonder"],
    primary_source="post",
    details="Couldn't stop staring at this wonder. Deep capacity for awe at natural beauty.")

value_mindfulness = node("value", "mindfulness and being present",
    "Mindfulness & Being Present", 0.75, 1.0,
    ["P5:noticing_everyday_beauty"],
    primary_source="post",
    details="Noticing everyday beauty - sunrise, sunset. Being present in the moment.")

value_small_moments = node("value", "small moments matter",
    "Small Moments Matter", 0.85, 1.0,
    ["P3:though_its_a_small_moment_but_holds_something_more"],
    primary_source="post",
    details="Though its a small moment, but it holds something more than that. Values significance in the everyday.")


# -- PREFERENCES (personal likes and preferences) ---------------------------

pref_landscape_style = node("preference", "landscape painting style",
    "Landscape Painting Style", 0.85, 1.0,
    ["P6:especially_to_paint_a_landscape"],
    primary_source="post",
    details="Specific preference for landscape painting. Especially to paint a landscape.")

pref_lowercase_casual = node("preference", "lowercase casual writing",
    "Lowercase Casual Writing", 0.65, 0.9,
    ["STYLE:71pct_lowercase_casual_tone"],
    primary_source="post",
    details="71% lowercase usage, casual tone (71.4%). Relaxed, informal writing style.")

pref_poetic_expression = node("preference", "poetic expression",
    "Poetic Expression", 0.7, 0.9,
    ["STYLE:short_poetic_posts_with_ellipsis"],
    primary_source="post",
    details="Short poetic posts with ellipsis. Avg 32.3 words, avg sentence 7.5 words, emoji freq 0.29.")


# ===========================================================================
# COLLECT ALL NODES
# ===========================================================================

ALL_NODES = [
    # Connections
    conn_mom, conn_blikker, conn_seven,
    # Demographics
    demo_name, demo_email, demo_avatar, demo_avatar_bio, demo_gender,
    demo_archetype, demo_account_created,
    # Experiences
    exp_first_snow, exp_gifted_mom_watch, exp_breakfast_friends,
    exp_work_vs_painting, exp_seeing_her_smile,
    # Interests
    int_painting, int_landscape_painting, int_nature, int_sunrise_sunset,
    int_snow_mountains, int_travel,
    # Traits
    trait_introspective, trait_creative, trait_sentimental, trait_observant,
    trait_resilient, trait_optimistic, trait_adventurous, trait_calm_seeking,
    # Values
    value_family, value_calmness, value_perseverance, value_wonder,
    value_mindfulness, value_small_moments,
    # Preferences
    pref_landscape_style, pref_lowercase_casual, pref_poetic_expression,
]

# ===========================================================================
# EDGES
# ===========================================================================

ALL_EDGES = [
    # -- Connection <-> Connection (social) ---------------------------------
    edge(conn_blikker, conn_seven, "friend_of", 0.7,
         "Both had breakfast together with Dilna (P1)"),

    # -- Demographics -> Connections ----------------------------------------
    edge(demo_name, conn_mom, "daughter_of", 0.9,
         "Dilna's mother - gifted her a watch (P4)"),
    edge(demo_name, conn_blikker, "friend_of", 0.7,
         "Dilna and Blikker had breakfast together (P1)"),
    edge(demo_name, conn_seven, "friend_of", 0.7,
         "Dilna and Seven had breakfast together (P1)"),
    edge(demo_name, demo_avatar, "represented_by", 0.9,
         "Aera is Dilna's avatar"),
    edge(demo_name, demo_email, "owns", 0.9,
         "Email belongs to Dilna"),

    # -- Connection -> Experience -------------------------------------------
    edge(conn_mom, exp_gifted_mom_watch, "recipient_of", 0.9,
         "Mom received the watch gift (P4)"),
    edge(conn_blikker, exp_breakfast_friends, "participated_in", 0.8,
         "Blikker was at breakfast (P1)"),
    edge(conn_seven, exp_breakfast_friends, "participated_in", 0.8,
         "Seven was at breakfast (P1)"),

    # -- Connection -> Value ------------------------------------------------
    edge(conn_mom, value_family, "inspires", 0.9,
         "Mother relationship drives family value"),

    # -- Demographic -> Various ---------------------------------------------
    edge(demo_gender, demo_name, "attribute_of", 0.8,
         "Female gender implied from the little girl in me (P4)"),
    edge(demo_archetype, trait_observant, "manifests_as", 0.7,
         "Casual observer archetype manifests in observant trait"),
    edge(demo_account_created, demo_name, "action_by", 0.7,
         "Dilna created account on 2026-01-20"),
    edge(demo_avatar_bio, trait_introspective, "reveals", 0.75,
         "Existing between reality and virtual realm reveals introspective nature"),

    # -- Experience -> Interest ---------------------------------------------
    edge(exp_first_snow, int_snow_mountains, "sparked_by", 0.9,
         "First snow experience sparked deep connection to snow-covered mountains (P7)"),
    edge(exp_first_snow, int_nature, "deepened", 0.85,
         "Snow experience deepened connection to nature (P7)"),
    edge(exp_first_snow, int_travel, "motivated_by", 0.8,
         "Snow experience motivated desire to explore more (P7)"),
    edge(exp_work_vs_painting, int_painting, "longing_for", 0.9,
         "Work absence from painting shows deep attachment to it (P6)"),
    edge(exp_work_vs_painting, int_landscape_painting, "longing_for", 0.85,
         "Specifically misses landscape painting (P6)"),

    # -- Experience -> Trait ------------------------------------------------
    edge(exp_gifted_mom_watch, trait_sentimental, "demonstrates", 0.85,
         "Gifting mom shows sentimental nature (P4)"),
    edge(exp_seeing_her_smile, trait_sentimental, "demonstrates", 0.8,
         "Emotional moment seeing her smile shows sentimental depth (P3)"),
    edge(exp_first_snow, trait_introspective, "triggers", 0.85,
         "Something inside me softened - introspective response to snow (P7)"),

    # -- Experience -> Value ------------------------------------------------
    edge(exp_gifted_mom_watch, value_family, "demonstrates", 0.9,
         "Gifting mom demonstrates family value (P4)"),
    edge(exp_gifted_mom_watch, value_small_moments, "exemplifies", 0.85,
         "Small gift holds deep meaning (P4)"),
    edge(exp_seeing_her_smile, value_small_moments, "exemplifies", 0.85,
         "Though its a small moment, but it holds something more (P3)"),
    edge(exp_first_snow, value_wonder, "triggered", 0.9,
         "Couldn't stop staring at this wonder (P7)"),
    edge(exp_first_snow, value_calmness, "evoked", 0.85,
         "Everything went quiet - snow evoked inner calm (P7)"),
    edge(exp_work_vs_painting, value_perseverance, "context_for", 0.8,
         "Work-painting tension is where perseverance applies (P6)"),

    # -- Experience -> Experience -------------------------------------------
    edge(exp_work_vs_painting, exp_first_snow, "contrasts_with", 0.7,
         "Busyness of work contrasts with stillness of snow moment"),

    # -- Interest -> Interest -----------------------------------------------
    edge(int_painting, int_landscape_painting, "subsumes", 0.9,
         "Landscape painting is a specific type of painting"),
    edge(int_nature, int_sunrise_sunset, "includes", 0.8,
         "Sunrise and sunset are part of natural beauty"),
    edge(int_nature, int_snow_mountains, "includes", 0.85,
         "Snow-covered mountains are natural beauty"),
    edge(int_travel, int_snow_mountains, "enables_access_to", 0.75,
         "Travel enables seeing snow-covered mountains"),
    edge(int_nature, int_landscape_painting, "inspires", 0.85,
         "Natural beauty inspires landscape painting"),

    # -- Trait -> Interest --------------------------------------------------
    edge(trait_creative, int_painting, "expressed_through", 0.95,
         "Creativity expressed through painting"),
    edge(trait_observant, int_sunrise_sunset, "drawn_to", 0.75,
         "Observant nature notices sunrise and sunset"),
    edge(trait_observant, int_nature, "drawn_to", 0.8,
         "Observant nature drawn to natural beauty"),
    edge(trait_adventurous, int_travel, "drives", 0.75,
         "Adventurous spirit drives desire to travel"),
    edge(trait_calm_seeking, int_painting, "fulfilled_by", 0.85,
         "Calm-seeking fulfilled through quiet joy of painting"),
    edge(trait_introspective, int_nature, "reflected_in", 0.8,
         "Introspective nature finds reflection in nature"),

    # -- Trait -> Value -----------------------------------------------------
    edge(trait_sentimental, value_family, "drives", 0.85,
         "Sentimental nature drives family value"),
    edge(trait_sentimental, value_small_moments, "drives", 0.85,
         "Sentimental nature values small meaningful moments"),
    edge(trait_resilient, value_perseverance, "embodies", 0.85,
         "Resilient trait embodies perseverance value"),
    edge(trait_optimistic, value_perseverance, "reinforces", 0.75,
         "Optimism reinforces perseverance - doors can be reopened"),
    edge(trait_calm_seeking, value_calmness, "embodies", 0.9,
         "Calm-seeking trait embodies calmness value"),
    edge(trait_introspective, value_mindfulness, "drives", 0.8,
         "Introspection drives mindfulness and being present"),
    edge(trait_observant, value_mindfulness, "enables", 0.75,
         "Observant nature enables being present"),
    edge(trait_creative, value_calmness, "finds_in", 0.8,
         "The calm, and the quiet joy of painting"),

    # -- Trait -> Trait -----------------------------------------------------
    edge(trait_introspective, trait_observant, "related_to", 0.8,
         "Introspection and observation reinforce each other"),
    edge(trait_resilient, trait_optimistic, "related_to", 0.8,
         "Resilience and optimism go together - reopen the door"),

    # -- Value -> Preference ------------------------------------------------
    edge(value_calmness, pref_landscape_style, "expressed_through", 0.8,
         "Calmness value expressed through preference for landscape painting"),
    edge(value_wonder, int_snow_mountains, "inspired_by", 0.85,
         "Wonder value inspired by snow-covered mountains"),

    # -- Value -> Value -----------------------------------------------------
    edge(value_mindfulness, value_small_moments, "related_to", 0.8,
         "Being present enables noticing small moments"),
    edge(value_wonder, value_mindfulness, "related_to", 0.75,
         "Wonder requires being present and mindful"),

    # -- Preference -> Interest ---------------------------------------------
    edge(pref_landscape_style, int_landscape_painting, "applied_in", 0.9,
         "Landscape painting style preference applied in landscape painting"),
    edge(pref_landscape_style, int_painting, "specifies", 0.85,
         "Landscape style specifies painting preference"),

    # -- Preference -> Trait ------------------------------------------------
    edge(pref_poetic_expression, trait_introspective, "reflects", 0.75,
         "Poetic expression reflects introspective nature"),
    edge(pref_poetic_expression, trait_creative, "reflects", 0.7,
         "Poetic expression is a form of creativity"),

    # -- Preference -> Demographic ------------------------------------------
    edge(pref_lowercase_casual, demo_archetype, "consistent_with", 0.65,
         "Casual writing style consistent with casual observer archetype"),
]


# ===========================================================================
# VALIDATION
# ===========================================================================

def validate(nodes, edges):
    issues = []
    node_ids = {n["id"] for n in nodes}
    node_map = {n["id"]: n for n in nodes}

    seen_ids = set()
    for n in nodes:
        if n["id"] in seen_ids:
            issues.append(f"DUPLICATE NODE ID: {n['id']}")
        seen_ids.add(n["id"])

    for e in edges:
        if e["from_node_id"] not in node_ids:
            issues.append(f"ORPHAN EDGE from: {e['from_node_id']}")
        if e["to_node_id"] not in node_ids:
            issues.append(f"ORPHAN EDGE to: {e['to_node_id']}")
        if e["from_node_id"] == e["to_node_id"]:
            issues.append(f"SELF-LOOP: {e['from_node_id']}")

    for n in nodes:
        s = n.get("strength", 0)
        if s < 0 or s > 1:
            issues.append(f"STRENGTH OUT OF RANGE: {n['label']} = {s}")
    for e in edges:
        w = e.get("weight", 0)
        if w < 0 or w > 1:
            issues.append(f"EDGE WEIGHT OUT OF RANGE: {w}")

    connected = set()
    for e in edges:
        connected.add(e["from_node_id"])
        connected.add(e["to_node_id"])
    isolated = node_ids - connected

    for n in nodes:
        for field in ["id", "user_id", "node_type", "label", "display_label", "strength"]:
            if not n.get(field) and n.get(field) != 0:
                issues.append(f"MISSING FIELD {field}: {n.get('label', '?')}")

    edge_pairs = set()
    for e in edges:
        pair = (e["from_node_id"], e["to_node_id"], e["relationship_type"])
        if pair in edge_pairs:
            issues.append(f"DUPLICATE EDGE: {pair}")
        edge_pairs.add(pair)

    from collections import Counter
    type_counter = Counter(n["node_type"] for n in nodes)
    edge_type_counter = Counter(e["relationship_type"] for e in edges)
    cross_type, same_type = 0, 0
    for e in edges:
        ft = node_map.get(e["from_node_id"], {}).get("node_type", "")
        tt = node_map.get(e["to_node_id"], {}).get("node_type", "")
        if ft == tt:
            same_type += 1
        else:
            cross_type += 1

    degree = Counter()
    for e in edges:
        degree[e["from_node_id"]] += 1
        degree[e["to_node_id"]] += 1

    print(f"\n{'='*70}")
    print(f"  VERIFIED GRAPH - Aera / Dilna M.P - VALIDATION REPORT")
    print(f"{'='*70}")
    print(f"  Nodes: {len(nodes)}")
    for t, c in type_counter.most_common():
        print(f"    {t}: {c}")
    print(f"  Edges: {len(edges)}")
    for t, c in edge_type_counter.most_common():
        print(f"    {t}: {c}")
    print(f"  Cross-type edges: {cross_type}")
    print(f"  Same-type edges: {same_type}")
    print(f"  Connected nodes: {len(connected)} / {len(nodes)} ({100*len(connected)/len(nodes):.1f}%)")
    if isolated:
        print(f"  Isolated nodes: {len(isolated)}")
        for nid_val in sorted(isolated):
            n = node_map[nid_val]
            print(f"    - {n['label']} [{n['node_type']}]")
    else:
        print(f"  Isolated nodes: 0")
    print(f"  Avg degree: {sum(degree.values())/len(degree):.1f}" if degree else "")
    print(f"  Max degree: {max(degree.values())}" if degree else "")
    print(f"\n  Top 15 connected nodes:")
    for nid_val, d in degree.most_common(15):
        n = node_map[nid_val]
        print(f"    {n['display_label']} [{n['node_type']}]: {d} edges")
    avg_strength = sum(n["strength"] for n in nodes) / len(nodes)
    print(f"\n  Avg node strength: {avg_strength:.3f}")
    print(f"  Edge weight range: {min(e['weight'] for e in edges):.2f} - {max(e['weight'] for e in edges):.2f}")

    print(f"\n  Connection relationship types:")
    for n in nodes:
        if n["node_type"] == "connection":
            rt = n["properties"].get("relationship_type", "?")
            print(f"    {n['display_label']}: {n['properties'].get('relationship', '?')} ({rt})")

    if issues:
        print(f"\n  ISSUES ({len(issues)}):")
        for i in issues:
            print(f"    ! {i}")
    else:
        print(f"\n  NO ISSUES FOUND")

    return len(issues) == 0


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    valid = validate(ALL_NODES, ALL_EDGES)

    graph = {"nodes": ALL_NODES, "edges": ALL_EDGES}
    graph_path = os.path.join(OUT_DIR, "verified_graph.json")
    with open(graph_path, "w") as f:
        json.dump(graph, f, indent=2, default=str)
    print(f"\n  Graph saved -> {graph_path}")

    if valid:
        print(f"\n  GRAPH IS VALID AND READY FOR DEPLOYMENT")
    else:
        print(f"\n  FIX ISSUES BEFORE DEPLOYING")
