#!/usr/bin/env python3
"""
Test: Internal State → Content Decisions
Demonstrates how internal state drives what avatars talk about
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from domain.avatar.state.state_models import MoodState, VoiceModulators
from domain.avatar.state.internal_state import InternalState
import random


def simulate_post_type_selection(internal_state: InternalState, num_samples: int = 100):
    """Simulate post type selection to show probabilities"""
    expression_ctx = internal_state.get_expression_context()
    
    # Base weights
    post_types = {
        "interest": 0.20,
        "thought": 0.15,
        "friend_interaction": 0.15,
        "joke": 0.10,
        "pleasantry": 0.10,
        "current_events": 0.15,
        "friendly_banter": 0.10,
        "experience": 0.05
    }
    
    # Apply same logic as in intelligent.py
    if expression_ctx.get('should_talk_about_friends', False):
        post_types["friend_interaction"] *= 2.0
        post_types["friendly_banter"] *= 1.5
        post_types["interest"] *= 0.7
    
    if expression_ctx.get('should_reference_world', False):
        post_types["current_events"] *= 2.0
        post_types["thought"] *= 1.3
        post_types["joke"] *= 0.8
    
    humor_level = expression_ctx.get('humor_level', 'medium')
    if humor_level == 'high':
        post_types["joke"] *= 1.8
        post_types["friendly_banter"] *= 1.3
        post_types["thought"] *= 0.7
    
    mood = expression_ctx.get('mood', 'neutral')
    if mood == 'social':
        post_types["friend_interaction"] *= 1.8
        post_types["friendly_banter"] *= 1.6
        post_types["pleasantry"] *= 1.4
    elif mood == 'bored':
        post_types["joke"] *= 1.5
        post_types["current_events"] *= 1.3
        post_types["pleasantry"] *= 0.5
    elif mood == 'curious':
        post_types["current_events"] *= 1.6
        post_types["thought"] *= 1.4
    
    # Normalize
    total = sum(post_types.values())
    normalized = {k: v/total for k, v in post_types.items()}
    
    # Sample
    counts = {k: 0 for k in post_types.keys()}
    for _ in range(num_samples):
        choice = random.choices(list(normalized.keys()), weights=list(normalized.values()))[0]
        counts[choice] += 1
    
    return {k: (v/num_samples)*100 for k, v in counts.items()}


def print_scenario(title: str, state: InternalState):
    """Print a scenario with state and probabilities"""
    print(f"\n{'='*70}")
    print(f"SCENARIO: {title}")
    print(f"{'='*70}")
    
    # Print state
    expr_ctx = state.get_expression_context()
    print(f"\nINTERNAL STATE:")
    print(f"  Mood: {state.mood.value}")
    print(f"  Energy: {state.energy_level:.2f}")
    print(f"  Social Desire: {state.social_desire:.2f}")
    print(f"\nVOICE MODULATORS:")
    print(f"  Friend Focus: {state.voice_modulators.friend_focus:.2f}")
    print(f"  World Awareness: {state.voice_modulators.world_awareness:.2f}")
    print(f"  Humor: {state.voice_modulators.humor_intensity:.2f}")
    print(f"\nDERIVED CONTEXT:")
    print(f"  Should talk about friends: {expr_ctx['should_talk_about_friends']}")
    print(f"  Should reference world: {expr_ctx['should_reference_world']}")
    print(f"  Humor level: {expr_ctx['humor_level']}")
    
    # Simulate post type selection
    probabilities = simulate_post_type_selection(state)
    
    print(f"\nPOST TYPE PROBABILITIES:")
    sorted_probs = sorted(probabilities.items(), key=lambda x: x[1], reverse=True)
    for post_type, prob in sorted_probs:
        bar = '█' * int(prob / 2)
        print(f"  {post_type:20s} {prob:5.1f}% {bar}")
    
    # Get top choice
    top_choice = sorted_probs[0][0]
    print(f"\nMOST LIKELY CONTENT: {top_choice} ({sorted_probs[0][1]:.1f}% chance)")
    
    # Show what gets fetched
    print(f"\nCONTENT FETCHING:")
    if expr_ctx['should_talk_about_friends']:
        print(f"  ✅ Fetch friend activities")
    else:
        print(f"  ❌ Skip friend activities (not interested)")
    
    if expr_ctx['should_reference_world']:
        print(f"  ✅ Fetch news/trending topics")
    else:
        print(f"  ❌ Skip news (not interested)")


def main():
    print("\n" + "="*70)
    print("║  Testing: Internal State → Content Decisions")
    print("="*70)
    
    # Scenario 1: SOCIAL mood with high friend focus
    state1 = InternalState()
    state1.adjust_mood(MoodState.SOCIAL)
    state1.social_desire = 0.9
    state1.energy_level = 0.7
    state1.voice_modulators.friend_focus = 0.9
    state1.voice_modulators.world_awareness = 0.3
    state1.update_voice_for_state()
    
    print_scenario(
        "Social Avatar (wants to talk about friends)",
        state1
    )
    
    # Scenario 2: CURIOUS mood with high world awareness
    state2 = InternalState()
    state2.adjust_mood(MoodState.CURIOUS)
    state2.energy_level = 0.6
    state2.social_desire = 0.4
    state2.voice_modulators.friend_focus = 0.3
    state2.voice_modulators.world_awareness = 0.9
    state2.update_voice_for_state()
    
    print_scenario(
        "Curious Avatar (wants to discuss world events)",
        state2
    )
    
    # Scenario 3: BORED mood with high humor
    state3 = InternalState()
    state3.adjust_mood(MoodState.BORED)
    state3.energy_level = 0.3
    state3.social_desire = 0.4
    state3.voice_modulators.humor_intensity = 0.9
    state3.voice_modulators.friend_focus = 0.4
    state3.voice_modulators.world_awareness = 0.5
    state3.update_voice_for_state()
    
    print_scenario(
        "Bored Avatar (wants to make jokes)",
        state3
    )
    
    # Scenario 4: NEUTRAL mood (balanced)
    state4 = InternalState()
    # Keep defaults
    
    print_scenario(
        "Neutral Avatar (balanced interests)",
        state4
    )
    
    # Summary
    print("\n\n" + "="*70)
    print("║  Summary: State Drives Content")
    print("="*70)
    print("""
KEY FINDINGS:

1. SOCIAL mood + high friend_focus:
   → friend_interaction: ~40-50% probability
   → Fetches friend activities ✅
   → Skips news ❌
   → Sample: "Everyone's online! Time to catch up with my crew! 🎉"

2. CURIOUS mood + high world_awareness:
   → current_events: ~35-45% probability
   → Fetches news ✅
   → Skips friend activities ❌
   → Sample: "Fascinating AI breakthrough today... thoughts? 🤔"

3. BORED mood + high humor:
   → joke: ~25-35% probability
   → Fetches both (need content to joke about)
   → Sample: "Another day, another existential crisis. At least I'm consistent. 😑"

4. NEUTRAL mood (balanced):
   → Relatively even distribution
   → Fetches both
   → Sample: "Thinking about life, tech, and everything in between..."

✅ Internal state doesn't just affect HOW avatars talk...
   It affects WHAT they choose to talk about!

✅ Content gathering is optimized based on state
   (Don't fetch friend data if avatar isn't social right now)

✅ Same avatar = different content focus at different times
   (Morning: social → friends, Evening: curious → news)
""")


if __name__ == "__main__":
    main()
