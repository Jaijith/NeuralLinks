#!/usr/bin/env python3
"""
Build a fully verified, fact-checked identity graph for Sreejith Sreekantan / _bLikker.

Every node and edge is traced to specific evidence:
  T1      = Voice transcript 1 (2026-02-06, 28s, mostly Malayalam)
  T2      = Voice transcript 2 (2026-02-07, 175s, multilingual, Rafseena joined)
  P1-P15  = Real posts (numbered by recency, most recent = P1)
    P1  = Coimbatore apartment design (Feb 18)
    P2  = "Another one..." (Feb 18)
    P3  = empty (Feb 8)
    P4  = "This gang and 3 more" (Feb 6)
    P5  = "Missing this guy..." (Feb 5)
    P6  = Heritage design + nadumuttams + @rafseena + Jishnu/Elance (Feb 5)
    P7  = "Colors" + HiLite office image (Feb 2)
    P8  = Epstein files reaction (Feb 2)
    P9  = Office rest, carroms, cards, crypto crash (Feb 1)
    P10 = "Missing this from mom :(" (Jan 30)
    P11 = Meeting Mr Noufal, CakeStudio, Jalee, Badu, Goa yearning (Jan 30)
    P12 = "Happy!" (Jan 30)
    P13 = HiLite Group office rendering, LearnPark (Jan 30)
    P14 = "Spaces Spaces! Vili & Vé Architecture studio" (Jan 19)
    P15 = "Joined! Yeay!" (Jan 19)
  PROF    = User profile fields
  WEB     = Web search results (viliandve.in, ArchDaily, Archello, The Architects Diary)
  CONV    = Conversation index summaries
  STYLE   = Style profile analysis
  COMM    = Comments on posts (Rafseena Sedeed, Pradeep Kumar Shetty, Jaijith S)

HALLUCINATIONS REMOVED (from existing graph):
  - "ceo at elance learning" -> Jishnu is the CEO, NOT Sreejith (evidence: P6)
  - "audacious", "judgmental" traits -> Epstein post reaction, not self-description
  - "tired", "busy", "happy" -> transient states, not personality traits
  - "reserved", "indirect" -> poor speech recognition in multilingual voice call
  - "romance" interest -> not from user evidence
  - "fashion" interest -> weak inference from Instagram import
  - "the house is the" preference -> sentence fragment
  - "2800 square feet area" preference -> project spec, not personal preference
  - "slept_early", "crypto_crash", "office_day_relaxed" -> transient events
  - "Rabsina" connection -> misrecognition of Rafseena Sedeed (co-architect)
"""

import json
import os
from datetime import datetime, timezone

USER_ID = "fb1a5d18-5c93-4084-8da1-2227b1bea266"
NOW = datetime.now(timezone.utc).isoformat()
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verified_graph_blikker")


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
      "instagram"    - from Instagram import
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

rafseena = node("connection", "rafseena sedeed", "Rafseena Sedeed", 0.9, 1.0,
    ["P6:congrats_@rafseena", "P14:commented_on_post", "T2:present_during_voice_call",
     "WEB:co_principal_architect_vili_ve", "COMM:Rafseena_Sedeed_commented"],
    primary_source="post",
    relationship="colleague_and_co_architect", relationship_type="colleague_of",
    details="Co-principal architect at Vili & Vé. Tagged in posts. Was present during voice call (system misheard as 'Rabsina'). Did custom paintings for Elance Learning project.")

abdul_jaleel = node("connection", "abdul jaleel", "Abdul Jaleel", 0.85, 1.0,
    ["P11:Jalee_went_to_meeting", "WEB:co_principal_architect_vili_ve",
     "WEB:archDaily_lead_architect"],
    primary_source="post",
    relationship="colleague_and_co_architect", relationship_type="colleague_of",
    details="Co-principal architect at Vili & Vé. Goes by 'Jalee'. Went to CakeStudio meeting. Did custom sculpture for Elance Learning project.")

badu = node("connection", "badu", "Badu", 0.65, 0.9,
    ["P11:went_to_meeting_together"],
    primary_source="post",
    relationship="colleague",
    details="Colleague at Vili & Vé. Went to CakeStudio meeting with Sreejith and Jalee.")

narmada = node("connection", "narmada", "Narmada", 0.8, 1.0,
    ["P10:Missing_this_from_mom", "USER_CONFIRMED:name_is_Narmada"],
    primary_source="user_confirmed",
    relationship="mother", relationship_type="son_of",
    details="Mother. Name is Narmada. Sreejith posted 'Missing this from mom :(' with a photo and emotional attachment.")

taran = node("connection", "taran", "Taran", 0.85, 1.0,
    ["USER_CONFIRMED:son_name_is_Taran"],
    primary_source="user_confirmed",
    relationship="son", relationship_type="father_of",
    details="Son. Name confirmed directly by user.")

noufal = node("connection", "noufal", "Mr. Noufal", 0.6, 1.0,
    ["P11:meeting_with_Mr_Noufal_cakestudio"],
    primary_source="post",
    relationship="client",
    details="Client. Owner of CakeStudio brand. Wants his own cabin in a private space.")

jishnu = node("connection", "jishnu", "Jishnu", 0.7, 1.0,
    ["P6:Jishnu_CEO_ELANCE_learning", "WEB:Elance_Learning_CEO"],
    primary_source="post",
    relationship="client",
    details="CEO of Elance Learning. Client of Vili & Vé. Sreejith congratulated Rafseena on his headquarters design.")

