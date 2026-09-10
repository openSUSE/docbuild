.. _agentic-workflow:

##################
Agentic Workflow
##################

This document describes the unified agentic workflow for docbuild development. It covers when to use each agent, what they do, and how they work together.

Overview
========

The docbuild agentic workflow runs in **OpenCode**, an interactive command-line environment. It consists of a primary orchestrator agent (:command:`docbuild`) and **5 specialized sub-agents** that work together to help you:

*   **Design** new features with sound architecture
*   **Write** code that matches the design
*   **Test** thoroughly with >95% coverage
*   **Document** with complete docstrings and guides
*   **Review** code for quality and safety

You interact with the primary agent by running :command:`docbuild` from your OpenCode shell, which then starts the OpenCode environment. Sub-agents are invoked via at-commands (e.g., :command:`@code-reviewer`) from within OpenCode to analyze files, branches, or pull requests.

The Primary Agent: :command:`docbuild`
======================================

The main entry point to the agentic workflow is the :command:`docbuild` command, which acts as the primary orchestrator.
In OpenCode, press :kbd:`Tab` to cycle through the list of available primary agents.

**Role:** Routes requests to specialized sub-agents and coordinates workflows.

**When to use:**

*   You have a complex task (e.g., "implement new feature", "fix critical bug")
*   You want agents to collaborate on a multi-step workflow
*   You need a summary report across multiple review passes

**What it does:**

1.  Interprets your request from the command line.
2.  Determines which sub-agents are needed.
3.  Delegates to code-reviewer, test-engineer, doc-writer, design-reviewer, etc. inside OpenCode.
4.  Aggregates results into a summary report.

**Example:**

.. code-block:: bash

    docbuild "implement caching for API responses"

    The docbuild agent would then coordinate the following workflow inside OpenCode:
      1. design-reviewer → "Review the caching architecture"
      2. code-reviewer → "Validate code matches design"
      3. test-engineer → "Run tests, check coverage"
      4. doc-writer → "Complete documentation"
      5. Aggregate results
      ↓
    Summary:
      ✅ Architecture: Approved (use @lru_cache, good!)
      ✅ Code quality: Matches design intent
      ✅ Coverage: 97% (no drops)
      ⚠️ Docs: Missing example in cache_ttl parameter

----

Quick Reference: Sub-Agent Invocation
=====================================

.. list-table::
   :header-rows: 1

   * - Command
     - Use Case
     - Context
   * - :command:`@code-reviewer <file|branch>`
     - Check if code matches its design intent
     - Context-aware
   * - :command:`@test-engineer <file|branch>`
     - Auto-run tests, analyze coverage
     - Context-aware
   * - :command:`@doc-writer <file|branch>`
     - Check docstrings & guide completeness
     - Context-aware
   * - :command:`@design-reviewer <file|branch>`
     - Holistic architecture review
     - Context-aware
   * - :command:`@pr-review <branch|PR-URL>`
     - Independent code quality check
     - Context-independent

----

The Sub-Agents
==============

1. Code Reviewer (Context-Aware)
--------------------------------

**Skills Used:** :file:`code-review.skill.md`, :file:`docbuild-guidelines.skill.md`

**Role:** Validates that your code matches its stated design intent and enforces quality standards.

**When to use:**

*   After writing code for a feature
*   You want to check if implementation matches your design
*   You need coverage analysis (>95% required)
*   You want feedback before running tests

**What it does:**

*   Compares code against stated feature intent
*   Flags code smells (duplication, complexity, poor naming)
*   Detects logical flaws and edge cases
*   Enforces >95% test coverage
*   **Flags coverage drops** (e.g., 99% → 98%)
*   Checks for YAGNI violations against the feature scope
*   Suggests simplifications

**Output Example:**

.. code-block:: text

    File: src/docbuild/cli/cache_api.py

    ✅ Code matches design intent
    ⚠️ Coverage drop detected: 99.5% → 98.7%
      → Missing tests for cache_miss() edge case

    🔴 Code smell: DRY violation
      → Lines 45-52 duplicate logic from lines 12-19
      → Suggestion: Extract to shared _get_cache_key() function

    🔴 Incomplete: TTL parameter documented but no example
      → See @doc-writer for docstring improvements

**Example Invocation:**

.. code-block:: text

    @code-reviewer src/docbuild/cli/cache_api.py
    @code-reviewer feature/caching  (analyzes all files in branch)

----

2. Test Engineer (Testing Expertise)
------------------------------------

