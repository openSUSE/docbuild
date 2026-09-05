---
name: create-pydantic-model
description: Create meaningful Pydantic models with clear naming, field metadata, defaults, and validation.
---

# Create Meaningful Pydantic Models Skill
Use this skill when the user asks to design or improve Pydantic models.

## Goal
Produce models that are readable, explicit, safe, and stable.

## Naming rules

* Use nouns for model names: `UserProfile`, `BuildJob`, `PortalDocset`.
* Use singular model names unless the object is inherently plural.
* Field names should be descriptive and domain-specific.
* Use `snake_case` for fields.
* Avoid unclear abbreviations (`cfg`, `dt`, `val`).
* Avoid generic fields like `data`, `info`, or `value` unless the domain truly needs them.
* Keep naming consistent with existing project terminology.

## Good and bad naming

Good naming patterns:

* model name reflects a business concept
* field name encodes meaning (`published_at`, `docset_id`, `is_active`)
* booleans start with `is_`, `has_`, or `can_`

Bad naming patterns:

* one-letter or short unclear names (`x`, `tmp`, `obj`)
* overloaded fields (`status` without clear allowed values)
* ambiguous timestamps (`date` instead of `created_at`)

## Field design

* Add a short description to all externally visible fields.
* Use precise types first; avoid `Any` unless unavoidable.
* Prefer constrained types where possible (length, range, pattern).
* Use `Literal` or `Enum` for closed sets of values.
* Mark optional fields explicitly and only when truly optional.
* Keep nested models small and composable.

## Defaults and required fields

* Make a field required when callers must always provide it.
* Use defaults only when there is a real domain default.
* Do not hide missing required business data behind empty defaults.
* Prefer `default_factory` for mutable defaults and generated values.
* Keep defaults deterministic unless randomness/time is explicitly required.

## Descriptions and examples

* Field descriptions should state purpose, not restate the name.
* Include units and format when relevant (for example: seconds, ISO 8601).
* Add examples for fields that are easy to misuse.
* Keep descriptions concise and objective.

## Validation strategy (Pydantic v2)

Use layered validation:

1. type-level constraints for shape and primitive limits
2. field-level validators for single-field business rules
3. model-level validators for cross-field consistency

Validation rules:

* Validate invariants, not presentation concerns.
* Error messages must explain the error and the expected format.
* Keep validators pure and side-effect free.
* Use model-level validation for dependencies (for example: `start_at <= end_at`).
* Normalize input only when that behavior is intended and documented.

## Serialization and schema quality

* Define aliases only when needed for external API compatibility.
* Keep internal names stable; map external names via aliasing.
* Ensure JSON schema output stays understandable.
* Avoid leaking internal-only fields in public response models.

## Review checklist

* Names are clear and domain-oriented.
* Field types are specific and strict enough.
* Required vs optional is intentional.
* Defaults are meaningful and safe.
* Field descriptions are present and useful.
* Validation covers both single-field and cross-field rules.
* Error messages are understandable for users.
* Model stays focused and not overloaded with unrelated concerns.

## Typical anti-patterns

* One large model doing input, domain, and output responsibilities at once.
* Catch-all dictionaries in place of typed nested models.
* Silent coercions that hide bad input quality.
* Validators that mutate unrelated fields.
* Reusing one model for multiple incompatible API versions.

## How to apply this skill

1. Identify the business concept and boundaries.
2. Propose model and field names first.
3. Define required and optional fields.
4. Add descriptions and domain-safe defaults.
5. Add field-level and model-level validation.
6. Check schema readability and error quality.
7. Refine by removing ambiguity and unnecessary fields.