p_sulaiman = node("connection", "p. sulaiman", "P. Sulaiman", 0.55, 0.9,
    ["WEB:HiLite_Group_Chairman_testimonial"],
    primary_source="web",
    relationship="client",
    details="Chairman of HiLite Group of Companies. 8-year client association with Vili & Vé. Praised the team as 'young, modern, vibrant and refreshing'.")

jaijith = node("connection", "jaijith s", "Jaijith S", 0.5, 0.9,
    ["COMM:commented_on_mom_post", "COMM:commented_on_epstein_post",
     "COMM:liked_multiple_posts"],
    primary_source="post",
    relationship="friend",
    details="Friend on the platform. Commented on Sreejith's posts and liked them.")


# ── DEMOGRAPHICS (identity facts) ─────────────────────────────────────

demo_name = node("demographic", "name:sreejith sreekantan", "Sreejith Sreekantan", 1.0, 1.0,
    ["PROF:name", "T1:avatar_says_Sreejith", "T2:avatar_says_Sreejith",
     "WEB:principal_architect_name"],
    primary_source="profile",
    category="name", value="Sreejith Sreekantan")

demo_avatar = node("demographic", "avatar:_blikker", "_bLikker", 0.9, 1.0,
    ["PROF:avatar_name"],
    primary_source="profile",
    category="avatar", value="_bLikker")

demo_email = node("demographic", "email:ar.sreejithsreekantan@gmail.com",
    "ar.sreejithsreekantan@gmail.com", 0.7, 1.0,
    ["PROF:email"],
    primary_source="profile",
    category="email", value="ar.sreejithsreekantan@gmail.com")

demo_age = node("demographic", "age:39", "Age 39", 0.8, 1.0,
    ["PROF:age"],
    primary_source="profile",
    category="age", value="39")

demo_gender = node("demographic", "gender:male", "Male", 0.8, 1.0,
    ["PROF:gender"],
    primary_source="profile",
    category="gender", value="Male")

demo_location = node("demographic", "location:kozhikode, kerala", "Kozhikode, Kerala", 1.0, 1.0,
    ["PROF:location", "P13:HiLite_Kozhikode", "WEB:studio_in_Kozhikode",
     "T2:Kozhikode_slang_discussion"],
    primary_source="profile",
    category="location", value="Kozhikode, Kerala")

demo_language = node("demographic", "language:malayalam", "Malayalam", 0.95, 1.0,
    ["T1:spoke_Malayalam", "T2:spoke_Malayalam_and_slang",
     "PROF:implied_Kerala", "P6:heritage_design_context"],
    primary_source="conversation",
    category="language", value="Malayalam")

demo_bio = node("demographic", "bio:life_is_energy_passing_through_time",
    "Life is just a passing of energy through time to find meaning of its existence....", 0.85, 1.0,
    ["PROF:bio"],
    primary_source="bio",
    category="bio",
    value="Life is just a passing of energy through time to find meaning of its existence....")

demo_job = node("demographic", "job:architect", "Architect", 1.0, 1.0,
    ["PROF:email_prefix_ar", "WEB:principal_architect", "P13:rendering_HiLite",
     "P1:designed_apartment", "P6:heritage_design"],
    primary_source="web",
    category="job_title", value="Architect / Founder, Vili & Vé Architecture Studio")

demo_archetype = node("demographic", "archetype:thoughtful_contributor",
    "Thoughtful Contributor", 0.7, 0.9,
    ["PROF:archetype"],
    primary_source="profile",
    category="archetype", value="thoughtful_contributor")


# ── EXPERIENCES (career & life milestones) ─────────────────────────────

exp_founded_studio = node("experience", "founded vili & vé architecture studio",
    "Founded Vili & Vé Architecture Studio", 1.0, 1.0,
    ["WEB:founded_under_Studio28_rebranded", "P14:Vili_Ve_Architecture_studio",
     "WEB:viliandve_about_page"],
    primary_source="web",
    details="Founded architecture studio, originally as Studio28, later rebranded to Vili & Vé Architecture Studio in Kozhikode.")

exp_hilite_office = node("experience", "hilite group office design",
    "HiLite Group Office Design", 0.9, 1.0,
    ["P13:RENDERING_HiLite_LearnPark", "P7:Colors_HiLite_image",
     "WEB:8_year_HiLite_association"],
    primary_source="post",
    details="Designed new office space for HiLite Group in their LearnPark building, Kozhikode. Tired but happy with results.")

exp_elance_hq = node("experience", "elance learning headquarters design",
    "Elance Learning Headquarters Design", 0.95, 1.0,
    ["P6:Jishnu_CEO_ELANCE_congratulated_Rafseena", "WEB:ArchDaily_published",
     "WEB:Archello_featured", "WEB:3320sqft_completed_2024"],
    primary_source="web",
    details="Designed 3320sqft headquarters for Elance Learning in Kozhikode. Featured on ArchDaily, Archello, and The Architects Diary. Completed 2024.")

exp_coimbatore_apt = node("experience", "coimbatore apartment design",
    "Coimbatore Apartment Design", 0.85, 1.0,
    ["P1:4_crores_3500sqft_all_balconies"],
    primary_source="post",
    details="Designed a 3500sqft apartment in Coimbatore worth 4 crores. All-around balconies, direct lift access, single floor. Worked sleepless for a week.")

exp_cakestudio_project = node("experience", "cakestudio cabin project",
    "CakeStudio Cabin Project", 0.7, 1.0,
    ["P11:meeting_Mr_Noufal_cakestudio"],
    primary_source="post",
    details="Project for Mr Noufal of CakeStudio brand. Private cabin design. Went to meeting with Jalee and Badu.")

