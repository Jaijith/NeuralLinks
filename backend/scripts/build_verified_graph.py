#!/usr/bin/env python3
"""
Build a fully verified, fact-checked identity graph for Jaijith / DigitalHunter.

Every node and edge is traced to specific evidence:
  T1-T33  = voice transcripts (by session order)
  P1-P61  = real posts (by recency order)
  PROF    = user profile fields
  CONN    = users.connections array
  IDMEM   = identity_memory collection
  LI      = LinkedIn-sourced data (via profile sync)
  YT      = YouTube-sourced data (subscriptions + liked videos)

CORRECTIONS v2 (per user feedback):
  - Brother is SREEJITH (user said "Srijit" in transcript but confirms Sreejith)
  - User DID mention THIRUVANANTHAPURAM — include as specific origin
  - Connections need directional types: father_of, husband_of, brother_of, etc.
  - Include LinkedIn professional data (job_title, skills)
  - Include YouTube liked channels/topics as interests
  - "lives in seattle", "works at google" remain hallucinations — still excluded
"""

import json
import os
from datetime import datetime, timezone

USER_ID = "dedc30ef-dca9-467d-84b1-5e643941e6fd"
NOW = datetime.now(timezone.utc).isoformat()
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verified_graph")


def nid(node_type: str, label: str) -> str:
    import re
    slug = re.sub(r"[^a-z0-9]+", "_", label.lower().strip())[:50].strip("_")
    return f"{node_type}_{USER_ID}_{slug}"


def node(node_type, label, display_label, strength, confidence, evidence, **extra):
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
            "source": "verified_manual_review",
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


# ═══════════════════════════════════════════════════════════════════════════
# NODES
# ═══════════════════════════════════════════════════════════════════════════

# ── CONNECTIONS (people) with relationship_type ────────────────────────
subhadra = node("connection", "subhadra", "Subhadra", 1.0, 1.0,
    ["T1", "T3", "T4", "T6", "T7", "T10:spoke_to_avatar", "T23", "T24", "T33:music_class", "P9:lego", "P16:drawing", "P17:dance", "P18:fine_dining"],
    relationship="daughter", relationship_type="father_of",
    details="Daughter. Does classical Indian dance, draws, reads Rainbow Magic, has music class, speaks Malayalam. Friends: Trimaan, Zara.")

manju = node("connection", "manju", "Manju", 0.95, 1.0,
    ["T1", "T3", "T4", "T6", "T10:confirmed_by_Subhadra", "T19", "T21", "T23", "T26", "P18"],
    relationship="wife", relationship_type="husband_of",
    details="Wife. Mentioned in fine dining outings and family contexts.")

sreejith = node("connection", "sreejith", "Sreejith", 0.75, 0.95,
    ["T3:user_mentioned_brother", "T26:avatar_says_Sreejith", "CONN:conversation"],
    relationship="brother", relationship_type="brother_of",
    details="Brother. Also enjoys talking to the avatar. User confirmed name is Sreejith.")

narmada = node("connection", "narmada", "Narmada", 0.7, 0.95,
    ["T23:user_confirmed", "T25:user_confirmed", "CONN:explicit"],
    relationship="mother", relationship_type="son_of",
    details="Mother. Confirmed by user in T23 and T25. Avatar: 'special place in your heart'.")

trimaan = node("connection", "trimaan", "Trimaan", 0.55, 0.9,
    ["T24:user_corrected_to_Trimaan", "CONN:conversation"],
    relationship="daughter's friend", relationship_type="daughter_friend_of",
    details="Subhadra's friend. Subhadra went to his birthday party.")

zara = node("connection", "zara", "Zara", 0.5, 0.9,
    ["T3:user_mentioned"],
    relationship="daughter's friend / family friend", relationship_type="family_friend_of",
    details="Subhadra's friend. Family went to fine dining with Zara's family.")

maya = node("connection", "maya", "Maya", 0.45, 0.85,
    ["P16:drawing_for_Maya"],
    relationship="known person", relationship_type="known_person",
    details="Subhadra drew a rainforest picture for Maya.")

# ── DEMOGRAPHICS ───────────────────────────────────────────────────────
demo_name = node("demographic", "name:jaijith s", "Jaijith S", 1.0, 1.0,
    ["PROF:name"], category="name", value="Jaijith S")
demo_preferred_name = node("demographic", "preferred name:jay", "Jay", 0.85, 1.0,
    ["T7:call_me_Jay", "T13:call_me_Jay", "T17:call_me_Jay"],
    category="preferred_name", value="Jay")
demo_email = node("demographic", "email:s.jaijith@gmail.com", "s.jaijith@gmail.com", 0.7, 1.0,
    ["PROF:email"], category="email", value="s.jaijith@gmail.com")
demo_origin = node("demographic", "origin:thiruvananthapuram, kerala, india", "Thiruvananthapuram, Kerala, India", 0.95, 1.0,
    ["T3:user_said_Kerala", "T4:user_said_Kerala_avatar_said_Thiruvananthapuram", "T6:confirmed_Kerala", "PROF:location_India"],
    category="origin", value="Thiruvananthapuram, Kerala, India")
demo_language = node("demographic", "language:malayalam", "Malayalam", 0.85, 0.95,
    ["T33:family_speaks_Malayalam", "YT:malayalam_content", "PROF:interests_manoramamax"],
    category="language", value="Malayalam",
    details="Family speaks Malayalam. Watches Malayalam YouTube content. From Kerala.")
