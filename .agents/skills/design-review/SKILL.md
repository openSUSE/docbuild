---
name: design-review
description: A skill for providing feedback on software architecture and design patterns.
license: GPL-3.0-or-later
compatibility: [opencode, github_copilot, claude]
metadata:
  category: design
  audience: [developers]
---
# Design Review Skill

This skill guides a holistic review of software architecture and design for maintainability and scalability.

## Workflow: Analyze, Propose, Implement

Your workflow is as follows:

1.  **Analyze & Propose:** Perform a read-only analysis, identify design improvements, and report findings as a summary or TODO list.
2.  **Ask for Confirmation:** After presenting your suggestions, you MUST ask the user for permission to implement them. Use the `question` tool for this.
3.  **Implement (If Approved):** If the user approves, proceed with implementing the changes.

**Example "Ask" Step:**

```
print(default_api.question(questions=[
  default_api.QuestionQuestions(
    header="Implement Suggestions",
    question="Would you like me to proceed with implementing the suggested design changes?",
    options=[
      default_api.QuestionQuestionsOptions(label="Yes, proceed", description="Apply the changes as suggested."),
      default_api.QuestionQuestionsOptions(label="No, not at this time", description="Do not apply any changes.")
    ],
    multiple=False
  )
]))
```

## 1. Core Principles

*   **Single Responsibility Principle (SRP):** Each class and function should have a single reason to change. Find and flag 'god classes'.
*   **Composition Over Inheritance:** Prefer composition (has-a) over inheritance (is-a). Inheritance can lead to tight coupling and rigid hierarchies.
*   **YAGNI (You Ain't Gonna Need It):** Is the design more complex than it needs to be? Avoid speculative abstractions and features that aren't required now.

## 2. Design Patterns

*   **Identify where design patterns could be useful.** For example:
    *   **Factory:** For creating objects without specifying the exact class.
    *   **Strategy:** For enabling an algorithm's behavior to be selected at runtime.
    *   **Decorator:** For adding behavior to an object dynamically.
    *   **Observer:** For notifying multiple objects about a change in state.
*   **Don't force it.** Only suggest a design pattern if it clearly simplifies the code or improves maintainability. Do not add patterns for the sake of adding patterns.

## 3. Red Flags (Over-Engineering)

*   **Single-implementation interfaces:** An interface with only one concrete implementation is often a sign of over-engineering.
*   **Unnecessary flexibility:** Configuration options or extension points that will likely never be used.
*   **Deep inheritance hierarchies:** These can be difficult to understand and maintain.
*   **Complex dependency graphs:** Look for circular dependencies and other signs of tight coupling.

## 4. Data Structures

*   **Choose the right tool for the job.**
    *   Use a `dataclass` for simple, immutable data structures.
    *   Use `Pydantic` for data validation and serialization/deserialization.
    *   Use a `NamedTuple` for very simple, lightweight structures.

## 5. Output Format

Provide a high-level summary of the design, followed by a list of concrete suggestions for improvement. For each suggestion, explain *why* it is an improvement.

**Example Suggestion:**

> **⚠️ SRP Violation in `UserManager` class**
> *   **Issue:** The `UserManager` class is responsible for both user authentication and profile management.
> *   **Suggestion:** Split the class into two: `AuthManager` and `ProfileManager`. This will make the code easier to understand and maintain, as each class will have a single, clear responsibility.
