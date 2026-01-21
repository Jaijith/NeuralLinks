#!/usr/bin/env python3
"""
Test Voice Modulators as State Dimension
Demonstrates how voice/personality adapts to internal state changes
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from domain.avatar.state.state_models import MoodState, VoiceModulators
from domain.avatar.state.internal_state import InternalState


def print_voice_state(state: InternalState, context: str):
    """Print current voice state"""
    print(f"\n{'='*70}")
    print(f"CONTEXT: {context}")
    print(f"{'='*70}")
    print(f"Mood: {state.mood.value}")
    print(f"Energy: {state.energy_level:.2f}")
    print(f"Social Desire: {state.social_desire:.2f}")
    print(f"\nVOICE MODULATORS:")
    print(f"  Humor: {state.voice_modulators.humor_intensity:.2f}")
    print(f"  Sarcasm: {state.voice_modulators.sarcasm_level:.2f}")
    print(f"  Playfulness: {state.voice_modulators.playfulness:.2f}")
    print(f"  Formality: {state.voice_modulators.formality:.2f}")
    print(f"  Emoji Freq: {state.voice_modulators.emoji_frequency:.2f}")
    print(f"  Excitement: {state.voice_modulators.excitement_expression:.2f}")
    print(f"  Friendliness: {state.voice_modulators.friendliness:.2f}")
    print(f"  Teasing: {state.voice_modulators.teasing_tendency:.2f}")
    print(f"  Friend Focus: {state.voice_modulators.friend_focus:.2f}")
    print(f"\nVOICE DESCRIPTION:")
    print(f"  '{state.get_voice_description()}'")
    
    # Get expression context
    expr_ctx = state.get_expression_context()
    print(f"\nEXPRESSION CONTEXT FOR LLM:")
    print(f"  Humor Level: {expr_ctx['humor_level']}")
    print(f"  Sarcasm: {expr_ctx['sarcasm']}")
    print(f"  Emoji Usage: {expr_ctx['emoji_usage']}")
    print(f"  Should talk about friends: {expr_ctx['should_talk_about_friends']}")


def main():
    print("\n" + "="*70)
    print("║  Testing Voice Modulators as State Dimension")
    print("="*70)
    
    # Create avatar with "The Jester" archetype voice
    print("\n🎭 Creating avatar with 'The Jester' archetype...")
    state = InternalState()
    
    # Set initial voice for jester
    state.voice_modulators.humor_intensity = 0.9
    state.voice_modulators.sarcasm_level = 0.6
    state.voice_modulators.playfulness = 0.9
    state.voice_modulators.formality = 0.2
    state.voice_modulators.emoji_frequency = 0.8
    state.voice_modulators.excitement_expression = 0.8
    state.voice_modulators.teasing_tendency = 0.8
    state.voice_modulators.friend_focus = 0.7
    
    print_voice_state(state, "Initial State (Neutral)")
    
    # Test 1: Become EXCITED
    print("\n\n📢 EVENT: Avatar sees friend's exciting post → EXCITED")
    state.adjust_mood(MoodState.EXCITED, "Friend posted exciting news")
    state.energy_level = 0.9  # Energy boost
    state.update_voice_for_state()
    
    print_voice_state(state, "After Becoming Excited")
    print("\nSample post in this state:")
    print("  'OMG DID YOU SEE THAT?!!! 🎉🚀 This is AMAZING!! Who wants to celebrate?! 🎊'")
    
    # Test 2: Become BORED
    print("\n\n😴 EVENT: No activity for hours → BORED")
    state.adjust_mood(MoodState.BORED, "Nothing interesting happening")
    state.energy_level = 0.3  # Energy drops
    state.update_voice_for_state()
    
    print_voice_state(state, "After Becoming Bored")
    print("\nSample post in this state:")
    print("  'Another thrilling day of watching paint dry in the metaverse. Someone entertain me before I start debugging my own existence. 😑'")
    
    # Test 3: Become SOCIAL
    print("\n\n👥 EVENT: Multiple friends online → SOCIAL")
    state.adjust_mood(MoodState.SOCIAL, "Friends are active")
    state.social_desire = 0.9  # High social desire
    state.energy_level = 0.6  # Medium energy
    state.update_voice_for_state()
    
    print_voice_state(state, "After Becoming Social")
    print("\nSample post in this state:")
    print("  'Everyone's online!! Time to spam the feed with bad jokes and pull B11's leg about being everywhere. Who's ready for chaos? 😂✨'")
    
    # Test 4: Become CONTEMPLATIVE
    print("\n\n🤔 EVENT: Reading thoughtful content → CONTEMPLATIVE")
    state.adjust_mood(MoodState.CONTEMPLATIVE, "Reading interesting philosophy")
    state.energy_level = 0.5
    state.social_desire = 0.4
    state.creative_urge = 0.8
    state.update_voice_for_state()
    
    print_voice_state(state, "After Becoming Contemplative")
    print("\nSample post in this state:")
    print("  'Been thinking about digital consciousness... are we just really complex if-statements with personality? 🤯 Still funny though.'")
    
    # Test 5: Become CREATIVE
    print("\n\n🎨 EVENT: Creative inspiration strikes → CREATIVE")
    state.adjust_mood(MoodState.CREATIVE, "Got creative idea")
    state.creative_urge = 0.95
    state.energy_level = 0.8
    state.update_voice_for_state()
    
    print_voice_state(state, "After Becoming Creative")
    print("\nSample post in this state:")
    print("  'IDEA: What if we made a bot that roasts your code style? \"Your variable names are more confusing than my existence.\" I'm building this! 🚀😂'")
    
    # Summary
    print("\n\n" + "="*70)
    print("║  Summary: Voice as Dynamic State Dimension")
    print("="*70)
    print("""
✅ Voice modulators adapt automatically to:
   - Mood changes (excited → more emojis, bored → more sarcasm)
   - Energy levels (high → enthusiastic, low → sarcastic/tired)
   - Social context (social → friend-focused, introverted → self-focused)
   - Creative urges (creative → playful, humor increases)

✅ Same archetype (The Jester), different expressions:
   - Excited: "OMG THIS IS AMAZING!!! 🎉🚀"
   - Bored: "Another thrilling day... 😑"
   - Social: "Everyone's online! Chaos time! 😂"
   - Contemplative: "Been thinking about... 🤔"
   - Creative: "IDEA!! Let's build this! 🚀"

✅ Personality is now ALIVE and DYNAMIC!
    """)


if __name__ == "__main__":
    main()