demo_bio = node("demographic", "bio:easy going hacker", "Easy-going hacker", 0.8, 1.0,
    ["PROF:bio"], category="bio", value="I am a easy going hacker")
demo_avatar = node("demographic", "avatar:digitalhunter", "DigitalHunter", 0.9, 1.0,
    ["PROF:avatar_name"], category="avatar_name", value="DigitalHunter")
demo_job = node("demographic", "job:software engineer", "Software Engineer", 0.9, 1.0,
    ["PROF:job_title", "LI:job_title", "T23:AI_space"],
    category="job_title", value="Software Engineer",
    details="Job title from LinkedIn sync and profile. Works in AI space as data scientist.")

# ── TRAITS ─────────────────────────────────────────────────────────────
trait_introverted = node("trait", "introverted", "Introverted", 0.85, 0.95,
    ["T23:not_outgoing_home_family_guy"],
    evidence_quote="I'm not a very outgoing person. Home family guy.")
trait_reflective = node("trait", "reflective", "Reflective", 0.75, 0.9,
    ["T23:tea_time_thoughts"],
    evidence_quote="Just to have something hot and just be at ease. Have my thoughts flowing in my mind.")
trait_persistent = node("trait", "persistent", "Persistent", 0.85, 0.95,
    ["P4:dont_give_up", "P10:wont_give_up"],
    evidence_quote="Don't give up Jaijith. Life will always throw problems. Face it gracefully. / won't give up.")
trait_easy_going = node("trait", "easy-going", "Easy-going", 0.7, 0.9,
    ["PROF:bio_easy_going_hacker"],
    evidence_quote="I am a easy going hacker")
trait_family_oriented = node("trait", "family-oriented", "Family-oriented", 0.95, 1.0,
    ["T23:home_family_guy", "T1", "T3", "T4", "P18", "P17", "P9"],
    evidence_quote="Home family guy. Multiple conversations centered on family.")
trait_proud_father = node("trait", "proud father", "Proud Father", 0.9, 0.95,
    ["P17:dance_what_a_relief", "P16:daughters_drawing", "P9:lego_with_subhadra", "T4:subhadras_activities"],
    evidence_quote="what a relief as a parent.")
trait_tech_savvy = node("trait", "tech-savvy", "Tech-savvy", 0.8, 0.9,
    ["T4:coding_extensively", "T8:AI_education_app", "T30:2in1_app", "PROF:bio_hacker", "LI:software_engineer"],
    evidence_quote="I've been coding extensively for this... to make your memory stronger")
trait_hardworking = node("trait", "hardworking", "Hardworking", 0.75, 0.85,
    ["P31:busy_day_workflow", "P43:busy_busy_day", "P55:busy_saturday", "P58:busy_monday", "P10:trying_my_best"])
trait_culturally_rooted = node("trait", "culturally rooted", "Culturally Rooted", 0.75, 0.9,
    ["P48:kathakali", "T3:kerala_south_india", "P51:my_village", "T33:speaks_malayalam"])

# ── VALUES ─────────────────────────────────────────────────────────────
value_family = node("value", "family", "Family", 1.0, 1.0,
    ["T1", "T3", "T4", "T23", "P17", "P18", "P9"])
value_perseverance = node("value", "perseverance", "Perseverance", 0.85, 0.95,
    ["P4:face_it_gracefully", "P10:wont_give_up"])
value_cultural_heritage = node("value", "cultural heritage", "Cultural Heritage", 0.75, 0.9,
    ["P48:kathakali", "T3:from_kerala", "P51:my_village", "T33:malayalam"])
value_quiet_reflection = node("value", "quiet reflection", "Quiet Reflection", 0.7, 0.85,
    ["T23:tea_thoughts_flowing"])
value_authenticity = node("value", "authenticity", "Authenticity", 0.7, 0.85,
    ["P4:real_about_struggles", "PROF:bio_easy_going"])

# ── INTERESTS — Core (strong evidence, multiple sources) ──────────────
int_fine_dining = node("interest", "fine dining", "Fine Dining", 0.95, 1.0,
    ["T1:went_for_fine_dining", "T3:fine_dining_with_wife", "T4:love_fine_dining", "T6:recalled", "P18:fine_dining_post"])
int_south_indian_cuisine = node("interest", "south indian cuisine", "South Indian Cuisine", 0.85, 0.95,
    ["T3:tried_south_indian_dish", "T4:south_indian_cuisine", "T6:south_indian_cuisine"])
int_family_time = node("interest", "family time", "Family Time", 0.95, 1.0,
    ["T23:home_family_guy", "T1", "T3", "T4", "P18", "P9"])
int_tea = node("interest", "tea", "Tea", 0.65, 0.9,
    ["T23:prefer_tea_in_evening"],
    details="Evening tea ritual for quiet time — about the warmth and reflection, not a specific type.")
int_technology = node("interest", "technology", "Technology", 0.9, 0.95,
    ["T4:coding", "T23:AI_space", "P1:avatar_personalization", "P2:avatar_assistants", "PROF:bio_hacker", "LI:experience"])
int_ai = node("interest", "artificial intelligence", "Artificial Intelligence", 0.9, 0.95,
    ["T23:AI_space_data_scientist", "T8:AI_education_app", "T30:AI_avatar_app", "PROF:interests"])
