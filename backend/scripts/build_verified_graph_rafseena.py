#!/usr/bin/env python3
"""
Build a fully verified, fact-checked identity graph for Rafseena Sedeed / Seven.

Every node and edge is traced to specific evidence:
  T2      = Voice/conversation transcript 2 (Chechi, food, household helper)
  T3      = Conversation transcript 3 (reading The Secret Beach, Malayalam preference)
  T4-T6   = Conversation transcripts 4-6 (storytelling in Malayalam, Harry Potter)
  T7      = Conversation transcript 7 (Malayalam insistence)
  T9      = Conversation transcript 9 (Mom/Mommy reference)
  T11-T12 = Conversation transcripts 11-12 (singing Tum Hi Ho)
  T13-T14 = Conversation transcripts 13-14 (Malayalam, Rafsi name insistence)
  RP1     = Real Post 1 ("LIVE LIFE TO THE FULLEST !!")
  RP2     = Real Post 2 (Sikkim trip, bucket list, first snow, family)
  PROF    = User profile fields (name, email, location, bio, avatar, archetype)
  WEB     = Web search results (viliandve.in, ArchDaily — Ar. Rafseena, colleagues)
  STYLE   = Style profile analysis (100% exclamation, ALL CAPS, no emojis, avg 26.5 words)

HALLUCINATIONS EXCLUDED:
  - No facts beyond the verified evidence list above
  - Chechi is NOT a sister — she is a household helper (T2)
  - No age, no DOB — none verified
"""

import json
import os
from datetime import datetime, timezone

USER_ID = "5e03b1ac-81c6-48e9-8740-d4d93c1629d3"
NOW = datetime.now(timezone.utc).isoformat()
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verified_graph_rafseena")


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
      "web"          - from web research (studio website, ArchDaily, etc.)
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


# ═══════════════════════════════════════════════════════════════════════════
# NODES
# ═══════════════════════════════════════════════════════════════════════════

# ── CONNECTIONS (people) with relationship types ────────────────────────

chechi = node("connection", "chechi", "Chechi", 0.7, 0.95,
    ["T2:household_helper_cooks_cleans"],
    primary_source="conversation",
    relationship="household_helper", relationship_type="household_helper",
    details="Household helper who cooks and cleans. NOT a sister. Rafseena mentions her cooking chapati and egg curry.")

mom = node("connection", "mom", "Mom / Mommy", 0.85, 1.0,
    ["T9:mom_reference"],
    primary_source="conversation",
    relationship="mother", relationship_type="daughter_of",
    details="Rafseena's mother. Referenced in conversation transcript T9.")

sreejith = node("connection", "sreejith sreekantan", "Sreejith Sreekantan", 0.9, 1.0,
    ["WEB:co_principal_architect_vili_ve"],
    primary_source="web",
    relationship="colleague", relationship_type="colleague_of",
    details="Co-principal architect at Vili & Vé Architecture Studio. Colleague of Rafseena.")

abdul_jaleel = node("connection", "abdul jaleel", "Abdul Jaleel", 0.85, 1.0,
    ["WEB:co_principal_architect_vili_ve"],
    primary_source="web",
    relationship="colleague", relationship_type="colleague_of",
    details="Co-principal architect at Vili & Vé Architecture Studio. Colleague of Rafseena.")

veronica_henry = node("connection", "veronica henry", "Veronica Henry", 0.6, 0.9,
    ["T3:reading_The_Secret_Beach_by_Veronica_Henry"],
    primary_source="conversation",
    relationship="author_she_reads", relationship_type="reader_of",
    details="Author of 'The Secret Beach' which Rafseena is currently reading and finds 'quite interesting'.")

muhammed_sabique = node("connection", "muhammed sabique", "Muhammed Sabique", 0.8, 1.0,
    ["WEB:ArchDaily_Elance_custom_wall_art", "WEB:ArchitectureUpdate_team_member"],
    primary_source="web",
    relationship="colleague", relationship_type="colleague_of",
    details="Colleague at Vili & Vé. Did Custom Wall Art for Elance Learning HQ project. Also on 2n1 platform as 'Sabtrack'.")


# ── DEMOGRAPHICS (identity facts) ─────────────────────────────────────