**Skills Used:** :file:`pytest-expert.skill.md`, :file:`testing.skill.md`

**Role:** Ensures comprehensive test coverage and suggests advanced pytest patterns.

**When to use:**

*   After code changes (auto-runs tests)
*   You need coverage gap analysis
*   You want suggestions for parametrized tests
*   You need mocking advice
*   You want to interpret coverage reports

**What it does:**

*   **Auto-runs tests** after code changes (full suite by default)
*   Analyzes coverage reports (``--cov-report=term-missing``)
*   Flags coverage < 95% on new code
*   Suggests ``@pytest.mark.parametrize`` opportunities
*   Reviews fixture patterns & scope management
*   Flags flaky or incomplete tests
*   Advises on mocking (what to mock, what not to)

**Output Example:**

.. code-block:: text

    Tests run: 245 passed in 3.2s

    Coverage: 97.2% (good!)
      → docbuild/cli/cache_api.py: 95.5%
      → Missing coverage:
        - Line 67: cache_miss() error path (mock failure case)
        - Line 89: TTL expiry edge case (time.sleep() test)

    Parametrize opportunities:
      ✓ test_cache_ttl() could use @pytest.mark.parametrize
        → Current: 3 separate tests
        → Suggested: 1 parametrized test with 6 cases
        → Saves: ~40 lines of boilerplate

    Mocking feedback:
      ✓ Good: Mocking external API calls
      ⚠️ Review: fixture scope=function vs. session
        → Current uses session-scoped cache (persists across tests)
        → Risk: Test isolation if one test pollutes cache
        → Suggestion: function-scoped for isolation

**Example Invocation:**

.. code-block:: text

    @test-engineer src/docbuild/cli/cache_api.py
    @test-engineer feature/caching  (runs full test suite on branch)

----

3. Doc Writer (Documentation Completeness)
-------------------------------------------

**Skills Used:** :file:`doc-writer.skill.md`, :file:`documentation.skill.md`

**Role:** Ensures docstrings are complete and guides are updated.

**When to use:**

*   After code changes (docstrings need updates)
*   You modified public APIs
*   You want to check docstring completeness
*   You need to update Developer or User Guides

**What it does:**

*   Scans docstrings for missing elements:

    *   Parameter descriptions
    *   Return type documentation
    *   Exception (``raises``) documentation
    *   Examples (for complex/algorithmic functions)
*   Suggests complex function examples
*   Determines if changes need Developer Guide or User Guide updates
*   Validates Sphinx RST syntax
*   Checks for contradictions between code and docs

**Output Example:**

.. code-block:: text

    File: src/docbuild/cli/cache_api.py

    🔴 Incomplete docstrings:
      Line 45: get_cached_api_response()
        ✗ Missing: 'ttl' parameter description
        ✗ Missing: example for algorithm explanation
        ✗ Missing: 'CacheError' exception documentation

      Line 78: _cache_decorator()
        ✓ Has params, returns
        ✗ Missing: example showing usage pattern

    ✅ Good: Lines 12-30 have complete docstring with example

    📖 Guide updates needed:
      ✓ User Guide: "Caching API Responses" section
        → Add: Configuration options, TTL defaults
      ✓ Developer Guide: "Cache Implementation" section
        → Add: Architecture diagram, extension points

    Sphinx build: ✅ No errors (existing warnings are pre-existing)

**Example Invocation:**

.. code-block:: text

    @doc-writer src/docbuild/cli/cache_api.py
    @doc-writer feature/caching

----

4. Design Reviewer (Architecture & Patterns)
--------------------------------------------

**Skills Used:** :file:`design-review.skill.md`

**Role:** Holistic architecture review using Python design patterns.

**When to use:**

*   Before writing code (validate architecture)
*   After significant refactoring
*   You suspect over-engineering
*   You want pattern recommendations

**What it does:**

*   Reviews class design (composition vs. inheritance)
*   Checks Single Responsibility Principle (SRP)
*   Identifies over-abstraction (unnecessary interfaces, factories)
*   Suggests appropriate design patterns
*   Reviews async/await usage
*   Flags speculative complexity

**Output Example:**