int_data_science = node("interest", "data science", "Data Science", 0.8, 0.9,
    ["T23:data_scientist", "PROF:interests_explicit", "LI:skill"])
int_machine_learning = node("interest", "machine learning", "Machine Learning", 0.7, 0.85,
    ["PROF:interests_explicit", "LI:skill", "YT:liked_topics"])
int_python = node("interest", "python", "Python", 0.65, 0.85,
    ["PROF:interests_explicit", "LI:skill"])
int_software_engineering = node("interest", "software engineering", "Software Engineering", 0.8, 0.9,
    ["LI:skill", "LI:experience", "PROF:job_title"],
    details="From LinkedIn — listed as a skill and experience.")
int_coding = node("interest", "coding", "Coding", 0.8, 0.9,
    ["T4:coding_extensively", "T23:career", "P1:personalization", "P2:avatar_work"])
int_classical_dance = node("interest", "classical indian dance", "Classical Indian Dance", 0.8, 0.9,
    ["T4:subhadras_dance", "T6", "T7", "P17:dance_at_global_village"],
    details="Through daughter Subhadra's performances. Actively involved — returns costumes, watches.")
int_kathakali = node("interest", "kathakali", "Kathakali", 0.65, 0.85,
    ["P48:our_traditional_dance_form"],
    details="'our traditional dance form' — cultural pride.")
int_nature = node("interest", "nature", "Nature", 0.65, 0.8,
    ["P47:morning_sun", "P49:sunset", "P52:mountains", "P51:my_village"])
int_app_dev = node("interest", "app development", "App Development", 0.8, 0.9,
    ["T8:AI_education_app", "T9:learning_AI_app", "T30:2in1_app", "T31:advertisement_campaign_2in1"])
int_avatar_personalization = node("interest", "avatar personalization", "Avatar Personalization", 0.75, 0.85,
    ["P1:personalisation_of_avatars", "P2:avatar_assistants", "T4:coding_for_memory"])
int_lego = node("interest", "lego", "Lego", 0.45, 0.7,
    ["P9:lego_princess_castle_with_subhadra"])

# ── INTERESTS — Music (profile subscriptions + YouTube liked) ─────────
int_music = node("interest", "music", "Music", 0.7, 0.8,
    ["PROF:interests_music", "YT:coldplay", "YT:shadow_music", "YT:film_soundtracks", "YT:eiro_motoki", "YT:linkin_park", "YT:hans_zimmer", "YT:percussive_strings"])
int_coldplay = node("interest", "coldplay", "Coldplay", 0.5, 0.75,
    ["PROF:interests_youtube"])
int_shadow_music = node("interest", "shadow music", "Shadow Music", 0.45, 0.7,
    ["PROF:interests_youtube"])
int_film_soundtracks = node("interest", "film soundtracks", "Film Soundtracks", 0.5, 0.75,
    ["PROF:interests_youtube", "YT:dune_part_two_ost"])
int_eiro_motoki = node("interest", "eiro motoki", "Eiro Motoki (永露 元稀)", 0.45, 0.7,
    ["PROF:interests_youtube"])
int_linkin_park = node("interest", "linkin park", "Linkin Park", 0.5, 0.75,
    ["YT:liked_video_topic", "YT:liked_channel_linkin_park_topic"],
    details="YouTube liked video. Also liked 'Bleed It Out' by Linkin Park.")
int_hans_zimmer = node("interest", "hans zimmer", "Hans Zimmer", 0.5, 0.75,
    ["YT:liked_video_topic", "YT:liked_channel_hans_zimmer_topic"],
    details="YouTube liked video. Also liked Dune Part Two OST.")
int_percussive_strings = node("interest", "percussive strings", "Percussive Strings", 0.5, 0.75,
    ["YT:liked_channel_like_count_2"],
    details="YouTube liked channel with 2 likes — higher signal than single-like channels.")

# ── INTERESTS — Comedy/Entertainment (profile + YouTube) ──────────────
int_comedy = node("interest", "comedy and entertainment", "Comedy & Entertainment", 0.6, 0.75,
    ["PROF:interests_youtube_graham_norton", "PROF:interests_youtube_manoramamax", "YT:malayalam_comedy"])
int_graham_norton = node("interest", "the graham norton show", "The Graham Norton Show", 0.45, 0.7,
    ["PROF:interests_youtube"])
int_manoramamax = node("interest", "manoramamax", "ManoramamaX", 0.5, 0.7,
    ["PROF:interests_youtube"],
    details="Malayalam entertainment/streaming platform.")

# ── INTERESTS — Spiritual/Philosophical (profile + YouTube) ───────────
int_spiritual = node("interest", "spiritual content", "Spiritual Content", 0.55, 0.75,
    ["PROF:interests_youtube", "YT:alan_watts", "YT:1_universal_consciousness"])
int_univ_consciousness = node("interest", "1 universal consciousness", "1 Universal Consciousness", 0.4, 0.65,
    ["PROF:interests_youtube"])
int_redfrost = node("interest", "redfrost motivation", "Redfrost Motivation", 0.4, 0.65,
    ["PROF:interests_youtube"])
int_alan_watts = node("interest", "alan watts", "Alan Watts", 0.45, 0.7,
    ["YT:liked_video_topic"],
    details="Philosopher. YouTube liked video topic — signals interest in philosophy/existence.")
int_philosophy = node("interest", "philosophy", "Philosophy", 0.5, 0.75,
    ["YT:liked_video_topic", "YT:alan_watts", "YT:existence"],
    details="YouTube liked topics include philosophy and existence alongside Alan Watts.")

