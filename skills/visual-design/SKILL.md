---
name: visual-design
description: Evaluate, design and independently review visual work across websites, posters, editorial graphics and brand systems. Use when a user asks for visual direction, redesign, layout, typography, style analysis, or visual quality assurance.
---

# Visual Design Skill · V0.1

## Mission
Turn a design brief into an intentional, buildable artifact with traceable aesthetic decisions and honest QA evidence. This skill is **brand-neutral**: never force AKA.CRISTI colors, logos or tastes onto another user's brand.

## Trigger and boundaries
Use for UI/web, editorial, poster, photography art direction and branding. Respect the user's supplied assets, likenesses, logo geometry and existing project constraints. For reference works, extract principles rather than copying distinctive layouts or copyrighted imagery. Never claim that a screenshot, browser test, or implementation exists without evidence.

## Workflow: Brief → Perceive → Reason → Execute → Verify
1. **Brief**: capture deliverable, audience, platform, message, existing brand, accessibility, assets, constraints and success criteria. Ask only for essential missing details.
2. **Perceive**: inspect existing artifact and supplied references where available. Record observations, not assumptions. Describe composition, type hierarchy, color, spacing, imagery, contrast, interaction and responsive behavior. If screenshots or reference pages cannot be accessed, label them unverified.
3. **Reason**: propose at most three design directions when useful. Choose one by weighing clarity, originality, brand fit, feasibility and accessibility. Produce a compact Design Decision Record (DDR): goal → evidence → choice → trade-off.
4. **Execute**: implement in the native medium. For code, inspect existing structure, change the minimum necessary files, respect reduced-motion, keyboard operation, responsive breakpoints and performance. For static art, specify production dimensions, typography, color and export criteria. Do not substitute a concept mockup for a functional deliverable.
5. **Verify**: run hard checks first, then aesthetic critique. Repair high-severity issues and repeat within a bounded loop (maximum two automatic revision passes). If tools are unavailable, mark the check NOT_RUN and explain why. Human review is required for subjective final approval.

## Style DNA extraction
Record a source and permission context, observations and transferable design principles. Use the following fields:
- source / medium / observation
- typography / palette / grid / spacing / imagery / motion
- transferable_principle / avoid_copying / confidence / applicable_context
Keep source evidence distinct from generated interpretations. A reference is inspiration, not a template to reproduce.

## Quality gates
**Hard checks (pass/fail/not-run):** required content present; responsive overflow; text contrast (WCAG AA target where applicable); keyboard navigation; focus visibility; image alt text; reduced-motion behavior; build/lint/typecheck if relevant; no broken media or links; preserve identity and brand assets.

**Aesthetic critique (1–5 each, with reasons):** hierarchy, coherence, editorial rhythm, originality, brand fit, composition, imagery and craft. These are editorial judgments, not automated guarantees. Never average them into a claim of objectively correct beauty.

**Evidence contract:** each gate records status, method, evidence reference, and limitation. Separate VERIFIED, FAILED, NOT_RUN, and SUBJECTIVE_REVIEW. Do not turn unavailable tools into a passing score.

## Output contract
Provide: (a) chosen direction and rationale, (b) artifact or exact changed files, (c) DDR, (d) hard-check matrix, (e) aesthetic critique with actionable corrections, (f) known limitations, (g) next action. Keep the report concise and suited to the user's medium.

## Tool selection and recovery
Use available native tools for inspection, creation, browser validation and screenshots. Prefer API/MCP for web retrieval; use browser automation when necessary; HTML parsing (e.g. Beautiful Soup) is optional and not presumed installed. Never crawl a gallery at scale without checking site policies and resource costs. Never imply a tool was installed just because an equivalent is available.

On failure: diagnose once, retry only reversible operations with bounded attempts, preserve originals, log what changed, and stop before irreversible publication or overwriting existing production sites.

## Acceptance
A passing local Skill validation proves file structure only. Real acceptance requires at least three varied briefs (website, poster/editorial, brand system), side-by-side comparison with/without this skill, reproducible evidence, and an independent reviewer. Until then, report V0.1 as implemented but NOT FIELD-VALIDATED.