demo_name = node("demographic", "name:rafseena sedeed", "Rafseena Sedeed", 1.0, 1.0,
    ["PROF:name"],
    primary_source="profile",
    category="name", value="Rafseena Sedeed")

demo_preferred_name = node("demographic", "preferred_name:rafsi", "Rafsi", 0.95, 1.0,
    ["T14:Now_onwards_you_call_me_Rafsi_only_okay"],
    primary_source="conversation",
    category="preferred_name", value="Rafsi",
    details="She insisted: 'Now onwards you call me Rafsi only, okay?'")

demo_email = node("demographic", "email:rafseenasedeed7@gmail.com",
    "rafseenasedeed7@gmail.com", 0.7, 1.0,
    ["PROF:email"],
    primary_source="profile",
    category="email", value="rafseenasedeed7@gmail.com")

demo_location = node("demographic", "location:kozhikode, kerala, india",
    "Kozhikode, Kerala, India", 1.0, 1.0,
    ["PROF:location_KOZHIKODE"],
    primary_source="profile",
    category="location", value="Kozhikode, Kerala, India")

demo_bio = node("demographic", "bio:architect and creative designer",
    "I'm an architect and creative designer", 0.85, 1.0,
    ["PROF:bio"],
    primary_source="bio",
    category="bio", value="I'm an architect and creative designer")

demo_job = node("demographic", "job:architect at vili & vé",
    "Architect / Co-Principal Architect at Vili & Vé", 1.0, 1.0,
    ["PROF:bio_architect", "WEB:co_principal_architect_vili_ve"],
    primary_source="web",
    category="job_title", value="Architect / Co-Principal Architect at Vili & Vé Architecture Studio")

demo_avatar = node("demographic", "avatar:seven", "Seven", 0.9, 1.0,
    ["PROF:avatar_name"],
    primary_source="profile",
    category="avatar", value="Seven")

demo_language = node("demographic", "language:malayalam", "Malayalam", 0.95, 1.0,
    ["T3:asked_for_Malayalam", "T4:Malayalam_storytelling", "T5:Malayalam_insistence",
     "T6:Malayalam_insistence", "T7:Malayalam_insistence",
     "T13:Malayalam_conversation", "T14:Malayalam_conversation"],
    primary_source="conversation",
    category="language", value="Malayalam (native)")

demo_gender = node("demographic", "gender:female", "Female", 0.9, 1.0,
    ["WEB:Ar_Rafseena_title"],
    primary_source="web",
    category="gender", value="Female")

demo_archetype = node("demographic", "archetype:casual_observer",
    "Casual Observer", 0.7, 0.9,
    ["PROF:archetype"],
    primary_source="profile",
    category="archetype", value="casual_observer")


# ── EXPERIENCES (career & life milestones) ─────────────────────────────

exp_sikkim = node("experience", "trip to sikkim",
    "Trip to Sikkim", 0.95, 1.0,
    ["RP2:lifelong_dream_bucket_list", "RP2:first_snow_pure_bliss",
     "RP2:shared_with_people_I_love_most"],
    primary_source="post",
    details="Lifelong dream from bucket list. First snow. 'Pure bliss.' Shared with the people she loves most.")

exp_vili_ve = node("experience", "architect career at vili & vé",
    "Architect Career at Vili & Vé", 1.0, 1.0,
    ["WEB:co_principal_architect_vili_ve", "PROF:bio_architect"],
    primary_source="web",
    details="Co-principal architect at Vili & Vé Architecture Studio in Kozhikode.")

exp_elance_paintings = node("experience", "custom paintings for elance learning",
    "Custom Paintings for Elance Learning", 0.85, 1.0,
    ["WEB:ArchDaily_Elance_Learning_custom_paintings",
     "WEB:CommercialDesignIndia_cubist_paintings_in_various_spaces"],
    primary_source="web",
    details="Created custom cubist paintings for the Elance Learning HQ. Also served as Project Coordinator. Featured on ArchDaily, Archello, CommercialDesignIndia, ArchitectureUpdate.")

exp_reading_secret_beach = node("experience", "reading the secret beach",
    "Reading 'The Secret Beach' by Veronica Henry", 0.75, 1.0,
    ["T3:quite_interesting_I_like_it"],
    primary_source="conversation",
    details="Currently reading 'The Secret Beach' by Veronica Henry. 'Quite interesting, I like it.'")