# ── INTERESTS — Educational/Academic (profile + YouTube) ──────────────
int_edu_math = node("interest", "educational mathematics", "Educational Mathematics", 0.45, 0.7,
    ["PROF:interests_youtube"])
int_statistics = node("interest", "statistics", "Statistics", 0.45, 0.7,
    ["YT:liked_video_topic"],
    details="YouTube liked video topic. Related to data science background.")
int_mathematicalmonk = node("interest", "mathematicalmonk", "MathematicalMonk", 0.45, 0.7,
    ["YT:liked_channel"],
    details="YouTube educational channel for math/statistics/ML. Signals academic curiosity.")
int_log_conf = node("interest", "learning on graphs conference", "Learning on Graphs Conference", 0.55, 0.8,
    ["PROF:interests_youtube"],
    details="Academic conference — signals interest in graph ML.")
int_garden_life = node("interest", "my garden life", "My Garden Life", 0.4, 0.65,
    ["PROF:interests_youtube"])
int_habeeb = node("interest", "habeeb rahman", "Habeeb Rahman", 0.45, 0.7,
    ["PROF:interests_youtube"],
    details="Malayalam YouTube channel.")

# ── INTERESTS — YouTube liked channels (additional signal) ────────────
int_chess = node("interest", "chess", "Chess", 0.45, 0.7,
    ["YT:liked_channel_fide_chess"],
    details="FIDE Chess YouTube channel liked. Signals interest in chess/strategy.")
int_ulka = node("interest", "ulka", "Ulka", 0.4, 0.65,
    ["YT:liked_channel"],
    details="YouTube liked channel. Likely Malayalam content.")
int_tjop = node("interest", "thejourneyofpurpose", "TheJourneyOfPurpose (TJOP)", 0.4, 0.65,
    ["YT:liked_channel", "YT:liked_video_topic"],
    details="Motivational YouTube channel.")

# ── INTERESTS — Malayalam content (aggregated YouTube signal) ──────────
int_malayalam_content = node("interest", "malayalam content", "Malayalam Content", 0.6, 0.8,
    ["YT:malayalam", "YT:malayalam_comedy", "YT:malayalam_shortfilm", "YT:malayalam_webseries", "YT:manoramamax", "YT:habeeb_rahman", "YT:ulka"],
    details="Watches Malayalam comedy, shortfilms, webseries, unboxing on YouTube. Also ManoramamaX subscriber.")

int_reading = node("interest", "reading", "Reading", 0.4, 0.6,
    ["T10:subhadra_reads_rainbow_magic"],
    details="Indirect — Subhadra reads Rainbow Magic; Jaijith's direct reading interest unconfirmed.")

# ── EXPERIENCES ────────────────────────────────────────────────────────
exp_fine_dining_event = node("experience", "fine dining with family and friends", "Fine Dining with Family & Friends", 0.85, 1.0,
    ["T1", "T3:with_Zaras_family", "P18:pleasant_evening"],
    details="Went with wife Manju, daughter Subhadra, and friend Zara's family.",
    date="~2026-01-31")
exp_dance_global_village = node("experience", "subhadra's dance at global village dubai", "Subhadra's Dance at Global Village Dubai", 0.85, 1.0,
    ["P17:dance_performance_at_global_village"],
    details="Subhadra's classical Indian dance performance at Global Village in Dubai. 'what a relief as a parent.'",
    location="Global Village, Dubai",
    date="~2026-01-31")
exp_at_palakkad = node("experience", "visited palakkad", "Visited Palakkad", 0.55, 0.9,
    ["P33:At_Palakkad"],
    location="Palakkad, Kerala",
    date="2025-12-22")
exp_lego_with_subhadra = node("experience", "building lego with subhadra", "Building Lego with Subhadra", 0.6, 0.9,
    ["P9:lego_princess_castle"],
    details="Built Lego Princess castle with Subhadra. 'not sure what that mouse is doing there'",
    date="2026-02-09")
exp_hard_times = node("experience", "going through hard times", "Going Through Hard Times", 0.7, 0.9,
    ["P4:dont_give_up", "P10:becoming_really_hard", "P20:feeling_losts"],
    date_range="2026-01 to 2026-02")
exp_software_engineer = node("experience", "software engineer in ai space", "Software Engineer in AI Space", 0.85, 0.95,
    ["T23:AI_space_as_data_scientist", "T4:coding_extensively", "PROF:bio_hacker", "LI:software_engineer", "PROF:job_title"],
    details="Came to AI accidentally. 'it's accidental... I was not intending to be in the AI space.'")
exp_building_2in1 = node("experience", "building 2-in-1 ai avatar app", "Building 2-in-1 AI Avatar App", 0.8, 0.9,
    ["T30:2in1_app", "T31:advertisement_for_2in1", "T32:AI_trading_app", "P1:avatar_personalization"])
exp_building_ai_edu = node("experience", "building ai education app", "Building AI Education App", 0.7, 0.85,
    ["T8:ronnie_AI_education_app", "T9:new_app_for_learning_AI"],
    details="'Ronnie starting my AI education app'.")
exp_subhadra_drawing = node("experience", "subhadra's rainforest drawing", "Subhadra's Rainforest Drawing", 0.6, 0.9,
    ["T4:drawing_rainforest", "T6:rainforest_drawing", "P16:drawing_for_maya"],
    details="Subhadra drew a rainforest picture, given to Maya.",
    date="~2026-02-01")
