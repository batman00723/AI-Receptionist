# Title:
# Handle consecutive booking attempts after an active booking exists.

# Current:
# booking_data is cleared by setting it to None, which causes reducer issues on subsequent bookings.

# Future solution:
# Separate transient booking workflow state from persistent appointment state, or replace the reducer with explicit state replacement.





# Handle repeated booking attempts when an active appointment already exists.

# Current behavior:
# - Booking succeeds.
# - Starting another booking with the same patient can lead to inconsistent state.

# Expected behavior:
# - Detect existing active appointment.
# - Ask user whether they want to cancel/reschedule or create an additional appointment (depending on business rules).


# Future roadmap:
# - Voice calling support
# - LiveKit integration
# - Human handoff
# - Multi-clinic support


# 3. Semantic Cache Improvement (Future)

# Current semantic cache is query-embedding based.
# To avoid incorrect cache hits from conversational queries,
# cache retrieval is restricted to longer queries (8+ words).

# Long-Term Plan:
#
# Phase 1:
# - Collect real user queries and responses for 1-2 months.
# - Store query frequency statistics.
# - Identify FAQs that are repeatedly asked and have stable answers.
#
# Examples:
# - What are your clinic timings?
# - Where is the clinic located?
# - Do you offer root canal treatment?
#
# Avoid caching conversational queries:
# - yes
# - no
# - okay
# - thanks
# - how much?
# - what about Sunday?
#
# Phase 2:
# - Build a curated FAQ cache from frequently repeated questions.
# - Remove one-off and context-dependent entries.
#
# Phase 3:
# - Switch semantic cache to read-heavy mode.
# - Only approved FAQ responses are allowed into cache.
# - New cache entries require manual approval or frequency threshold.
#
# Goal:
# Use semantic cache only for high-confidence,
# context-independent FAQ responses while routing all
# conversational and context-dependent queries through RAG.