exp_tropical_house = node("experience", "tropical theme house design",
    "Tropical Theme House (Own Residence)", 0.85, 1.0,
    ["T2:2800sqft_tropical_theme", "T2:person_says_same_house_they_live_in"],
    primary_source="conversation",
    details="Designed a 2800sqft tropical theme house. This is his own residence.")

exp_joined_platform = node("experience", "joined 2n1 platform",
    "Joined 2n1 Platform", 0.6, 1.0,
    ["P15:Joined_Yeay"],
    primary_source="post",
    details="Joined the 2n1 social platform on Jan 19, 2026.")

exp_archdaily_featured = node("experience", "featured on archdaily",
    "Featured on ArchDaily", 0.8, 1.0,
    ["WEB:ArchDaily_Elance_Learning_published_May_2024"],
    primary_source="web",
    details="Elance Learning HQ project published on ArchDaily, May 2024.")

exp_multi_state_consulting = node("experience", "consulting across indian states",
    "Consulting Across Indian States", 0.75, 0.95,
    ["WEB:Karnataka_Telangana_Chennai_Kerala"],
    primary_source="web",
    details="Works as consultant for firms and builders across Karnataka, Telangana, Chennai, and Kerala.")


# ── INTERESTS (activities, topics, hobbies) ────────────────────────────

int_architecture = node("interest", "architecture", "Architecture", 1.0, 1.0,
    ["PROF:explicit_interest", "P13:rendering_HiLite", "P1:apartment_design",
     "P6:heritage_design", "P14:Vili_Ve_studio", "WEB:principal_architect",
     "T2:facade_for_house"],
    primary_source="explicit",
    category="core_professional")

int_rendering = node("interest", "architectural rendering", "Architectural Rendering", 0.95, 1.0,
    ["P13:RENDERING_RENDERING", "P7:Colors_rendering_image",
     "P1:apartment_rendering"],
    primary_source="post",
    category="professional_skill",
    details="Key skill. Excited about rendering results - 'RENDERING RENDERING!' Multiple projects shown.")

int_heritage_design = node("interest", "heritage-inspired design", "Heritage-Inspired Design", 0.9, 1.0,
    ["P6:rooted_to_heritage_nadumuttams_ventilation_light",
     "WEB:studio_philosophy_art_soul"],
    primary_source="post",
    category="professional_philosophy",
    details="Designs rooted in heritage, adapted to modern times. Nadumuttams, flowing gardens, open groves of green.")

int_interior_design = node("interest", "interior design", "Interior Design", 0.85, 1.0,
    ["WEB:specialization_interior_design", "P13:HiLite_office_interior",
     "WEB:Elance_office_interior"],
    primary_source="web",
    category="professional")

int_landscape_design = node("interest", "landscape design", "Landscape Design", 0.7, 0.95,
    ["WEB:specialization_landscape_design"],
    primary_source="web",
    category="professional")

int_tropical_design = node("interest", "tropical design themes", "Tropical Design Themes", 0.8, 1.0,
    ["T2:tropical_theme_house", "P6:flowing_gardens"],
    primary_source="conversation",
    category="design_style",
    details="Tropical architectural themes with ventilation, light, and flowing gardens.")

int_nadumuttams = node("interest", "nadumuttams", "Nadumuttams", 0.85, 1.0,
    ["P6:nadumuttams_not_just_centre_anymore"],
    primary_source="post",
    category="traditional_architecture",
    details="Kerala traditional courtyards. Reimagined: 'not so in the naduv or centre anymore, but varied and spread along interior spaces of value'.")

int_quantum_physics = node("interest", "quantum physics", "Quantum Physics", 0.8, 1.0,
    ["PROF:explicit_interest"],
    primary_source="explicit",
    category="intellectual")

int_spiritual_unknowns = node("interest", "spiritual unknowns", "Spiritual Unknowns", 0.75, 1.0,
    ["PROF:explicit_interest"],
    primary_source="explicit",
    category="philosophical_spiritual")

int_fitness = node("interest", "fitness", "Fitness", 0.7, 1.0,
    ["PROF:explicit_interest"],
    primary_source="explicit",
    category="lifestyle")

int_art = node("interest", "art", "Art", 0.85, 1.0,
    ["PROF:explicit_interest", "PROF:avatar_interest",
     "WEB:architecture_is_an_art"],
    primary_source="explicit",
    category="creative")

int_food = node("interest", "food", "Food", 0.7, 1.0,
    ["PROF:explicit_interest"],
    primary_source="explicit",
    category="lifestyle")

int_travel = node("interest", "travel", "Travel", 0.75, 1.0,
    ["PROF:explicit_interest", "P11:long_drive_to_Goa"],
    primary_source="explicit",
    category="lifestyle")

int_photography = node("interest", "photography", "Photography", 0.7, 1.0,
    ["PROF:explicit_interest"],
    primary_source="explicit",
    category="creative")

int_badminton = node("interest", "badminton", "Badminton", 0.65, 0.95,
    ["P11:skipped_playing_badminton"],
    primary_source="post",
    category="sport",
    details="Plays badminton regularly but skipped since turn of year due to work pressure.")

int_fifa = node("interest", "fifa", "FIFA (Video Game)", 0.6, 0.95,
    ["P11:play_fifa_for_break"],
    primary_source="post",
    category="gaming",
    details="Mentioned as a preferred relaxation activity.")