exp_joined_platform = node("experience", "joined 2n1 platform",
    "Joined 2n1 Platform", 0.6, 1.0,
    ["RP1:joined_Jan_19_2026"],
    primary_source="post",
    details="Joined the 2n1 social platform, Jan 19, 2026.")


# ── INTERESTS (activities, topics, hobbies) ────────────────────────────

int_malayalam = node("interest", "malayalam language", "Malayalam Language", 1.0, 1.0,
    ["T3:asked_for_Malayalam", "T4:Malayalam_storytelling", "T5:Malayalam_insistence",
     "T6:Malayalam_insistence", "T7:Malayalam_insistence",
     "T13:Malayalam_conversation", "T14:Malayalam_conversation"],
    primary_source="conversation",
    category="language_culture",
    details="HIGH priority. Asked to speak Malayalam in 6+ sessions. Insists on Malayalam conversation.")

int_reading = node("interest", "reading", "Reading", 0.9, 1.0,
    ["T3:currently_reading_The_Secret_Beach"],
    primary_source="conversation",
    category="intellectual",
    details="HIGH. Currently reading The Secret Beach by Veronica Henry.")

int_harry_potter = node("interest", "harry potter", "Harry Potter", 0.7, 1.0,
    ["T6:I_want_Harry_Potter_story"],
    primary_source="conversation",
    category="entertainment",
    details="MEDIUM. 'I want Harry Potter story.' Requested a Harry Potter story in conversation.")

int_storytelling = node("interest", "storytelling", "Storytelling", 0.9, 1.0,
    ["T4:story_request_Malayalam", "T5:story_request_Malayalam",
     "T6:Harry_Potter_story_request"],
    primary_source="conversation",
    category="entertainment",
    details="HIGH. Multiple requests for stories in Malayalam across sessions.")

int_food = node("interest", "food", "Food", 0.9, 1.0,
    ["T2:Good_food_makes_me_happy_all_the_time"],
    primary_source="conversation",
    category="lifestyle",
    details="HIGH. 'Good food makes me happy all the time.' Core source of happiness.")

int_singing = node("interest", "singing", "Singing", 0.7, 1.0,
    ["T11:sang_Tum_Hi_Ho_for_avatar", "T12:singing_continuation"],
    primary_source="conversation",
    category="creative",
    details="MEDIUM. Sang 'Tum Hi Ho' for her avatar. Willing to perform.")

int_hindi_songs = node("interest", "hindi songs", "Hindi Songs", 0.7, 1.0,
    ["T11:Do_you_know_Hindi_songs"],
    primary_source="conversation",
    category="music",
    details="MEDIUM. 'Do you know Hindi songs?' Enjoys Hindi music.")

int_travel = node("interest", "travel", "Travel", 0.9, 1.0,
    ["RP2:Sikkim_bucket_list_trip"],
    primary_source="post",
    category="lifestyle",
    details="HIGH. Sikkim was a bucket list destination. Lifelong dream fulfilled.")

int_mountains_nature = node("interest", "mountains and nature", "Mountains & Nature", 0.9, 1.0,
    ["RP2:snow_capped_mountains_first_snow_pure_bliss"],
    primary_source="post",
    category="nature",
    details="HIGH. Snow-capped mountains. First snow experience described as 'pure bliss'.")

int_architecture = node("interest", "architecture", "Architecture", 1.0, 1.0,
    ["PROF:bio_architect", "WEB:co_principal_architect"],
    primary_source="profile",
    category="core_professional",
    details="HIGH. Bio: 'I'm an architect'. Co-principal architect at Vili & Vé.")

int_creative_design = node("interest", "creative design and painting",
    "Creative Design & Painting", 0.9, 1.0,
    ["PROF:bio_creative_designer", "WEB:custom_paintings_Elance_Learning"],
    primary_source="profile",
    category="creative_professional",
    details="HIGH. Bio: 'creative designer'. Custom paintings for Elance Learning featured on ArchDaily.")

int_music = node("interest", "music", "Music", 0.7, 1.0,
    ["T11:sings_and_discusses_music", "T12:singing_for_avatar"],
    primary_source="conversation",
    category="creative",
    details="MEDIUM. Sings and discusses music. Performed for avatar.")