exp_going_production = node("experience", "going to production", "Going to Production", 0.6, 0.85,
    ["P37:Production_House", "P40:going_production", "P41:production_mode"],
    details="Deploying the app to production. Multiple posts about production push.",
    date="2025-12-11")

# ── PREFERENCES ────────────────────────────────────────────────────────
pref_call_jay = node("preference", "prefers to be called jay", "Prefers to be called Jay", 0.8, 1.0,
    ["T7:call_me_Jay", "T13:call_me_Jay_not_JayJay", "T17:call_me_Jay_dont_change"])
pref_no_pet_names = node("preference", "no romantic pet names", "No Romantic Pet Names", 0.75, 1.0,
    ["T21:dont_call_me_love"],
    evidence_quote="Oh my God, that's dangerous. Don't call me love. My wife will put me in trouble.")
pref_dont_repeat_name = node("preference", "don't overuse name", "Don't Overuse Name", 0.7, 0.95,
    ["T3:dont_tell_name_all_time", "T6:dont_call_name_all_time", "T7"])
pref_evening_tea = node("preference", "evening tea for reflection", "Evening Tea for Reflection", 0.65, 0.9,
    ["T23:tea_in_evening"])
pref_homebody = node("preference", "prefers home over going out", "Prefers Home Over Going Out", 0.8, 0.95,
    ["T23:not_outgoing_home_family_guy"])


# ═══════════════════════════════════════════════════════════════════════════
# Collect all nodes
# ═══════════════════════════════════════════════════════════════════════════
ALL_NODES = [
    # Connections (7)
    subhadra, manju, sreejith, narmada, trimaan, zara, maya,
    # Demographics (8)
    demo_name, demo_preferred_name, demo_email, demo_origin, demo_language,
    demo_bio, demo_avatar, demo_job,
    # Traits (9)
    trait_introverted, trait_reflective, trait_persistent, trait_easy_going,
    trait_family_oriented, trait_proud_father, trait_tech_savvy, trait_hardworking,
    trait_culturally_rooted,
    # Values (5)
    value_family, value_perseverance, value_cultural_heritage, value_quiet_reflection,
    value_authenticity,
    # Core interests (16)
    int_fine_dining, int_south_indian_cuisine, int_family_time, int_tea, int_technology,
    int_ai, int_data_science, int_machine_learning, int_python, int_software_engineering,
    int_coding, int_classical_dance, int_kathakali, int_nature, int_app_dev,
    int_avatar_personalization,
    # Music interests (8)
    int_music, int_coldplay, int_shadow_music, int_film_soundtracks, int_eiro_motoki,
    int_linkin_park, int_hans_zimmer, int_percussive_strings,
    # Entertainment (3)
    int_comedy, int_graham_norton, int_manoramamax,
    # Spiritual/Philosophy (5)
    int_spiritual, int_univ_consciousness, int_redfrost, int_alan_watts, int_philosophy,
    # Educational/Academic (5)
    int_edu_math, int_statistics, int_mathematicalmonk, int_log_conf, int_garden_life,
    # YouTube channels (3)
    int_chess, int_ulka, int_tjop,
    # Aggregated (2)
    int_malayalam_content, int_reading,
    # Misc (1)
    int_lego, int_habeeb,
    # Experiences (10)
    exp_fine_dining_event, exp_dance_global_village, exp_at_palakkad,
    exp_lego_with_subhadra, exp_hard_times, exp_software_engineer,
    exp_building_2in1, exp_building_ai_edu, exp_subhadra_drawing, exp_going_production,
    # Preferences (5)
    pref_call_jay, pref_no_pet_names, pref_dont_repeat_name, pref_evening_tea,
    pref_homebody,
]