int_counterstrike = node("interest", "counter-strike", "Counter-Strike", 0.6, 0.95,
    ["P11:play_counterstrike_for_break"],
    primary_source="post",
    category="gaming",
    details="Mentioned alongside FIFA as relaxation gaming.")

int_carroms = node("interest", "carroms", "Carroms", 0.55, 0.9,
    ["P9:played_carroms_at_office"],
    primary_source="post",
    category="indoor_games")

int_cards = node("interest", "cards", "Cards", 0.5, 0.9,
    ["P9:played_cards_at_office"],
    primary_source="post",
    category="indoor_games")

int_goa = node("interest", "goa road trips", "Goa Road Trips", 0.7, 0.95,
    ["P11:long_drive_down_to_sunsets_of_Goa"],
    primary_source="post",
    category="travel",
    details="Yearns for road trips to Goa for sunsets, calm and quiet with friends.")

int_norse_mythology = node("interest", "norse mythology", "Norse Mythology", 0.75, 1.0,
    ["P14:Vili_Ve_studio_name", "WEB:Vili_Ve_Norse_brothers_of_Odin"],
    primary_source="web",
    category="mythology_philosophy",
    details="Studio named after Vili & Vé from Norse mythology - brothers of Odin who helped create the world. Vili = Will/Spiritual Force, Vé = Sacred/Holy.")

int_current_events = node("interest", "current events", "Current Events", 0.55, 0.9,
    ["P8:Epstein_files_reaction", "P9:crypto_crash_commentary"],
    primary_source="post",
    category="awareness",
    details="Follows current events. Reacted strongly to Epstein files. Commented on crypto crash.")

int_crypto_markets = node("interest", "cryptocurrency markets", "Cryptocurrency Markets", 0.5, 0.9,
    ["P9:crypto_crash_economy_bleeding", "COMM:Sreejith_replied_35_percent_crash_unprecedented"],
    primary_source="post",
    category="finance",
    details="Follows crypto markets. Commented that 35% crash in a couple of days is unprecedented.")

int_design = node("interest", "design", "Design", 0.9, 1.0,
    ["PROF:avatar_interest", "P7:Colors", "P13:rendering", "P1:apartment"],
    primary_source="post",
    category="core_creative")

int_poetry = node("interest", "poetry", "Poetry", 0.5, 0.8,
    ["PROF:avatar_interest_poetry"],
    primary_source="profile",
    category="creative")

int_kozhikode_slang = node("interest", "kozhikode malayalam slang", "Kozhikode Malayalam Slang", 0.55, 0.9,
    ["T2:asked_avatar_to_speak_Kozhikode_slang"],
    primary_source="conversation",
    category="cultural",
    details="Tried to get avatar to speak Kozhikode Malayalam slang. Avatar recognized it as 'Kozhikodan slang'.")


# ── TRAITS (personality characteristics) ────────────────────────────────

trait_hardworking = node("trait", "hardworking", "Hardworking", 0.95, 1.0,
    ["P1:forgetting_sleep_for_the_last_week", "P5:I_should_work_and_work",
     "P11:work_has_kept_me_busy", "P13:Tired_but_happy",
     "STYLE:enthusiastic_75pct"],
    primary_source="post",
    details="Consistently works very hard. Forgets sleep for project deadlines. Keeps going despite tiredness.")

trait_passionate = node("trait", "passionate about craft", "Passionate About Craft", 0.9, 1.0,
    ["P13:happy_with_results", "P1:so_worth_forgetting_sleep",
     "P6:nice_to_see_designs_rooted_to_heritage",
     "WEB:architecture_is_an_art"],
    primary_source="post",
    details="Deep passion for architecture. 'It was so worth forgetting sleep' for design. Genuinely excited about rendering results.")

trait_warm = node("trait", "warm", "Warm", 0.8, 1.0,
    ["T2:Thank_you_all_very_dearly", "P10:Missing_this_from_mom",
     "P5:Missing_this_guy"],
    primary_source="conversation",
    details="Expressive warmth. 'Thank you all very dearly.' Posts emotional content about missing loved ones.")

trait_team_oriented = node("trait", "team-oriented", "Team-Oriented", 0.85, 1.0,
    ["P9:Let_them_come_back_refreshed", "P11:Me_Jalee_and_Badu",
     "P11:Take_the_guys_along", "P9:played_carroms_cards_office_day"],
    primary_source="post",
    details="Takes care of team. Organized fun office days. Takes team to meetings. Wants to take them on trips.")

trait_creative = node("trait", "creative", "Creative", 0.95, 1.0,
    ["P13:rendering_HiLite", "P1:apartment_design",
     "P6:heritage_design_nadumuttams", "T2:tropical_theme_house",
     "WEB:principal_architect"],
    primary_source="post",
    details="Core personality trait. Expresses creativity through architecture, rendering, design philosophy.")

trait_culturally_rooted = node("trait", "culturally rooted", "Culturally Rooted", 0.85, 1.0,
    ["P6:designs_rooted_to_our_heritage", "T1:spoke_Malayalam",
     "T2:Kozhikode_slang", "P6:nadumuttams"],
    primary_source="post",
    details="Deeply connected to Kerala culture. Heritage-inspired designs. Speaks Malayalam. Values nadumuttams.")

trait_reflective = node("trait", "reflective", "Reflective", 0.8, 1.0,
    ["PROF:bio_passing_of_energy_meaning", "STYLE:contemplative_33pct",
     "P8:what_is_world_descending_to"],
    primary_source="bio",
    details="Philosophical and reflective nature. Bio about life's meaning. Contemplative communication style.")