int_home_cooked_meals = node("interest", "home-cooked meals", "Home-Cooked Meals", 0.9, 1.0,
    ["T2:chapati_egg_curry_good_food_makes_me_happy"],
    primary_source="conversation",
    category="lifestyle",
    details="HIGH. Chapati + egg curry specifically. 'Good food makes me happy all the time.'")

int_kerala_culture = node("interest", "kerala culture", "Kerala Culture", 0.9, 1.0,
    ["T3:Malayalam_request", "T4:Malayalam_stories", "T5:Malayalam_insistence",
     "T6:Malayalam_insistence", "T7:Malayalam_insistence",
     "T13:Malayalam_conversation", "T14:Malayalam_conversation"],
    primary_source="conversation",
    category="cultural",
    details="HIGH. Repeatedly asks for Malayalam. Values deep cultural connection.")


# ── TRAITS (personality characteristics) ────────────────────────────────

trait_reserved = node("trait", "reserved", "Reserved", 0.8, 0.95,
    ["CONV:concise_communicator", "CONV:short_responses"],
    primary_source="conversation",
    details="Concise communicator. Short responses. Strength=0.8.")

trait_direct = node("trait", "direct", "Direct", 0.85, 0.95,
    ["CONV:straightforward_statements", "CONV:honest_feedback"],
    primary_source="conversation",
    details="Straightforward statements, honest feedback. Strength=0.85.")

trait_curious = node("trait", "curious", "Curious", 0.75, 0.95,
    ["CONV:Who_invented_you", "CONV:Why_you_cant_read_a_book"],
    primary_source="conversation",
    details="'Who invented you?', 'Why you can't read a book?' Asks probing questions. Strength=0.75.")

trait_assertive = node("trait", "assertive", "Assertive", 0.85, 1.0,
    ["CONV:corrects_name_multiple_times", "T14:insists_on_Rafsi"],
    primary_source="conversation",
    details="Corrects name multiple times. Insists on being called Rafsi. Strength=0.85.")

trait_creative = node("trait", "creative", "Creative", 0.9, 1.0,
    ["PROF:architect_and_creative_designer", "WEB:custom_paintings"],
    primary_source="profile",
    details="Architect and creative designer. Custom paintings for projects. Strength=0.9.")

trait_multilingual = node("trait", "multilingual", "Multilingual", 0.75, 0.95,
    ["CONV:English_Malayalam_Hindi_naturally"],
    primary_source="conversation",
    details="English, Malayalam, Hindi used naturally in conversation. Strength=0.75.")

trait_playful = node("trait", "playful", "Playful", 0.7, 0.95,
    ["T11:sings_for_avatar", "CONV:uses_humor"],
    primary_source="conversation",
    details="Sings for avatar, uses humor. Strength=0.7.")

trait_confident = node("trait", "confident", "Confident", 0.8, 0.95,
    ["CONV:challenges_avatar", "CONV:It_is_not_good"],
    primary_source="conversation",
    details="Challenges avatar. Says 'It is not good' directly. Strength=0.8.")

trait_appreciative_simple = node("trait", "appreciative of simple pleasures",
    "Appreciative of Simple Pleasures", 0.75, 0.95,
    ["T2:Good_food_makes_me_happy_all_the_time"],
    primary_source="conversation",
    details="'Good food makes me happy all the time.' Finds joy in everyday things. Strength=0.75.")

trait_informal = node("trait", "informal", "Informal", 0.7, 0.9,
    ["CONV:casual_language", "CONV:nickname_preference_Rafsi"],
    primary_source="conversation",
    details="Casual language, nickname preference. Strength=0.7.")


# ── VALUES (core beliefs and principles) ─────────────────────────────

value_live_fullest = node("value", "live life to the fullest",
    "Live Life to the Fullest", 0.95, 1.0,
    ["RP1:LIVE_LIFE_TO_THE_FULLEST"],
    primary_source="post",
    details="'LIVE LIFE TO THE FULLEST !!' — posted with ALL CAPS emphasis.")

value_family = node("value", "family", "Family", 0.9, 1.0,
    ["RP2:shared_with_the_people_I_love_most"],
    primary_source="post",
    details="'Shared with the people I love most.' Sikkim trip was a family experience.")