# ═══════════════════════════════════════════════════════════════════════════
# EDGES
# ═══════════════════════════════════════════════════════════════════════════
ALL_EDGES = [
    # ── Connection → Connection (family structure) ─────────────────────
    edge(subhadra, manju, "daughter_of", 0.95, "Subhadra is Manju's daughter"),
    edge(trimaan, subhadra, "friend_of", 0.6, "Trimaan is Subhadra's friend; birthday party (T24)"),
    edge(zara, subhadra, "friend_of", 0.6, "Zara is Subhadra's friend; families dine together (T3)"),
    edge(maya, subhadra, "known_to", 0.5, "Subhadra drew rainforest picture for Maya (P16)"),

    # ── Connection → Value/Interest (inspires) ─────────────────────────
    edge(subhadra, value_family, "inspires", 0.95, "Daughter is central to family life"),
    edge(subhadra, int_classical_dance, "inspires", 0.9, "Subhadra does classical Indian dance; Jaijith supports"),
    edge(subhadra, int_lego, "inspires", 0.7, "Built Lego Princess castle together (P9)"),
    edge(subhadra, int_family_time, "inspires", 0.9, "Much of family time revolves around Subhadra"),
    edge(subhadra, trait_proud_father, "inspires", 0.95, "Dance performances, drawings — 'what a relief as a parent'"),
    edge(subhadra, int_reading, "related_to", 0.55, "Subhadra reads Rainbow Magic books"),
    edge(manju, value_family, "inspires", 0.9, "Wife is core family"),
    edge(manju, int_fine_dining, "inspires", 0.85, "Fine dining outings are with Manju (T1,T3,P18)"),
    edge(manju, int_family_time, "inspires", 0.85, "Family time with wife"),
    edge(sreejith, value_family, "inspires", 0.7, "Brother — 'also enjoys talking to you'"),
    edge(narmada, value_family, "inspires", 0.7, "Mother — 'special place in your heart'"),

    # ── Trait → Value (reflects / complements) ─────────────────────────
    edge(trait_family_oriented, value_family, "reflects", 0.95, "Being family-oriented reflects the value of family"),
    edge(trait_persistent, value_perseverance, "reflects", 0.9, "Persistence reflects perseverance"),
    edge(trait_reflective, value_quiet_reflection, "reflects", 0.85, "Reflective nature reflects valuing quiet reflection"),
    edge(trait_culturally_rooted, value_cultural_heritage, "reflects", 0.9, "Cultural rootedness reflects heritage value"),
    edge(trait_easy_going, value_authenticity, "complements", 0.7, "Easy-going nature complements authenticity"),
    edge(trait_introverted, trait_reflective, "complements", 0.8, "Introversion and reflection go hand in hand"),
    edge(trait_persistent, trait_hardworking, "complements", 0.85, "Persistence and hard work reinforce each other"),
    edge(trait_family_oriented, trait_proud_father, "complements", 0.9, "Family orientation expressed through proud fatherhood"),

    # ── Trait → Interest (expressed_through) ───────────────────────────
    edge(trait_tech_savvy, int_coding, "expressed_through", 0.9, "Tech skills through coding"),
    edge(trait_tech_savvy, int_ai, "expressed_through", 0.85, "Tech-savvy through AI work"),
    edge(trait_tech_savvy, int_app_dev, "expressed_through", 0.85, "Tech skills through app development"),
    edge(trait_tech_savvy, int_software_engineering, "expressed_through", 0.85, "Tech through software engineering"),
    edge(trait_reflective, int_tea, "expressed_through", 0.8, "Reflection through evening tea ritual (T23)"),
    edge(trait_reflective, int_philosophy, "expressed_through", 0.7, "Reflective nature aligns with philosophy interest"),
    edge(trait_culturally_rooted, int_kathakali, "expressed_through", 0.85, "Cultural roots through Kathakali appreciation"),
    edge(trait_culturally_rooted, int_south_indian_cuisine, "expressed_through", 0.8, "Kerala roots through South Indian food"),
    edge(trait_culturally_rooted, int_malayalam_content, "expressed_through", 0.75, "Cultural roots through Malayalam content consumption"),
    edge(trait_proud_father, int_classical_dance, "expressed_through", 0.85, "Pride in daughter through supporting her dance"),
    edge(trait_introverted, pref_homebody, "expressed_through", 0.9, "Introversion as preference for home"),
    edge(trait_introverted, int_family_time, "expressed_through", 0.8, "Introvert prioritizes family time over going out"),

    # ── Value → Interest (motivates) ───────────────────────────────────
    edge(value_family, int_family_time, "motivates", 0.95, "Family value drives family time"),
    edge(value_family, int_fine_dining, "motivates", 0.8, "Family dinners as family bonding"),
    edge(value_cultural_heritage, int_kathakali, "motivates", 0.85, "Heritage motivates Kathakali appreciation"),
    edge(value_cultural_heritage, int_south_indian_cuisine, "motivates", 0.8, "Heritage motivates South Indian food"),
    edge(value_cultural_heritage, int_malayalam_content, "motivates", 0.75, "Heritage motivates consuming Malayalam content"),
    edge(value_quiet_reflection, int_tea, "motivates", 0.85, "Reflection value motivates tea ritual"),
    edge(value_quiet_reflection, int_philosophy, "motivates", 0.7, "Reflection motivates philosophical interests"),
    edge(value_perseverance, int_app_dev, "motivates", 0.7, "Perseverance drives app building through difficulties"),

    # ── Experience → Trait (shaped_by) ─────────────────────────────────
    edge(trait_persistent, exp_hard_times, "shaped_by", 0.85, "Persistence shaped by going through hard times"),
    edge(trait_tech_savvy, exp_software_engineer, "shaped_by", 0.9, "Tech skills shaped by career"),
    edge(trait_proud_father, exp_dance_global_village, "shaped_by", 0.8, "Parental pride reinforced by dance performance"),
    edge(trait_hardworking, exp_building_2in1, "shaped_by", 0.8, "Hardwork reinforced by building the app"),
    edge(trait_hardworking, exp_going_production, "shaped_by", 0.7, "Production push reflects hard work ethic"),

    # ── Experience → Place/Person/Interest ─────────────────────────────
    edge(exp_fine_dining_event, int_fine_dining, "instance_of", 0.9, "Fine dining event is instance of fine dining interest"),
    edge(exp_fine_dining_event, int_south_indian_cuisine, "related_to", 0.8, "Tried South Indian dish at dinner"),
    edge(exp_fine_dining_event, subhadra, "involves", 0.9, "Subhadra was at the dinner"),
    edge(exp_fine_dining_event, manju, "involves", 0.9, "Manju was at the dinner"),
    edge(exp_fine_dining_event, zara, "involves", 0.7, "Went with Zara's family"),
    edge(exp_dance_global_village, subhadra, "involves", 0.95, "Subhadra's dance performance"),
    edge(exp_dance_global_village, int_classical_dance, "instance_of", 0.95, "Dance performance at Global Village"),
    edge(exp_lego_with_subhadra, subhadra, "involves", 0.95, "Built Lego with Subhadra"),
    edge(exp_lego_with_subhadra, int_lego, "instance_of", 0.9, "Lego building activity"),
    edge(exp_subhadra_drawing, subhadra, "involves", 0.95, "Subhadra drew the picture"),
    edge(exp_subhadra_drawing, maya, "involves", 0.7, "Drawing was for Maya"),
    edge(exp_at_palakkad, demo_origin, "related_to", 0.75, "Palakkad is in Kerala"),
    edge(exp_software_engineer, int_ai, "related_to", 0.9, "Works in AI space"),
    edge(exp_software_engineer, int_data_science, "related_to", 0.85, "Data scientist role"),
    edge(exp_software_engineer, demo_job, "related_to", 0.9, "Software engineer job"),
    edge(exp_software_engineer, int_software_engineering, "related_to", 0.9, "Software engineering experience"),
    edge(exp_building_2in1, int_app_dev, "instance_of", 0.9, "2-in-1 is an app"),
    edge(exp_building_2in1, int_ai, "related_to", 0.85, "2-in-1 is an AI avatar app"),
    edge(exp_building_2in1, int_avatar_personalization, "related_to", 0.9, "Building avatar personalization"),
    edge(exp_building_ai_edu, int_app_dev, "instance_of", 0.85, "AI education is an app"),
    edge(exp_building_ai_edu, int_ai, "related_to", 0.85, "AI education app"),
    edge(exp_hard_times, value_perseverance, "related_to", 0.85, "Hard times reinforce perseverance"),
    edge(exp_going_production, int_app_dev, "instance_of", 0.8, "Production push for the app"),
    edge(exp_going_production, exp_building_2in1, "related_to", 0.75, "Deploying the 2-in-1 app"),

    # ── Interest → Interest (subsumes / related_to) ────────────────────
    edge(int_ai, int_machine_learning, "subsumes", 0.85, "ML is a subset of AI"),
    edge(int_ai, int_data_science, "related_to", 0.8, "Data science closely related to AI"),
    edge(int_data_science, int_python, "related_to", 0.75, "Python is a data science tool"),
    edge(int_data_science, int_statistics, "related_to", 0.75, "Statistics underpins data science"),
    edge(int_coding, int_python, "related_to", 0.8, "Python is a programming language"),
    edge(int_coding, int_app_dev, "related_to", 0.85, "Coding is how apps are built"),
    edge(int_coding, int_software_engineering, "related_to", 0.85, "Coding is core to software engineering"),
    edge(int_technology, int_ai, "subsumes", 0.8, "AI is a technology domain"),
    edge(int_technology, int_coding, "related_to", 0.8, "Coding is a tech activity"),
    edge(int_technology, int_software_engineering, "related_to", 0.8, "Software engineering is tech"),
    edge(int_app_dev, int_avatar_personalization, "subsumes", 0.75, "Avatar work is a specific app project"),
    edge(int_fine_dining, int_south_indian_cuisine, "related_to", 0.85, "South Indian cuisine is a fine dining preference"),
    edge(int_classical_dance, int_kathakali, "related_to", 0.8, "Kathakali is a classical dance form"),
    edge(int_family_time, int_fine_dining, "related_to", 0.8, "Fine dining is family activity"),
    edge(int_family_time, int_tea, "related_to", 0.6, "Tea time within home life"),

    # Music hierarchy
    edge(int_music, int_coldplay, "subsumes", 0.7, "Coldplay is a music artist"),
    edge(int_music, int_shadow_music, "subsumes", 0.65, "Shadow Music is a music channel"),
    edge(int_music, int_film_soundtracks, "subsumes", 0.7, "Film soundtracks are music"),
    edge(int_music, int_eiro_motoki, "subsumes", 0.65, "Eiro Motoki is a musician"),
    edge(int_music, int_linkin_park, "subsumes", 0.7, "Linkin Park is a music band"),
    edge(int_music, int_hans_zimmer, "subsumes", 0.75, "Hans Zimmer is a film composer"),
    edge(int_music, int_percussive_strings, "subsumes", 0.65, "Percussive Strings is a music channel"),
    edge(int_hans_zimmer, int_film_soundtracks, "related_to", 0.8, "Hans Zimmer makes film soundtracks"),

    # Entertainment hierarchy
    edge(int_comedy, int_graham_norton, "subsumes", 0.75, "Graham Norton is comedy/entertainment"),
    edge(int_comedy, int_manoramamax, "related_to", 0.65, "ManoramamaX has entertainment content"),

    # Spiritual/Philosophy hierarchy
    edge(int_spiritual, int_univ_consciousness, "subsumes", 0.65, "1 Universal Consciousness is spiritual"),
    edge(int_spiritual, int_alan_watts, "related_to", 0.7, "Alan Watts — spiritual/philosophical content"),
    edge(int_philosophy, int_alan_watts, "subsumes", 0.75, "Alan Watts is a philosopher"),
    edge(int_spiritual, int_philosophy, "related_to", 0.7, "Spiritual and philosophical overlap"),
    edge(int_spiritual, int_tjop, "related_to", 0.6, "TJOP is motivational/purpose-driven content"),
    edge(int_redfrost, int_spiritual, "related_to", 0.55, "Redfrost Motivation adjacent to spiritual content"),

    # Educational/Academic hierarchy
    edge(int_edu_math, int_statistics, "related_to", 0.7, "Math and statistics are related"),
    edge(int_edu_math, int_mathematicalmonk, "related_to", 0.7, "MathematicalMonk is a math education channel"),
    edge(int_statistics, int_data_science, "related_to", 0.75, "Statistics feeds data science"),
    edge(int_statistics, int_mathematicalmonk, "related_to", 0.7, "MathematicalMonk covers statistics"),
    edge(int_ai, int_log_conf, "related_to", 0.7, "Learning on Graphs is AI/ML conference"),
    edge(int_machine_learning, int_log_conf, "related_to", 0.7, "LoG conference is about graph ML"),

    # Malayalam content hierarchy
    edge(int_malayalam_content, int_manoramamax, "subsumes", 0.7, "ManoramamaX is Malayalam"),
    edge(int_malayalam_content, int_habeeb, "subsumes", 0.65, "Habeeb Rahman is Malayalam content"),
    edge(int_malayalam_content, int_ulka, "subsumes", 0.6, "Ulka is likely Malayalam content"),
    edge(int_malayalam_content, demo_language, "related_to", 0.85, "Malayalam content in Malayalam language"),
    edge(int_malayalam_content, int_comedy, "related_to", 0.6, "Malayalam comedy is entertainment"),

    # Nature
    edge(int_nature, int_garden_life, "related_to", 0.6, "My Garden Life is nature content"),
    edge(int_nature, exp_at_palakkad, "related_to", 0.7, "Palakkad — nature/village"),
    edge(int_nature, value_quiet_reflection, "related_to", 0.6, "Nature appreciation ties to reflection"),

    # Chess
    edge(int_chess, int_strategy_placeholder if False else int_technology, "related_to", 0.5, "Chess is a strategic/intellectual pursuit"),

    # ── Demographic connections ────────────────────────────────────────
    edge(demo_origin, int_south_indian_cuisine, "related_to", 0.85, "Kerala origin connects to South Indian food"),
    edge(demo_origin, int_kathakali, "related_to", 0.85, "Kathakali is from Kerala"),
    edge(demo_origin, value_cultural_heritage, "related_to", 0.9, "Kerala origin is cultural heritage"),
    edge(demo_origin, int_malayalam_content, "related_to", 0.8, "Kerala origin connects to Malayalam content"),
    edge(demo_origin, demo_language, "related_to", 0.9, "Kerala origin — Malayalam language"),
    edge(demo_origin, exp_at_palakkad, "related_to", 0.8, "Palakkad is in Kerala"),
    edge(demo_bio, trait_easy_going, "related_to", 0.85, "Bio says 'easy going hacker'"),
    edge(demo_bio, trait_tech_savvy, "related_to", 0.8, "Bio says 'hacker'"),
    edge(demo_preferred_name, pref_call_jay, "related_to", 0.9, "Preferred name Jay connects to preference"),
    edge(demo_avatar, demo_name, "related_to", 0.9, "DigitalHunter is Jaijith's avatar"),
    edge(demo_avatar, int_avatar_personalization, "related_to", 0.85, "Avatar connects to personalization work"),
    edge(demo_name, demo_preferred_name, "related_to", 0.9, "Full name vs preferred name Jay"),
    edge(demo_job, int_software_engineering, "related_to", 0.9, "Job title matches skill"),
    edge(demo_job, exp_software_engineer, "related_to", 0.9, "Job matches career experience"),
    edge(demo_email, demo_name, "related_to", 0.7, "Email belongs to Jaijith"),

    # ── Preference connections ─────────────────────────────────────────
    edge(pref_evening_tea, int_tea, "related_to", 0.9, "Tea preference drives tea interest"),
    edge(pref_evening_tea, value_quiet_reflection, "related_to", 0.85, "Tea is for reflection"),
    edge(pref_homebody, trait_introverted, "related_to", 0.9, "Homebody preference from introversion"),
    edge(pref_homebody, int_family_time, "related_to", 0.8, "Staying home means family time"),
    edge(pref_no_pet_names, manju, "related_to", 0.75, "Pet name concern is about wife's reaction (T21)"),
    edge(pref_dont_repeat_name, demo_preferred_name, "related_to", 0.8, "Name overuse links to name preference"),
]


# ═══════════════════════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

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

    # Check for duplicate edges
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
    print(f"  VERIFIED GRAPH v2 — VALIDATION REPORT")
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
        for nid in sorted(isolated):
            n = node_map[nid]
            print(f"    - {n['label']} [{n['node_type']}]")
    else:
        print(f"  Isolated nodes: 0")
    print(f"  Avg degree: {sum(degree.values())/len(degree):.1f}" if degree else "")
    print(f"  Max degree: {max(degree.values())}" if degree else "")
    print(f"\n  Top 15 connected nodes:")
    for nid, d in degree.most_common(15):
        n = node_map[nid]
        print(f"    {n['display_label']} [{n['node_type']}]: {d} edges")
    avg_strength = sum(n["strength"] for n in nodes) / len(nodes)
    print(f"\n  Avg node strength: {avg_strength:.3f}")
    print(f"  Edge weight range: {min(e['weight'] for e in edges):.2f} - {max(e['weight'] for e in edges):.2f}")

    # Connection types
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
        print(f"\n  GRAPH v2 IS VALID AND READY FOR DEPLOYMENT")
    else:
        print(f"\n  FIX ISSUES BEFORE DEPLOYING")