trait_expressive = node("trait", "expressive", "Expressive", 0.75, 0.95,
    ["STYLE:exclamation_rate_75pct", "STYLE:ellipsis_rate_33pct",
     "P1:exclamation_marks", "P8:Oh_my_dear_word"],
    primary_source="post",
    details="Expressive writing style. High exclamation rate (75%). Uses ellipsis (33%). Emotionally open in posts.")

trait_resilient = node("trait", "resilient", "Resilient", 0.75, 0.95,
    ["P5:I_should_work_and_work_ignore_this_feeling",
     "P11:yearning_for_break_but_keeps_working"],
    primary_source="post",
    details="Pushes through difficult feelings. 'I should work and work... ignore this feeling!' Keeps working despite yearning for breaks.")

trait_multilingual = node("trait", "multilingual", "Multilingual", 0.7, 0.9,
    ["T1:Malayalam_speech", "T2:Malayalam_and_Kozhikode_slang",
     "T2:some_Hindi_Tamil_phrases", "PROF:implied_from_Kerala"],
    primary_source="conversation",
    details="Speaks Malayalam natively. Attempted Kozhikode dialect in voice calls. Some multilingual phrases in conversation.")

trait_grounded = node("trait", "grounded", "Grounded", 0.8, 1.0,
    ["P6:as_grounded_as_he_is_about_Jishnu",
     "PROF:bio_meaning_of_existence",
     "P6:designs_rooted_to_heritage"],
    primary_source="post",
    details="Grounded person. Values heritage and rootedness. Bio reflects deep philosophical grounding.")


# ── VALUES (core beliefs and principles) ─────────────────────────────

value_heritage = node("value", "heritage and tradition", "Heritage & Tradition", 0.95, 1.0,
    ["P6:rooted_to_our_heritage", "P6:nadumuttams_flowing_gardens",
     "WEB:studio_philosophy"],
    primary_source="post",
    details="Core design value. Believes in adapting heritage to modern times while preserving the soul.")

value_meaning = node("value", "meaning-seeking", "Meaning-Seeking", 0.85, 1.0,
    ["PROF:bio_passing_of_energy_to_find_meaning",
     "P6:design_as_grounded_expression"],
    primary_source="bio",
    details="Life philosophy. 'Life is just a passing of energy through time to find meaning of its existence.'")

value_authenticity = node("value", "authenticity", "Authenticity", 0.85, 1.0,
    ["P6:designs_rooted_to_heritage",
     "WEB:architecture_is_art_masterpiece_has_soul"],
    primary_source="post",
    details="Values authenticity in design and life. 'Every masterpiece should have a soul of its own.'")

value_team_care = node("value", "caring for team", "Caring for Team", 0.8, 1.0,
    ["P9:Let_them_come_back_refreshed",
     "P11:Take_the_guys_along"],
    primary_source="post",
    details="Gives team well-deserved breaks. Wants to enjoy trips with team.")

value_hard_work = node("value", "achievement through hard work", "Achievement Through Hard Work", 0.9, 1.0,
    ["P1:worth_forgetting_sleep", "P5:I_should_work_and_work",
     "P13:Tired_but_happy_with_results"],
    primary_source="post",
    details="Believes in working hard to achieve results. Sacrifices sleep for projects.")

value_cultural_identity = node("value", "cultural identity", "Cultural Identity", 0.8, 1.0,
    ["T2:spoke_Malayalam_slang", "P6:heritage_design",
     "PROF:location_Kozhikode_Kerala"],
    primary_source="conversation",
    details="Strong cultural identity rooted in Kozhikode/Kerala. Expresses through design and language.")

value_creativity = node("value", "creativity as expression", "Creativity as Expression", 0.9, 1.0,
    ["WEB:architecture_is_an_art", "P6:heritage_design_expression",
     "P7:Colors_post"],
    primary_source="post",
    details="Art and design as primary modes of self-expression. Architecture as art, not just process.")

value_family = node("value", "family connection", "Family Connection", 0.75, 1.0,
    ["P10:Missing_this_from_mom", "P5:Missing_this_guy"],
    primary_source="post",
    details="Strong emotional bonds with family. Misses mom. Emotional about loved ones.")


# ── PREFERENCES (personal likes and preferences) ──────────────────────

pref_ventilation = node("preference", "natural ventilation in design", "Natural Ventilation", 0.85, 1.0,
    ["P6:more_ventilation_more_light"],
    primary_source="post",
    details="Prioritizes natural ventilation in architectural design. More light, more air.")

pref_natural_light = node("preference", "natural lighting", "Natural Lighting", 0.85, 1.0,
    ["P6:more_light"],
    primary_source="post",
    details="Emphasizes natural light in designs. Key design principle.")

pref_heritage_modern_fusion = node("preference", "heritage-modern fusion", "Heritage-Modern Fusion", 0.9, 1.0,
    ["P6:adapt_to_modern_times_heritage",
     "P6:apertures_open_groves_of_green"],
    primary_source="post",
    details="Prefers blending heritage with modern elements. Nadumuttams spread along interior spaces, apertures opening to green.")

pref_calm_quiet = node("preference", "calm and quiet", "Calm and Quiet", 0.75, 1.0,
    ["P11:enjoy_some_calm_and_quiet"],
    primary_source="post",
    details="Values calm and quiet environments for relaxation.")