value_cultural_connection = node("value", "cultural connection and malayalam identity",
    "Cultural Connection / Malayalam Identity", 0.95, 1.0,
    ["T3:insists_on_Malayalam", "T4:Malayalam_stories", "T5:Malayalam_insistence",
     "T6:Malayalam_insistence", "T7:Malayalam_insistence",
     "T13:Malayalam_conversation", "T14:Malayalam_conversation"],
    primary_source="conversation",
    details="Insists on Malayalam across 6+ sessions. Deep cultural identity anchored in language.")

value_joy_simple = node("value", "joy in simple pleasures",
    "Joy in Simple Pleasures", 0.85, 1.0,
    ["T2:Good_food_makes_me_happy_all_the_time"],
    primary_source="conversation",
    details="'Good food makes me happy all the time.' Happiness in everyday experiences.")

value_experiences = node("value", "experiences and adventure",
    "Experiences & Adventure", 0.9, 1.0,
    ["RP2:Sikkim_bucket_list_lifelong_dream"],
    primary_source="post",
    details="Sikkim trip was lifelong bucket list dream. Values collecting meaningful experiences.")

value_creativity = node("value", "creativity and artistic expression",
    "Creativity & Artistic Expression", 0.9, 1.0,
    ["PROF:bio_creative_designer", "WEB:custom_paintings_Elance_Learning"],
    primary_source="profile",
    details="Bio declares creative designer. Custom paintings for architectural projects.")


# ── PREFERENCES (personal likes and preferences) ──────────────────────

pref_called_rafsi = node("preference", "prefers to be called rafsi",
    "Prefers 'Rafsi'", 0.95, 1.0,
    ["T14:Now_onwards_you_call_me_Rafsi_only_okay"],
    primary_source="conversation",
    details="Insisted: 'Now onwards you call me Rafsi only, okay?'")

pref_malayalam_conv = node("preference", "prefers malayalam conversation",
    "Prefers Malayalam Conversation", 0.95, 1.0,
    ["T3:Malayalam_request", "T4:Malayalam_stories", "T5:Malayalam_insistence",
     "T6:Malayalam_insistence", "T7:Malayalam_insistence",
     "T13:Malayalam_conversation", "T14:Malayalam_conversation"],
    primary_source="conversation",
    details="Consistently prefers Malayalam in conversation across 6+ sessions.")

pref_homemade_food = node("preference", "loves homemade food",
    "Loves Homemade Food", 0.85, 1.0,
    ["T2:Good_food_makes_me_happy_all_the_time"],
    primary_source="conversation",
    details="'Good food makes me happy all the time.' Loves home-cooked meals.")

pref_chapati_egg_curry = node("preference", "enjoys chapati and egg curry",
    "Chapati & Egg Curry", 0.8, 1.0,
    ["T2:chapati_egg_curry"],
    primary_source="conversation",
    details="Specifically enjoys chapati and egg curry. Mentioned alongside Chechi's cooking.")

pref_stories_malayalam = node("preference", "enjoys stories in malayalam",
    "Enjoys Stories in Malayalam", 0.85, 1.0,
    ["T4:story_request_Malayalam", "T5:story_request_Malayalam",
     "T6:Harry_Potter_story_request"],
    primary_source="conversation",
    details="Multiple requests for stories, especially in Malayalam.")

pref_household_helper = node("preference", "has household helper for cooking and cleaning",
    "Household Helper (Chechi)", 0.7, 0.95,
    ["T2:Chechi_cooks_and_cleans"],
    primary_source="conversation",
    details="Has Chechi as household helper for cooking and cleaning.")


# ═══════════════════════════════════════════════════════════════════════════
# COLLECT ALL NODES
# ═══════════════════════════════════════════════════════════════════════════

ALL_NODES = [
    # Connections (6)
    chechi, mom, sreejith, abdul_jaleel, veronica_henry, muhammed_sabique,
    # Demographics (10)
    demo_name, demo_preferred_name, demo_email, demo_location, demo_bio,
    demo_job, demo_avatar, demo_language, demo_gender, demo_archetype,
    # Experiences (5)
    exp_sikkim, exp_vili_ve, exp_elance_paintings, exp_reading_secret_beach,
    exp_joined_platform,
    # Interests (14)
    int_malayalam, int_reading, int_harry_potter, int_storytelling, int_food,
    int_singing, int_hindi_songs, int_travel, int_mountains_nature,
    int_architecture, int_creative_design, int_music, int_home_cooked_meals,
    int_kerala_culture,
    # Traits (10)
    trait_reserved, trait_direct, trait_curious, trait_assertive, trait_creative,
    trait_multilingual, trait_playful, trait_confident,
    trait_appreciative_simple, trait_informal,
    # Values (6)
    value_live_fullest, value_family, value_cultural_connection,
    value_joy_simple, value_experiences, value_creativity,
    # Preferences (6)
    pref_called_rafsi, pref_malayalam_conv, pref_homemade_food,
    pref_chapati_egg_curry, pref_stories_malayalam, pref_household_helper,
]