.. code-block:: text

    Architecture Review: src/docbuild/config/cache.py

    ✅ Good: Dataclass for CacheConfig (no over-engineering)

    🔴 SRP violation: CacheManager class
      → Responsibilities: cache storage, TTL management, stats tracking
      → Suggestion: Extract stats tracking to separate CacheStats class
      → Result: Each class has single reason to change

    ⚠️ Over-abstraction: CacheBackend interface
      → Current: 1 implementation (InMemoryCache)
      → Risk: Interface adds complexity without flexibility need
      → Question: Will we add other backends (Redis, Memcached)?
        - If NO → Delete interface, use InMemoryCache directly
        - If YES → Keep interface, add Redis implementation

    ✅ Pattern match: Decorator for cache_api()
      → Good choice for transparent caching

    Composition opportunity:
      → Cache uses Strategy pattern for TTL (fixed, LRU, adaptive)
      → Consider: Composition over inheritance
        - Current: TTLStrategy base class + 3 subclasses
        - Alternative: Simple callable config + switch
        - Trade-off: Simpler code vs. extensibility

**Example Invocation:**

.. code-block:: text

    @design-review src/docbuild/config/cache.py
    @design-review feature/caching  (reviews all design files in branch)

----

5. PR Reviewer (Context-Independent)
-------------------------------------

**Skills Used:** :file:`code-smell.skill.md`, :file:`pytest-expert.skill.md`, :file:`docbuild-guidelines.skill.md`

**Role:** Independent code quality check that doesn't assume context or intent.

**When to use:**

*   Reviewing a pull request (independent of PR description)
*   You want a skeptical review (assumes code might not do what it claims)
*   You want pure code quality feedback
*   You have a branch to review in isolation

**Key Feature:** **CONTEXT-INDEPENDENT**

*   Does NOT read PR description
*   Does NOT assume feature intent
*   Does NOT validate against design (that's code-reviewer's job)
*   Pure question: "Is this code well-written?"

**What it does:**

*   Detects code smells (duplication, complexity, naming, tight coupling)
*   Logical flaws and edge cases
*   Security concerns
*   Test coverage analysis
*   Asks: "Does this code do what it claims to do?" (from code alone)

**Output Example:**

.. code-block:: text

    PR Review: feature/caching (independent, no context)

    🔴 Code smell: Duplication
      → Lines 45-52 and 12-19 have identical cache lookup logic
      → No comment explaining why duplication is needed
      → Suggestion: Extract to shared function

    🔴 Complexity: CacheManager.sync()
      → Cyclomatic complexity: 8 (acceptable is ≤5)
      → Consider: Break into smaller functions

    ⚠️ Security: TTL from user input
      → Line 67: ttl = request.args.get('ttl')
      → Risk: No validation (could be negative, huge, non-integer)
      → Suggestion: Validate range and type

    ✅ Good: Tests look comprehensive
      ✅ Coverage: 97.2%
      ✅ Edge cases covered (empty cache, expired entries)

    ⚠️ Missing: Docstring examples
      → get_cached_api_response() does complex things
      → Algorithm explanation would help reviewers understand intent

**Example Invocation:**

.. code-block:: text

    @pr-review feature/caching
    @pr-review https://github.com/opensuse/docbuild/pull/123

----

Common Workflows
================

Workflow 1: Implement New Feature
---------------------------------

1.  **Design phase:**
    *   :command:`@design-review feature-branch`
    *   → Get architecture feedback
    *   → Adjust design based on feedback

2.  **Implementation:**
    *   Write code...

3.  **Quality checks:**
    *   :command:`@code-reviewer feature-branch`
    *   → Validate code matches design
    *   → Fix coverage drops
    *   :command:`@test-engineer feature-branch`
    *   → Auto-run tests
    *   → Fill coverage gaps with tests

4.  **Documentation:**
    *   :command:`@doc-writer feature-branch`
    *   → Complete docstrings
    *   → Update guides

5.  **Final review:**
    *   :command:`@pr-review feature-branch`
    *   → Independent code quality check
    *   → Catch anything missed

----

Workflow 2: Fix a Bug
---------------------

1.  **Root cause analysis:**
    *   :command:`@code-reviewer` :file:`src/docbuild/module_with_bug.py`
    *   → Identify logical flaw

2.  **Implement fix...**

3.  **Verify fix:**
    *   :command:`@test-engineer` :file:`src/docbuild/module_with_bug.py`
    *   → Ensure tests catch the bug
    *   → No coverage regressions

4.  **Documentation:**
    *   :command:`@doc-writer` :file:`src/docbuild/module_with_bug.py`
    *   → Update any clarifications in docstrings

5.  **Independent review:**
    *   :command:`@pr-review bugfix-branch`
    *   → Ensure fix is sound and doesn't introduce new issues

----

Workflow 3: Code Review on PR (as Reviewer)
-------------------------------------------

