#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: "Make avatars intelligent using Graph RAG. Each avatar should be backed by a knowledge graph built from real-world (Sense) data. Use LLM with Graph RAG to propel avatar behavior including chat responses, post generation, and matching. Add provision for external platform integrations (Spotify, YouTube, Instagram, Facebook, Amazon, Netflix, Goodreads, Strava) as placeholders to enrich the graph."

backend:
  - task: "Create Graph Builder Module"
    implemented: true
    working: "NA"
    file: "/app/backend/graph_builder.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Created graph_builder.py module with functions to build knowledge graphs from user profiles, extract entities from text using LLM, enrich graphs from posts and interactions, and add external platform data"

  - task: "Create Graph RAG Module"
    implemented: true
    working: "NA"
    file: "/app/backend/graph_rag.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Created graph_rag.py module with functions to retrieve user context, calculate compatibility, find similar users, generate avatar personality profiles, and get conversation context"

  - task: "Create Intelligent Avatar Module"
    implemented: true
    working: "NA"
    file: "/app/backend/intelligent_avatar.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Created intelligent_avatar.py module with AI-powered avatar post generation, chat response generation, bio generation, conversation starters, and match explanations using Graph RAG"

  - task: "Add Avatar Intelligence Routes"
    implemented: true
    working: "NA"
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Added API routes: /avatar/generate-post, /avatar/chat-response, /avatar/generate-bio, /avatar/conversation-starters, /avatar/match-explanation"

  - task: "Add Graph Building Routes"
    implemented: true
    working: "NA"
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Added routes: /graph/build-from-profile, /graph/enrich-from-post, /graph/enrich-from-interaction, /graph/context, /graph/compatibility, /graph/similar-users"

  - task: "Add External Platform Integration Routes"
    implemented: true
    working: "NA"
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Added placeholder integration routes: /integrations (GET), /integrations/connect (POST), /integrations/disconnect (POST), /integrations/sync (POST) for Spotify, YouTube, Instagram, Facebook, Amazon, Netflix, Goodreads, Strava"

  - task: "Auto Graph Building on Profile Update"
    implemented: true
    working: "NA"
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Updated /profile (PUT) endpoint to automatically rebuild knowledge graph when user updates their Sense profile"

  - task: "Graph Enrichment on Post Creation"
    implemented: true
    working: "NA"
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Updated /profile/posts (POST) endpoint to enrich knowledge graph from real post content using LLM entity extraction"

  - task: "Auto Graph Building on User Registration"
    implemented: true
    working: "NA"
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Updated /auth/session-data endpoint to automatically build initial knowledge graph for new users during registration"

frontend:
  - task: "Update Integrations Page"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/pages/IntegrationsPage.jsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Updated IntegrationsPage to work with new backend API, added connect and sync functionality for external platforms"

metadata:
  created_by: "main_agent"
  version: "1.0"
  test_sequence: 0
  run_ui: false

test_plan:
  current_focus:
    - "Graph Builder Module"
    - "Graph RAG Module"
    - "Intelligent Avatar Module"
    - "Avatar Intelligence Routes"
    - "External Platform Integration Routes"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: "Implemented Phase 1 of intelligent avatar system with Graph RAG. Created 3 new backend modules (graph_builder.py, graph_rag.py, intelligent_avatar.py) and integrated them into server.py. Added 15+ new API routes for avatar intelligence, graph management, and external platform integrations. Automatic graph building/enrichment is now triggered on profile updates, post creation, and user registration. Ready for backend testing."
  - agent: "testing"
    message: "Completed comprehensive backend testing of Graph RAG system. Fixed critical bug in GraphRAG module (singular/plural node type mapping). All core functionality working: graph building (31 nodes created), avatar intelligence (post/bio/chat generation), external integrations (Spotify/YouTube/Instagram), and Graph RAG queries. Azure OpenAI integration working correctly. System ready for production use."