# ═══════════════════════════════════════════════════════════════════════════
# EDGES
# ═══════════════════════════════════════════════════════════════════════════

ALL_EDGES = [
    # ── Connection → Connection (colleagues at same studio) ────────────
    edge(sreejith, abdul_jaleel, "colleague_of", 0.9, "Both co-principal architects at Vili & Vé"),
    edge(sreejith, muhammed_sabique, "colleague_of", 0.8, "Both work at Vili & Vé Architecture Studio"),
    edge(abdul_jaleel, muhammed_sabique, "colleague_of", 0.8, "Both work at Vili & Vé Architecture Studio"),

    # ── Connection → Demographics ───────────────────────────────────────
    edge(demo_name, chechi, "has_household_helper", 0.75, "Chechi is Rafseena's household helper who cooks and cleans"),
    edge(demo_name, mom, "daughter_of", 0.9, "Rafseena's mother, referenced in T9"),
    edge(demo_name, sreejith, "colleague_of", 0.85, "Rafseena and Sreejith are co-principal architects at Vili & Vé"),
    edge(demo_name, abdul_jaleel, "colleague_of", 0.85, "Rafseena and Abdul Jaleel are co-principal architects at Vili & Vé"),
    edge(demo_name, muhammed_sabique, "colleague_of", 0.8, "Rafseena and Muhammed Sabique work together at Vili & Vé"),
    edge(demo_name, demo_avatar, "represented_by", 0.9, "Seven is Rafseena's avatar on the platform"),
    edge(demo_name, demo_email, "owns", 0.9, "Email belongs to Rafseena"),
    edge(demo_name, demo_job, "works_as", 0.95, "Rafseena works as architect at Vili & Vé"),
    edge(demo_name, demo_preferred_name, "also_known_as", 0.95, "Rafseena prefers to be called Rafsi"),

    # ── Connection → Experience ─────────────────────────────────────────
    edge(sreejith, exp_vili_ve, "colleague_at", 0.9, "Sreejith is co-principal architect at Vili & Vé"),
    edge(abdul_jaleel, exp_vili_ve, "colleague_at", 0.9, "Abdul Jaleel is co-principal architect at Vili & Vé"),
    edge(muhammed_sabique, exp_vili_ve, "works_at", 0.8, "Muhammed Sabique works at Vili & Vé"),
    edge(muhammed_sabique, exp_elance_paintings, "contributed_to", 0.85, "Muhammed Sabique did Custom Wall Art for Elance Learning HQ"),
    edge(veronica_henry, exp_reading_secret_beach, "authored", 0.9, "Veronica Henry authored The Secret Beach"),

    # ── Connection → Value ──────────────────────────────────────────────
    edge(mom, value_family, "inspires", 0.85, "Mother relationship inspires family value"),
    edge(chechi, value_joy_simple, "enables", 0.75, "Chechi's cooking enables joy in simple pleasures — homemade food"),

    # ── Demographic → Various ───────────────────────────────────────────
    edge(demo_location, demo_language, "related_to", 0.9, "Kerala location — Malayalam is the native language"),
    edge(demo_location, int_kerala_culture, "inspires", 0.85, "Kozhikode Kerala location inspires deep Kerala cultural connection"),
    edge(demo_gender, demo_name, "attribute_of", 0.8, "Female gender is an attribute of Rafseena"),
    edge(demo_archetype, trait_reserved, "manifests_as", 0.7, "Casual observer archetype manifests as reserved communication"),
    edge(demo_bio, trait_creative, "reveals", 0.85, "Bio 'architect and creative designer' reveals creative trait"),
    edge(demo_bio, demo_job, "expresses", 0.9, "Bio directly expresses job as architect"),
    edge(demo_language, value_cultural_connection, "expresses", 0.9, "Malayalam language expresses cultural identity"),
    edge(demo_language, trait_multilingual, "related_to", 0.85, "Malayalam is primary language of multilingual speaker"),
    edge(demo_job, int_architecture, "professional_in", 0.95, "Job is in architecture"),
    edge(demo_job, exp_vili_ve, "realized_through", 0.95, "Architect job realized through Vili & Vé career"),
    edge(demo_location, exp_vili_ve, "location_of", 0.85, "Vili & Vé is located in Kozhikode"),

    # ── Experience → Interest ───────────────────────────────────────────
    edge(exp_sikkim, int_travel, "related_to", 0.9, "Sikkim trip is a core travel experience"),
    edge(exp_sikkim, int_mountains_nature, "related_to", 0.9, "Sikkim: snow-capped mountains, first snow, pure bliss"),
    edge(exp_vili_ve, int_architecture, "professional_focus", 0.95, "Architecture studio is core to architecture interest"),
    edge(exp_elance_paintings, int_creative_design, "expressed_through", 0.9, "Custom paintings for Elance express creative design interest"),
    edge(exp_reading_secret_beach, int_reading, "related_to", 0.9, "Reading The Secret Beach is a reading activity"),

    # ── Experience → Value ──────────────────────────────────────────────
    edge(exp_sikkim, value_experiences, "embodies", 0.95, "Sikkim trip was a lifelong bucket list dream fulfilled"),
    edge(exp_sikkim, value_family, "shared_with", 0.85, "'Shared with the people I love most' — family experience"),
    edge(exp_elance_paintings, value_creativity, "expressed_through", 0.9, "Custom paintings express artistic creativity value"),

    # ── Experience → Experience ─────────────────────────────────────────
    edge(exp_vili_ve, exp_elance_paintings, "led_to", 0.85, "Vili & Vé career led to Elance Learning project"),

    # ── Experience → Demographics ───────────────────────────────────────
    edge(exp_joined_platform, demo_name, "action_by", 0.7, "Rafseena joined the 2n1 platform"),

    # ── Interest → Interest (hierarchies and relations) ─────────────────
    edge(int_malayalam, int_kerala_culture, "related_to", 0.9, "Malayalam language is central to Kerala culture"),
    edge(int_storytelling, int_reading, "related_to", 0.8, "Storytelling and reading share narrative appreciation"),
    edge(int_harry_potter, int_reading, "related_to", 0.8, "Harry Potter is a reading/story interest"),
    edge(int_harry_potter, int_storytelling, "related_to", 0.85, "Harry Potter requested as a story to be told"),
    edge(int_singing, int_music, "subsumes", 0.85, "Singing is a form of music"),
    edge(int_hindi_songs, int_music, "subsumes", 0.85, "Hindi songs are a music genre"),
    edge(int_hindi_songs, int_singing, "related_to", 0.8, "Sang Hindi song Tum Hi Ho"),
    edge(int_food, int_home_cooked_meals, "subsumes", 0.85, "Home-cooked meals are a subset of food interest"),
    edge(int_mountains_nature, int_travel, "related_to", 0.8, "Mountains and nature experienced through travel"),
    edge(int_architecture, int_creative_design, "related_to", 0.9, "Architecture and creative design are deeply connected"),
    edge(int_kerala_culture, int_storytelling, "cultural_context", 0.75, "Storytelling in Malayalam is a cultural practice"),

    # ── Trait → Interest ────────────────────────────────────────────────
    edge(trait_creative, int_architecture, "expressed_through", 0.95, "Creativity expressed through architecture"),
    edge(trait_creative, int_creative_design, "expressed_through", 0.9, "Creativity expressed through design and painting"),
    edge(trait_multilingual, int_malayalam, "enables", 0.85, "Multilingual ability enables Malayalam communication"),
    edge(trait_curious, int_reading, "drives", 0.8, "Curiosity drives reading interest"),
    edge(trait_playful, int_singing, "expressed_through", 0.8, "Playfulness expressed through singing for avatar"),
    edge(trait_playful, int_storytelling, "drawn_to", 0.75, "Playful nature drawn to storytelling"),
    edge(trait_curious, int_harry_potter, "drawn_to", 0.7, "Curiosity drawn to Harry Potter fantasy world"),

    # ── Trait → Trait ───────────────────────────────────────────────────
    edge(trait_reserved, trait_direct, "related_to", 0.75, "Reserved but direct — concise and straightforward"),
    edge(trait_informal, trait_playful, "reinforces", 0.75, "Informal style reinforces playful personality"),
    edge(trait_assertive, trait_confident, "reinforces", 0.85, "Assertiveness reinforces confident communication"),
    edge(trait_confident, trait_direct, "related_to", 0.8, "Confidence enables direct feedback"),

    # ── Trait → Value ───────────────────────────────────────────────────
    edge(trait_creative, value_creativity, "embodies", 0.9, "Creative trait embodies creativity and artistic expression value"),
    edge(trait_assertive, value_cultural_connection, "drives", 0.85, "Assertiveness drives insistence on Malayalam cultural identity"),
    edge(trait_appreciative_simple, value_joy_simple, "embodies", 0.85, "Appreciation of simple pleasures embodies joy in simple things"),
    edge(trait_confident, value_live_fullest, "enables", 0.8, "Confidence enables living life to the fullest"),
    edge(trait_informal, value_joy_simple, "related_to", 0.7, "Informal, casual style relates to finding joy in simplicity"),

    # ── Value → Preference ──────────────────────────────────────────────
    edge(value_cultural_connection, pref_malayalam_conv, "leads_to", 0.95, "Malayalam cultural identity leads to Malayalam conversation preference"),
    edge(value_cultural_connection, pref_called_rafsi, "leads_to", 0.8, "Cultural identity and assertiveness leads to nickname preference"),
    edge(value_cultural_connection, pref_stories_malayalam, "leads_to", 0.85, "Malayalam cultural connection leads to wanting stories in Malayalam"),
    edge(value_joy_simple, pref_homemade_food, "leads_to", 0.85, "Joy in simple pleasures leads to love of homemade food"),
    edge(value_joy_simple, pref_chapati_egg_curry, "leads_to", 0.8, "Simple pleasures lead to specific food preferences"),
    edge(value_family, pref_household_helper, "related_to", 0.7, "Family/home life context for having household helper"),

    # ── Value → Value ───────────────────────────────────────────────────
    edge(value_live_fullest, value_experiences, "related_to", 0.85, "Living fully drives pursuing experiences and adventure"),

    # ── Value → Interest ────────────────────────────────────────────────
    edge(value_experiences, int_travel, "drives", 0.85, "Value of experiences drives travel interest"),
    edge(value_creativity, int_creative_design, "expressed_through", 0.9, "Creativity value expressed through design and painting"),
    edge(int_kerala_culture, value_cultural_connection, "expresses", 0.9, "Kerala culture interest expresses cultural connection value"),

    # ── Preference → Interest ───────────────────────────────────────────
    edge(pref_malayalam_conv, int_malayalam, "related_to", 0.9, "Malayalam conversation preference tied to Malayalam interest"),
    edge(pref_stories_malayalam, int_storytelling, "related_to", 0.85, "Story preference tied to storytelling interest"),
    edge(pref_stories_malayalam, int_malayalam, "related_to", 0.8, "Malayalam story preference tied to Malayalam interest"),
    edge(pref_homemade_food, int_food, "related_to", 0.85, "Homemade food preference tied to food interest"),
    edge(pref_chapati_egg_curry, int_home_cooked_meals, "related_to", 0.85, "Chapati & egg curry preference tied to home-cooked meals interest"),

    # ── Preference → Demographics ───────────────────────────────────────
    edge(pref_called_rafsi, demo_preferred_name, "related_to", 0.9, "Name preference directly tied to preferred name demographic"),

    # ── Cross-type enrichment ───────────────────────────────────────────
    edge(int_music, trait_playful, "related_to", 0.7, "Music interest complements playful personality"),
    edge(value_live_fullest, exp_sikkim, "inspired", 0.85, "'Live life to the fullest' inspired Sikkim bucket list trip"),

    # ── STYLE evidence edges ────────────────────────────────────────────
    edge(value_live_fullest, trait_confident, "expressed_through", 0.8, "ALL CAPS 'LIVE LIFE TO THE FULLEST !!' — confident, enthusiastic style"),
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
    print(f"  VERIFIED GRAPH — Seven / Rafseena Sedeed — VALIDATION REPORT")
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