You receive a PR for review:

1.  **Initial analysis:**
    *   :command:`@pr-review https://github.com/opensuse/docbuild/pull/456`
    *   → Get independent code quality assessment
    *   → Identify smells, security issues, coverage gaps

2.  **Context-aware review:**
    *   :command:`@code-reviewer pr-branch`
    *   → Check if code matches stated feature intent
    *   → Coverage should not drop

3.  **Summary for PR comment:**
    *   Combine feedback from pr-reviewer (independent) and code-reviewer (context-aware) into a comprehensive review.

----

Workflow 4: Refactoring Existing Code
-------------------------------------

1.  **Design phase:**
    *   :command:`@design-review` :file:`src/docbuild/legacy_module.py`
    *   → Identify over-engineering, SRP violations
    *   → Plan refactoring

2.  **Refactor...**

3.  **Quality assurance:**
    *   :command:`@code-reviewer` :file:`src/docbuild/legacy_module.py`
    *   → Ensure refactoring matches intent (improved design)
    *   → No logic changes, no coverage drops
    *   :command:`@test-engineer` :file:`src/docbuild/legacy_module.py`
    *   → Verify all tests still pass
    *   → Coverage unchanged or improved

4.  **Independent review:**
    *   :command:`@pr-review refactor-branch`
    *   → Ensure refactoring doesn't introduce bugs
    *   → Code is cleaner, not just different

----

Understanding Coverage Reports
==============================

When test-engineer runs tests, it reports coverage like this:

.. code-block:: text

    File: src/docbuild/cli/cache_api.py
      Lines: 87
      Covered: 83
      Coverage: 95.4%

      Missing lines:
        67: except CacheError as e:        # Error path not tested
        89: if ttl_remaining < 60:          # Edge case: near-expiry
        102: logger.debug(f"Cache stats")  # Debug logging not exercised

**What each means:**

*   **Missing** → Code path never executed in tests
*   **Covered** → Code path has at least one test

**When to fix:**

*   New code should have >95% coverage
*   Coverage should not drop compared to main branch
*   Debug/logging paths (nice to have, not critical)
*   Error handling is more important than happy paths

----

Agent vs. Skill: The "What" vs. The "How"
===========================================

A key concept in this workflow is the separation of roles between agents and skills:

*   An **Agent** definition (:file:`.opencode/agents/name.md`) describes the agent's high-level purpose, persona, and goals. It answers the question, "**WHAT** is your job?"

*   A **Skill** definition (:file:`.agents/skills/.../SKILL.md`) provides a detailed, step-by-step procedure for a specific task. It answers the question, "**HOW** do you do your job?"

Agents are guided by their core instructions, and they consume skills to execute specific, complex procedures correctly and consistently.

----

Agent vs. Skill: The "What" vs. The "How"
===========================================

A key concept in this workflow is the separation of roles between agents and skills:

*   An **Agent** definition (:file:`.opencode/agents/name.md`) describes the agent's high-level purpose, persona, and goals. It answers the question, "**WHAT** is your job?"

*   A **Skill** definition (:file:`.agents/skills/.../SKILL.md`) provides a detailed, step-by-step procedure for a specific task. It answers the question, "**HOW** do you do your job?"

Agents are guided by their core instructions, and they consume skills to execute specific, complex procedures correctly and consistently.

----

Skills: What Agents Use
=======================

.. list-table::
   :header-rows: 1

   * - Skill
     - Used By
     - Purpose
   * - :file:`docbuild-guidelines.skill.md`
     - code-reviewer, pr-reviewer
     - Surgical changes, YAGNI, simplicity
   * - :file:`code-review.skill.md`
     - code-reviewer
     - Context-aware design validation
   * - :file:`code-smell.skill.md`
     - pr-reviewer
     - Context-independent quality checks
   * - :file:`pytest-expert.skill.md`
     - test-engineer, pr-reviewer
     - Coverage, parametrize, mocking
   * - :file:`doc-writer.skill.md`
     - doc-writer
     - Docstring completeness, examples
   * - :file:`design-review.skill.md`
     - design-reviewer
     - Patterns, SRP, over-engineering

----

Skill File Structure
====================

Each skill in the :file:`.agents/skills/` directory is a Markdown file (:file:`SKILL.md`) that provides instructions to an agent. All procedural skills follow a standard structure composed of two parts:

1. A YAML Frontmatter for Metadata
------------------------------------

The file begins with a YAML block that provides structured data about the skill.