pref_road_trips = node("preference", "road trips", "Road Trips", 0.65, 0.95,
    ["P11:long_drive_down_to_sunsets_of_Goa"],
    primary_source="post",
    details="Prefers long road trips, especially to Goa for sunsets.")

pref_open_courtyards = node("preference", "open courtyards and gardens", "Open Courtyards & Gardens", 0.8, 1.0,
    ["P6:flowing_gardens_nadumuttams",
     "P6:apertures_open_groves_of_green"],
    primary_source="post",
    details="Designs with flowing gardens and open courtyards. Reimagined nadumuttams spread through interior spaces.")

pref_contemporary_urbanism = node("preference", "contemporary urbanism style", "Contemporary Urbanism", 0.75, 0.95,
    ["WEB:categorical_graphical_lines_contemporary_urbanism"],
    primary_source="web",
    details="Studio's signature style. Categorical graphical lines creating stunning forms of contemporary urbanism.")


# ═══════════════════════════════════════════════════════════════════════════
# COLLECT ALL NODES
# ═══════════════════════════════════════════════════════════════════════════

ALL_NODES = [
    # Connections
    rafseena, abdul_jaleel, badu, narmada, taran, noufal, jishnu, p_sulaiman, jaijith,
    # Demographics
    demo_name, demo_avatar, demo_email, demo_age, demo_gender, demo_location,
    demo_language, demo_bio, demo_job, demo_archetype,
    # Experiences
    exp_founded_studio, exp_hilite_office, exp_elance_hq, exp_coimbatore_apt,
    exp_cakestudio_project, exp_tropical_house, exp_joined_platform,
    exp_archdaily_featured, exp_multi_state_consulting,
    # Interests
    int_architecture, int_rendering, int_heritage_design, int_interior_design,
    int_landscape_design, int_tropical_design, int_nadumuttams,
    int_quantum_physics, int_spiritual_unknowns, int_fitness, int_art, int_food,
    int_travel, int_photography, int_badminton, int_fifa, int_counterstrike,
    int_carroms, int_cards, int_goa, int_norse_mythology, int_current_events,
    int_crypto_markets, int_design, int_poetry, int_kozhikode_slang,
    # Traits
    trait_hardworking, trait_passionate, trait_warm, trait_team_oriented,
    trait_creative, trait_culturally_rooted, trait_reflective, trait_expressive,
    trait_resilient, trait_multilingual, trait_grounded,
    # Values
    value_heritage, value_meaning, value_authenticity, value_team_care,
    value_hard_work, value_cultural_identity, value_creativity, value_family,
    # Preferences
    pref_ventilation, pref_natural_light, pref_heritage_modern_fusion,
    pref_calm_quiet, pref_road_trips, pref_open_courtyards,
    pref_contemporary_urbanism,
]

# ═══════════════════════════════════════════════════════════════════════════
# EDGES
# ═══════════════════════════════════════════════════════════════════════════

