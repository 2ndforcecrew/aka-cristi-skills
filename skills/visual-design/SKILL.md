---
name: visual-design
description: Evaluate, design and independently review visual work across illustration, character and environment design, photography, brand identity, packaging, campaigns, editorial layouts, digital interfaces and motion graphics. Use when a user asks for visual direction, redesign, layout, typography, style analysis, or visual quality assurance.
---

# Visual Design Skill · V0.1

## Mission
Turn a design brief into an intentional, buildable artifact with traceable aesthetic decisions and honest QA evidence. This skill is **brand-neutral**: never force AKA.CRISTI colors, logos or tastes onto another user's brand.

## Trigger and boundaries
Select the production route below for each requested deliverable. Respect the user's supplied assets, likenesses, logo geometry and existing project constraints. For reference works, extract principles rather than copying distinctive layouts or copyrighted imagery. Never claim that a screenshot, browser test, or implementation exists without evidence.

## Workflow: Brief → Perceive → Reason → Execute → Verify
1. **Brief**: capture deliverable, audience, platform, message, existing brand, accessibility, assets, constraints and success criteria. Ask only for essential missing details.
2. **Perceive**: inspect existing artifact and supplied references where available. Record observations, not assumptions. Describe composition, type hierarchy, color, spacing, imagery, contrast, interaction and responsive behavior. If screenshots or reference pages cannot be accessed, label them unverified.
3. **Reason**: propose at most three design directions when useful. Choose one by weighing clarity, originality, brand fit, feasibility and accessibility. Produce a compact Design Decision Record (DDR): goal → evidence → choice → trade-off.
4. **Execute**: implement in the native medium. For code, inspect existing structure, change the minimum necessary files, respect reduced-motion, keyboard operation, responsive breakpoints and performance. For static art, specify production dimensions, typography, color and export criteria. Do not substitute a concept mockup for a functional deliverable.
5. **Verify**: run hard checks first, then aesthetic critique. Repair high-severity issues and repeat within a bounded loop (maximum two automatic revision passes). If tools are unavailable, mark the check NOT_RUN and explain why. Human review is required for subjective final approval.

## Art direction across media

Select the output by its intended use. When references arrive together, identify the role of each image (subject identity, drawing technique, light, palette, composition or timing). Record what must carry over and what can vary. Use the client's own references before inferring any house style. Infer timing from stills only as a proposal.

| Deliverable | Make the design decisions in this order | Inspect the actual output |
| --- | --- | --- |
| Narrative, fashion or editorial illustration | Define the story beat and viewpoint, thumbnail the value masses, choose silhouette and gesture, then set edge treatment, mark-making and color. Render at the intended crop. | Read the silhouette at thumbnail size; zoom in on hands, overlaps and texture; compare the focal point with the brief. |
| Characters, IP and environments | Lock distinguishing proportions, face, costume and props in a model sheet when multiple views are requested. Establish horizon, scale and lighting for the environment. | Compare identities across poses and views; check perspective, scale and contact shadows where characters meet the ground. |
| Brand identity and graphic systems | Establish mark geometry, wordmark spacing, type hierarchy and palette roles. Apply the system to the requested touchpoints. | Inspect small-size and monochrome legibility; compare mark geometry and clear space across applications. |
| Packaging and merchandise | Work from the supplied dieline or printable area; map front, side, seams and folds before placing artwork. Request the vendor specification when needed for production. | Inspect at physical scale, fold boundaries, readable copy and vendor bleed; label a perspective mockup as a concept until the production file is checked. |
| Editorial, campaign and commerce | Plan reading order, grid, typography and product prominence for each placement. Recompose for the target ratio. | Inspect the final crop and smallest text on each requested placement; verify key copy, product proportions and logo. |
| Fashion photography and image direction | Decide framing, lens perspective, key/fill relationship, styling and grade. Preserve identity, fabric texture and product color across the set. | Inspect skin and material detail at full resolution and compare light direction and color in a contact sheet. |
| Web, UI and interactive design | Translate visual hierarchy into components, responsive behavior, states and keyboard paths. Implement and exercise the primary journey. | Check a narrow screen, visible focus, actual interactions and reduced motion in a running build. |
| Motion graphics and storyboards | Establish key poses, layers, timing, easing, camera path and loop seam. Track fixed brand geometry separately from moving elements. | Play the export at target speed; inspect first/last frames, occlusions and identity continuity. Identify boards or animatics explicitly when those are the deliverables. |

For a mixed brief, carry a short list of shared decisions through the outputs. For example, carry a character's silhouette and two ink colors from an illustration to a sleeve, then rearrange the composition around its fold. Judge each output at its own viewing size. Return editable artwork, print files, playable media or working code according to the requested format and available tools. Record any missing output explicitly.

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

Track field validation separately for each additional medium. A passing web case supplies no evidence for illustration continuity, a packaging proof or a motion export.