.. code-block:: yaml

   ---
   name: [skill-name]
   description: [One-sentence description of the skill's purpose.]
   license: GPL-3.0-or-later
   compatibility: [opencode, github_copilot, claude]
   metadata:
     category: [e.g., testing, documentation, design]
     audience: [developers]
   ---

2. A Markdown Body with Standard Sections
-----------------------------------------

The body of the skill uses Markdown headings to create a consistent, four-part structure:

*   **Context:** Explains the background and the "why" of the skill. It sets the scene for the agent.
*   **Procedure:** A numbered, step-by-step list of actions the agent should take to complete the task.
*   **Checklist:** A list of questions the agent can use to verify its work during the procedure.
*   **Validation:** The final success criteria. It defines what must be true for the task to be considered complete.

This structure ensures that all skills are consistent, predictable, and easy for both agents and humans to understand.

----

Best Practices
==============

Core Principle: Ask When Unsure
--------------------------------

A critical guardrail for all agents in this workflow is to **ask for clarification** when a request is ambiguous or they lack context. Agents will not make assumptions about your intent. They will state what they are unsure about and, if possible, present you with options.

1. Use the right agent for the right phase
------------------------------------------

*   Design phase → :command:`@design-review` (before code)
*   After code → :command:`@code-reviewer` (validation)
*   Testing → :command:`@test-engineer` (coverage analysis)
*   Docs → :command:`@doc-writer` (completeness)
*   Final → :command:`@pr-review` (independent check)

2. Let agents auto-run tests
----------------------------

*   test-engineer auto-runs tests after changes
*   Don't manually run tests first; let it analyze and report

3. Address coverage gaps first
------------------------------

*   Coverage < 95% blocks approval
*   Write tests to fill gaps (use test-engineer for parametrize suggestions)

4. Code-reviewer is your sounding board
---------------------------------------

*   Use it to validate "does my code match my design?"
*   Use it to catch missed edge cases
*   Use it to enforce YAGNI (no speculative features)

5. PR-Reviewer is skeptical by design
-------------------------------------

*   It doesn't know your intent; that's the point
*   If it finds issues, they're real (no context bias)
*   Use pr-reviewer as final sanity check

6. Documentation is not optional
--------------------------------

*   doc-writer ensures completeness
*   Complex functions get examples
*   Guides stay in sync with code

----

Directory Structure
===================

.. code-block:: text

    .
    ├── .agents/
    │   └── skills/      # Shared skills used by agents
    │       ├── ...
    │       └── docstrings/
    │           └── SKILL.md
    │
    └── .opencode/
        └── agents/      # Agent definitions for OpenCode
            ├── code-reviewer.md
            ├── docbuild.md
            └── ...

**Why this structure:**

*   Agent and skill definitions are separated for clarity.
*   GitHub Copilot uses symlinks from :file:`.github/`
*   OpenCode auto-discovers agents & skills

----

Integration with Development Tools
==================================

With OpenCode
-------------

*   Run :command:`docbuild <task>` from your shell to start the workflow.
*   Inside OpenCode, use at-commands like :command:`@code-reviewer` to invoke sub-agents.
*   Skills guide agent behavior

With GitHub Copilot
-------------------

*   Agents discovered from :file:`.github/agents/` (symlinked to :file:`../.opencode/agents/`)
*   Instructions in :file:`.github/instructions/` provide general guidance

With Claude
-----------

*   Paste agent/skill files directly or link them
*   All agents work across models (Claude 3.5, GPT-4o, etc.)

With VS Code
------------

*   Agent files can be referenced in VS Code Copilot Chat
*   Same at-commands work

----

When in Doubt
=============

.. list-table::
   :header-rows: 1

   * - Scenario
     - Use This Agent
   * - "Is my design sound?"
     - :command:`@design-review`
   * - "Does my code do what I said?"
     - :command:`@code-reviewer`
   * - "Do I have enough tests?"
     - :command:`@test-engineer`
   * - "Are my docstrings complete?"
     - :command:`@doc-writer`
   * - "Can you find anything wrong with this code?"
     - :command:`@pr-review`
   * - "I have a complex task"
     - :command:`docbuild <task>`

----

See Also
========

*   :file:`AGENTS.md` — Project setup and conventions
*   :file:`pyproject.toml` — Dependencies and tool configuration
*   :file:`.github/instructions/python.instructions.md` — Python style guide
*   :file:`pytest.ini` — Pytest configuration (coverage thresholds, etc.)