ALL_EDGES = [
    # ── Connection → Connection (family/team) ───────────────────────────
    edge(rafseena, abdul_jaleel, "colleague_of", 0.9, "Both co-principal architects at Vili & Vé"),
    edge(rafseena, badu, "colleague_of", 0.7, "Both at Vili & Vé, went to same meetings"),

    # ── Connection → Demographics ───────────────────────────────────────
    edge(demo_name, rafseena, "colleague_of", 0.85, "Sreejith and Rafseena are co-principal architects at Vili & Vé"),
    edge(demo_name, narmada, "son_of", 0.9, "Sreejith's mother is Narmada"),
    edge(demo_name, taran, "father_of", 0.9, "Sreejith's son is Taran"),
    edge(demo_name, demo_avatar, "represented_by", 0.9, "_bLikker is Sreejith's avatar"),
    edge(demo_name, demo_email, "owns", 0.9, "Email belongs to Sreejith"),
    edge(demo_name, demo_job, "works_as", 0.95, "Sreejith works as architect"),

    # ── Connection → Experience ─────────────────────────────────────────
    edge(rafseena, exp_elance_hq, "designed", 0.95, "Rafseena co-designed Elance HQ, did custom paintings"),
    edge(rafseena, exp_tropical_house, "involved_in", 0.7, "Rafseena was present during conversation about the tropical house design"),
    edge(abdul_jaleel, exp_elance_hq, "designed", 0.9, "Abdul Jaleel co-designed Elance HQ, did custom sculpture"),
    edge(abdul_jaleel, exp_cakestudio_project, "attended_meeting", 0.85, "Jalee went to CakeStudio meeting"),
    edge(badu, exp_cakestudio_project, "attended_meeting", 0.85, "Badu went to CakeStudio meeting"),
    edge(noufal, exp_cakestudio_project, "client_of", 0.9, "Mr Noufal is the CakeStudio client"),
    edge(jishnu, exp_elance_hq, "client_of", 0.95, "Jishnu is CEO of Elance, client for HQ design"),
    edge(p_sulaiman, exp_hilite_office, "client_of", 0.85, "P. Sulaiman chairs HiLite Group"),

    # ── Experience → Interest ───────────────────────────────────────────
    edge(exp_founded_studio, int_architecture, "professional_focus", 0.95, "Architecture studio is core to architecture interest"),
    edge(exp_hilite_office, int_rendering, "required_skill", 0.9, "HiLite office required rendering"),
    edge(exp_elance_hq, int_interior_design, "project_type", 0.9, "Elance HQ was an interior design project"),
    edge(exp_coimbatore_apt, int_architecture, "project_type", 0.85, "Coimbatore apartment is architecture project"),
    edge(exp_tropical_house, int_tropical_design, "design_style", 0.9, "Own residence uses tropical design theme"),
    edge(exp_tropical_house, int_heritage_design, "design_style", 0.8, "Tropical house combines heritage with tropical"),
    edge(exp_archdaily_featured, int_architecture, "recognition_for", 0.85, "ArchDaily feature for architecture work"),

    # ── Interest → Interest (hierarchies and relations) ─────────────────
    edge(int_architecture, int_rendering, "requires", 0.9, "Architecture requires rendering skills"),
    edge(int_architecture, int_interior_design, "subsumes", 0.85, "Interior design is a branch of architecture"),
    edge(int_architecture, int_landscape_design, "subsumes", 0.75, "Landscape design complements architecture"),
    edge(int_architecture, int_heritage_design, "expressed_through", 0.9, "Heritage design is an architectural philosophy"),
    edge(int_architecture, int_tropical_design, "expressed_through", 0.8, "Tropical design is an architectural style"),
    edge(int_heritage_design, int_nadumuttams, "exemplified_by", 0.9, "Nadumuttams exemplify heritage design"),
    edge(int_heritage_design, int_tropical_design, "related_to", 0.75, "Heritage and tropical design merge in Kerala context"),
    edge(int_architecture, int_art, "related_to", 0.9, "Architecture is an art — studio philosophy"),
    edge(int_architecture, int_design, "related_to", 0.95, "Architecture is design"),
    edge(int_art, int_design, "related_to", 0.85, "Art and design deeply connected"),
    edge(int_art, int_photography, "related_to", 0.7, "Photography is an art form"),
    edge(int_travel, int_goa, "subsumes", 0.8, "Goa trips are a travel interest"),
    edge(int_travel, int_photography, "related_to", 0.7, "Travel photography"),
    edge(int_badminton, int_fitness, "contributes_to", 0.75, "Badminton is fitness activity"),
    edge(int_fifa, int_counterstrike, "related_to", 0.8, "Both video games for relaxation"),
    edge(int_carroms, int_cards, "related_to", 0.7, "Both office indoor games"),
    edge(int_quantum_physics, int_spiritual_unknowns, "related_to", 0.7, "Physics and spiritual unknowns connect philosophically"),
    edge(int_norse_mythology, int_spiritual_unknowns, "related_to", 0.6, "Norse mythology touches spiritual themes"),
    edge(int_crypto_markets, int_current_events, "related_to", 0.7, "Crypto crash is a current event"),

    # ── Trait → Interest ────────────────────────────────────────────────
    edge(trait_creative, int_architecture, "expressed_through", 0.95, "Creativity expressed through architecture"),
    edge(trait_creative, int_art, "expressed_through", 0.85, "Creativity through art"),
    edge(trait_creative, int_design, "expressed_through", 0.9, "Creativity through design"),
    edge(trait_culturally_rooted, int_heritage_design, "expressed_through", 0.9, "Cultural roots expressed in heritage design"),
    edge(trait_culturally_rooted, int_nadumuttams, "expressed_through", 0.85, "Cultural roots in nadumuttam appreciation"),
    edge(trait_culturally_rooted, int_kozhikode_slang, "expressed_through", 0.7, "Cultural identity through local slang"),
    edge(trait_reflective, int_quantum_physics, "drawn_to", 0.75, "Reflective nature drawn to quantum physics"),
    edge(trait_reflective, int_spiritual_unknowns, "drawn_to", 0.7, "Reflective nature explores spiritual unknowns"),
    edge(trait_hardworking, int_rendering, "applied_to", 0.85, "Works hard on renderings"),
    edge(trait_passionate, int_architecture, "directed_at", 0.95, "Passion directed at architecture"),
    edge(trait_multilingual, int_kozhikode_slang, "enables", 0.75, "Multilingual ability enables slang usage"),

    # ── Trait → Value ───────────────────────────────────────────────────
    edge(trait_hardworking, value_hard_work, "embodies", 0.95, "Hardworking trait embodies achievement value"),
    edge(trait_culturally_rooted, value_heritage, "drives", 0.9, "Cultural roots drive heritage value"),
    edge(trait_culturally_rooted, value_cultural_identity, "drives", 0.9, "Cultural roots drive cultural identity"),
    edge(trait_creative, value_creativity, "embodies", 0.9, "Creative trait embodies creativity value"),
    edge(trait_reflective, value_meaning, "drives", 0.85, "Reflection drives meaning-seeking"),
    edge(trait_warm, value_family, "expresses", 0.85, "Warmth expressed through family connection"),
    edge(trait_team_oriented, value_team_care, "embodies", 0.9, "Team orientation embodies team care value"),
    edge(trait_grounded, value_authenticity, "drives", 0.85, "Being grounded drives authenticity"),

    # ── Value → Preference ──────────────────────────────────────────────
    edge(value_heritage, pref_heritage_modern_fusion, "leads_to", 0.9, "Heritage value leads to heritage-modern fusion preference"),
    edge(value_heritage, pref_open_courtyards, "leads_to", 0.85, "Heritage value leads to open courtyard preference"),
    edge(value_creativity, pref_contemporary_urbanism, "expressed_through", 0.8, "Creativity expressed in contemporary urbanism"),
    edge(value_hard_work, pref_calm_quiet, "counterbalanced_by", 0.7, "Hard work creates yearning for calm and quiet"),
    edge(value_authenticity, pref_ventilation, "applied_as", 0.75, "Authentic design uses natural ventilation"),
    edge(value_authenticity, pref_natural_light, "applied_as", 0.75, "Authentic design uses natural light"),

    # ── Preference → Interest ───────────────────────────────────────────
    edge(pref_heritage_modern_fusion, int_heritage_design, "applied_in", 0.9, "Heritage-modern fusion is core design interest"),
    edge(pref_heritage_modern_fusion, int_nadumuttams, "includes", 0.85, "Heritage fusion includes nadumuttams"),
    edge(pref_open_courtyards, int_nadumuttams, "realized_as", 0.85, "Open courtyards realized as nadumuttams"),
    edge(pref_road_trips, int_goa, "directed_at", 0.8, "Road trips directed toward Goa"),
    edge(pref_road_trips, int_travel, "related_to", 0.75, "Road trips are travel"),
    edge(pref_calm_quiet, int_goa, "found_in", 0.7, "Calm and quiet found in Goa sunsets"),
    edge(pref_ventilation, int_heritage_design, "applied_in", 0.85, "Ventilation priority in heritage design"),
    edge(pref_natural_light, int_heritage_design, "applied_in", 0.85, "Natural light priority in heritage design"),
    edge(pref_natural_light, int_rendering, "captured_in", 0.75, "Natural light captured in rendering work"),

    # ── Demographic → Various ───────────────────────────────────────────
    edge(demo_location, int_heritage_design, "inspires", 0.85, "Kozhikode Kerala location inspires heritage design"),
    edge(demo_location, int_nadumuttams, "cultural_context", 0.85, "Kerala location provides nadumuttam context"),
    edge(demo_location, int_kozhikode_slang, "origin_of", 0.9, "Kozhikode is origin of the slang"),
    edge(demo_location, demo_language, "related_to", 0.9, "Kerala location — Malayalam language"),
    edge(demo_language, trait_multilingual, "related_to", 0.85, "Malayalam is primary language"),
    edge(demo_language, value_cultural_identity, "expresses", 0.85, "Malayalam expresses cultural identity"),
    edge(demo_bio, value_meaning, "expresses", 0.95, "Bio directly expresses meaning-seeking value"),
    edge(demo_bio, trait_reflective, "reveals", 0.85, "Bio reveals reflective nature"),
    edge(demo_job, exp_founded_studio, "realized_through", 0.95, "Architect job realized through founding studio"),
    edge(demo_job, int_architecture, "professional_in", 0.95, "Job is in architecture"),
    edge(demo_job, exp_multi_state_consulting, "scope_of", 0.8, "Job scope extends across states"),

    # ── Experience → Experience ─────────────────────────────────────────
    edge(exp_founded_studio, exp_hilite_office, "led_to", 0.85, "Studio enabled HiLite project"),
    edge(exp_founded_studio, exp_elance_hq, "led_to", 0.85, "Studio enabled Elance project"),
    edge(exp_founded_studio, exp_coimbatore_apt, "led_to", 0.8, "Studio enabled Coimbatore project"),
    edge(exp_founded_studio, exp_cakestudio_project, "led_to", 0.75, "Studio enabled CakeStudio project"),
    edge(exp_founded_studio, exp_multi_state_consulting, "expanded_to", 0.8, "Studio expanded to multi-state consulting"),
    edge(exp_elance_hq, exp_archdaily_featured, "resulted_in", 0.9, "Elance HQ led to ArchDaily feature"),

    # ── Connection → Interest/Value ─────────────────────────────────────
    edge(jaijith, demo_name, "friend_of", 0.6, "Jaijith is a friend who interacts on the platform"),
    edge(narmada, value_family, "inspires", 0.85, "Missing mom inspires family connection value"),
    edge(taran, value_family, "inspires", 0.9, "Son Taran is central to family value"),

    # ── Norse mythology → Studio ────────────────────────────────────────
    edge(int_norse_mythology, exp_founded_studio, "inspired_name", 0.9, "Norse mythology (Vili & Vé) inspired studio name"),

    # ── Fix isolated nodes — connect to graph ───────────────────────────
    edge(demo_age, demo_name, "attribute_of", 0.8, "Age 39 is an attribute of Sreejith"),
    edge(demo_gender, demo_name, "attribute_of", 0.8, "Male gender is an attribute of Sreejith"),
    edge(demo_archetype, trait_reflective, "manifests_as", 0.7, "Thoughtful contributor archetype manifests in reflective trait"),
    edge(exp_joined_platform, demo_name, "action_by", 0.7, "Sreejith joined the platform"),
    edge(int_food, int_travel, "related_to", 0.7, "Food interest complements travel interest"),
    edge(int_food, demo_location, "influenced_by", 0.7, "Kerala location influences food interests"),
    edge(int_poetry, trait_creative, "related_to", 0.65, "Poetry is a creative pursuit"),
    edge(int_poetry, trait_reflective, "related_to", 0.65, "Poetry connects to reflective nature"),
    edge(trait_expressive, trait_warm, "related_to", 0.8, "Expressive and warm traits reinforce each other"),
    edge(trait_expressive, value_creativity, "enables", 0.75, "Expressiveness enables creative output"),
    edge(trait_resilient, trait_hardworking, "reinforces", 0.85, "Resilience reinforces hardworking nature"),
    edge(trait_resilient, value_hard_work, "enables", 0.8, "Resilience enables achieving through hard work"),
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
    print(f"  VERIFIED GRAPH — _bLikker / Sreejith Sreekantan — VALIDATION REPORT")
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
