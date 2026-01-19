"""
Seed Content Templates
======================
Populate database with 25 high-quality content templates across all awareness levels.

Templates are based on:
- 5 Awareness Levels (Eugene Schwartz)
- FATE Framework (Focus, Authority, Tribe, Emotion)

Distribution:
- Problem-Aware: 8 templates (TPL-002)
- Solution-Aware: 7 templates (TPL-003)
- Product-Aware: 6 templates (TPL-004)
- Most-Aware: 4 templates (TPL-005)

Total: 25 templates
"""

import asyncio
import sys
from pathlib import Path

# Add Backend to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from database.models import ContentTemplate
from datetime import datetime
from loguru import logger
import os


# Template definitions
TEMPLATES = [
    # ===================================================
    # PROBLEM-AWARE TEMPLATES (8)
    # ===================================================
    {
        "name": "Symptom Mirror",
        "description": "Reflects the audience's pain points back to them with empathy",
        "template_type": "post",
        "awareness_level": "problem_aware",
        "prompt_text": """Write a post that mirrors {icp}'s specific pain: {pain}.

Start with: "Ever feel like {pain}?"

Then describe 3-4 symptoms they're experiencing:
- Symptom 1: {symptom_1}
- Symptom 2: {symptom_2}
- Symptom 3: {symptom_3}

End with: "You're not alone. Here's what's really happening..."

Tone: Empathetic, validating, non-judgmental
Length: 150-200 words""",
        "fate_focus": 0.2,
        "fate_authority": 0.15,
        "fate_tribe": 0.4,
        "fate_emotion": 0.25,
        "cta_strength": "none",
    },
    {
        "name": "Cost of Inaction",
        "description": "Shows what happens if the problem isn't solved",
        "template_type": "post",
        "awareness_level": "problem_aware",
        "prompt_text": """Write about the consequences of not addressing {pain} for {icp}.

Structure:
1. Today: Describe current state
2. In 6 months: What gets worse
3. In 1 year: The compounding cost
4. In 3 years: The breaking point

Use specific numbers and scenarios from {industry}.

End with: "The cost of doing nothing is higher than you think."

Tone: Urgent but not alarmist
Length: 200-250 words""",
        "fate_focus": 0.35,
        "fate_authority": 0.25,
        "fate_tribe": 0.15,
        "fate_emotion": 0.25,
        "cta_strength": "none",
    },
    {
        "name": "Mistake Story",
        "description": "Personal story of making the same mistake",
        "template_type": "post",
        "awareness_level": "problem_aware",
        "prompt_text": """Share a personal story about experiencing {pain} as {icp}.

Hook: "I used to {mistake_behavior}..."

Story beats:
1. The setup: What I was doing wrong
2. The wake-up call: When I realized
3. The turning point: What changed
4. The lesson: What I learned

Make it vulnerable and authentic.

End with: "If you're doing this too, here's what I wish I knew earlier..."

Tone: Vulnerable, authentic, relatable
Length: 250-300 words""",
        "fate_focus": 0.15,
        "fate_authority": 0.35,
        "fate_tribe": 0.25,
        "fate_emotion": 0.25,
        "cta_strength": "soft",
    },
    {
        "name": "Mechanism Reveal",
        "description": "Explains WHY the problem happens",
        "template_type": "post",
        "awareness_level": "problem_aware",
        "prompt_text": """Explain the hidden mechanism behind {pain} for {icp}.

Hook: "Here's the real reason {pain} keeps happening..."

Explain:
1. The surface symptom (what people see)
2. The hidden mechanism (what's actually happening)
3. Why common fixes don't work
4. What needs to change instead

Use {mechanism} as the core insight.

Tone: Explanatory, insightful, aha-moment
Length: 200-250 words""",
        "fate_focus": 0.3,
        "fate_authority": 0.4,
        "fate_tribe": 0.1,
        "fate_emotion": 0.2,
        "cta_strength": "none",
    },
    {
        "name": "Self-Assessment Checklist",
        "description": "Interactive checklist to diagnose the problem",
        "template_type": "post",
        "awareness_level": "problem_aware",
        "prompt_text": """Create a diagnostic checklist for {icp} experiencing {pain}.

Hook: "Do you have these {number} warning signs?"

Checklist (5-7 items):
□ {sign_1}
□ {sign_2}
□ {sign_3}
□ {sign_4}
□ {sign_5}

Scoring:
- 0-2 checked: You're good
- 3-4 checked: Pay attention
- 5+ checked: Time to take action

End with insight about what the score means.

Tone: Interactive, diagnostic, helpful
Length: 150-200 words""",
        "fate_focus": 0.25,
        "fate_authority": 0.3,
        "fate_tribe": 0.2,
        "fate_emotion": 0.25,
        "cta_strength": "soft",
    },
    {
        "name": "Myth Buster",
        "description": "Debunks common misconceptions about the problem",
        "template_type": "post",
        "awareness_level": "problem_aware",
        "prompt_text": """Debunk a common myth about {pain} that {icp} believes.

Hook: "Everyone thinks {pain} is caused by {common_belief}, but..."

Structure:
- The Myth: What people wrongly believe
- Why it's wrong: The evidence
- What's actually true: The reality
- What to do instead: The action

Use data from {industry} to support your points.

Tone: Educational, myth-busting, corrective
Length: 200-250 words""",
        "fate_focus": 0.25,
        "fate_authority": 0.45,
        "fate_tribe": 0.1,
        "fate_emotion": 0.2,
        "cta_strength": "none",
    },
    {
        "name": "Identity Callout",
        "description": "Names the identity of people who have this problem",
        "template_type": "post",
        "awareness_level": "problem_aware",
        "prompt_text": """Create identity-based content for {icp} struggling with {pain}.

Hook: "If you're a {identity}, you know this feeling..."

Describe:
1. The unique struggle they face
2. Why it's harder for them specifically
3. What makes their situation different
4. The tribe they're part of

Use inclusive language. Make them feel seen.

End with: "You're not weird. You're just {identity}."

Tone: Identity-affirming, inclusive, tribal
Length: 150-200 words""",
        "fate_focus": 0.15,
        "fate_authority": 0.15,
        "fate_tribe": 0.5,
        "fate_emotion": 0.2,
        "cta_strength": "none",
    },
    {
        "name": "Diagnostic Question",
        "description": "Thought-provoking question that reveals the problem",
        "template_type": "post",
        "awareness_level": "problem_aware",
        "prompt_text": """Pose a diagnostic question about {pain} for {icp}.

Hook: "{diagnostic_question}"

Then explain:
- Why this question matters
- What your answer reveals
- The 3 possible answers and what each means
- What to do based on your answer

Make them think deeply about their situation.

Tone: Thought-provoking, introspective, revelatory
Length: 200-250 words""",
        "fate_focus": 0.3,
        "fate_authority": 0.25,
        "fate_tribe": 0.15,
        "fate_emotion": 0.3,
        "cta_strength": "soft",
    },

    # ===================================================
    # SOLUTION-AWARE TEMPLATES (7)
    # ===================================================
    {
        "name": "3 Approaches Breakdown",
        "description": "Compares 3 different solution approaches objectively",
        "template_type": "post",
        "awareness_level": "solution_aware",
        "prompt_text": """Compare 3 approaches to solving {pain} for {icp}.

Hook: "There are 3 ways to {outcome}. Here's how to choose..."

For each approach ({approach_1}, {approach_2}, {approach_3}):
- What it is
- Best for: [use case]
- Pros: [2-3 benefits]
- Cons: [2-3 drawbacks]
- Time to results: [timeline]

End with: "Choose based on your {decision_factor}."

Tone: Objective, educational, comparison
Length: 250-300 words""",
        "fate_focus": 0.35,
        "fate_authority": 0.35,
        "fate_tribe": 0.15,
        "fate_emotion": 0.15,
        "cta_strength": "soft",
    },
    {
        "name": "Framework Steps",
        "description": "Breaks down a framework into actionable steps",
        "template_type": "post",
        "awareness_level": "solution_aware",
        "prompt_text": """Teach the {framework_name} framework for solving {pain}.

Hook: "The {framework_name} framework: How {icp} can {outcome} in {timeframe}"

Steps:
1. {step_1}: [What to do and why]
2. {step_2}: [What to do and why]
3. {step_3}: [What to do and why]
4. {step_4}: [What to do and why]

For each step, include one example from {industry}.

End with: "This framework works because {reason}."

Tone: Educational, step-by-step, systematic
Length: 300-350 words""",
        "fate_focus": 0.45,
        "fate_authority": 0.3,
        "fate_tribe": 0.1,
        "fate_emotion": 0.15,
        "cta_strength": "soft",
    },
    {
        "name": "Decision Tree",
        "description": "Helps audience choose the right solution path",
        "template_type": "post",
        "awareness_level": "solution_aware",
        "prompt_text": """Create a decision tree for {icp} choosing how to solve {pain}.

Hook: "Not sure which approach to take? Use this decision tree..."

Decision nodes:
1. First question: {question_1}
   - If YES → {path_a}
   - If NO → Continue

2. Second question: {question_2}
   - If YES → {path_b}
   - If NO → {path_c}

For each path, explain:
- Why this is right for them
- What to do next

Tone: Decision-support, clear, directive
Length: 250-300 words""",
        "fate_focus": 0.4,
        "fate_authority": 0.3,
        "fate_tribe": 0.1,
        "fate_emotion": 0.2,
        "cta_strength": "direct",
    },
    {
        "name": "Tool Stack Breakdown",
        "description": "Shows the complete toolkit needed for the solution",
        "template_type": "post",
        "awareness_level": "solution_aware",
        "prompt_text": """Share the complete tool stack for {icp} to achieve {outcome}.

Hook: "Here's every tool you need to {outcome}..."

Categories:
1. {category_1}: {tool_1} - Why you need it
2. {category_2}: {tool_2} - Why you need it
3. {category_3}: {tool_3} - Why you need it
4. {category_4}: {tool_4} - Why you need it

Total monthly cost: ${total_cost}
Free alternatives: {free_options}

Tone: Comprehensive, practical, resource-focused
Length: 250-300 words""",
        "fate_focus": 0.35,
        "fate_authority": 0.35,
        "fate_tribe": 0.15,
        "fate_emotion": 0.15,
        "cta_strength": "soft",
    },
    {
        "name": "Do This First",
        "description": "Identifies the single most important first step",
        "template_type": "post",
        "awareness_level": "solution_aware",
        "prompt_text": """Tell {icp} the ONE thing they should do first to solve {pain}.

Hook: "Before you do anything else to {outcome}, do this first..."

Structure:
1. Why most people start wrong
2. The right first step: {first_step}
3. Why this matters so much
4. How to do it (tactical)
5. What to do after

Make it crystal clear and actionable.

Tone: Directive, clarifying, prioritizing
Length: 200-250 words""",
        "fate_focus": 0.5,
        "fate_authority": 0.25,
        "fate_tribe": 0.1,
        "fate_emotion": 0.15,
        "cta_strength": "direct",
    },
    {
        "name": "Case Study Breakdown",
        "description": "Detailed breakdown of how someone solved the problem",
        "template_type": "post",
        "awareness_level": "solution_aware",
        "prompt_text": """Share a case study of {example_person} solving {pain}.

Hook: "How {example_person} went from {before_state} to {after_state} in {timeframe}"

Story structure:
- Starting point: Where they were
- The approach: What they did (specific steps)
- Obstacles: What went wrong
- Adjustments: How they adapted
- Results: What they achieved (specific metrics)

Extract 3 key lessons at the end.

Tone: Story-driven, detailed, proof-based
Length: 350-400 words""",
        "fate_focus": 0.25,
        "fate_authority": 0.35,
        "fate_tribe": 0.2,
        "fate_emotion": 0.2,
        "cta_strength": "soft",
    },
    {
        "name": "Benchmarks & Timelines",
        "description": "Sets realistic expectations for results",
        "template_type": "post",
        "awareness_level": "solution_aware",
        "prompt_text": """Share realistic benchmarks for {icp} pursuing {outcome}.

Hook: "Here's what to expect when solving {pain}..."

Timeline:
- Week 1-4: {milestone_1} - {metric_1}
- Month 2-3: {milestone_2} - {metric_2}
- Month 4-6: {milestone_3} - {metric_3}
- Month 6+: {milestone_4} - {metric_4}

Red flags: Signs you're off track
Green flags: Signs you're on track

Based on data from {data_source}.

Tone: Realistic, expectation-setting, data-driven
Length: 250-300 words""",
        "fate_focus": 0.3,
        "fate_authority": 0.4,
        "fate_tribe": 0.15,
        "fate_emotion": 0.15,
        "cta_strength": "soft",
    },

    # ===================================================
    # PRODUCT-AWARE TEMPLATES (6)
    # ===================================================
    {
        "name": "Why We Built This",
        "description": "Origin story of your product/solution",
        "template_type": "post",
        "awareness_level": "product_aware",
        "prompt_text": """Share why you built {offer} for {icp}.

Hook: "Why we built {offer}..."

Story beats:
1. The problem we personally experienced: {founder_pain}
2. What we tried that didn't work
3. The insight that changed everything: {key_insight}
4. How we built {offer} differently
5. Who it's for (and who it's NOT for)

Make it personal and mission-driven.

Tone: Personal, mission-driven, authentic
Length: 300-350 words""",
        "fate_focus": 0.2,
        "fate_authority": 0.3,
        "fate_tribe": 0.25,
        "fate_emotion": 0.25,
        "cta_strength": "soft",
    },
    {
        "name": "Feature → Outcome Map",
        "description": "Maps specific features to specific outcomes",
        "template_type": "post",
        "awareness_level": "product_aware",
        "prompt_text": """Map {offer} features to outcomes for {icp}.

Hook: "Here's exactly what each part of {offer} does for you..."

Feature mapping:
- {feature_1} → {outcome_1}
  Why it matters: {reason_1}

- {feature_2} → {outcome_2}
  Why it matters: {reason_2}

- {feature_3} → {outcome_3}
  Why it matters: {reason_3}

End with: "Everything works together to help you {main_outcome}."

Tone: Educational, benefit-focused, clear
Length: 250-300 words""",
        "fate_focus": 0.4,
        "fate_authority": 0.25,
        "fate_tribe": 0.15,
        "fate_emotion": 0.2,
        "cta_strength": "direct",
    },
    {
        "name": "Objection Handler",
        "description": "Addresses the main objection preventing purchase",
        "template_type": "post",
        "awareness_level": "product_aware",
        "prompt_text": """Address the objection: "{objection}" for {icp} considering {offer}.

Hook: "I get asked this all the time: '{objection}'"

Structure:
1. Acknowledge: Why this concern makes sense
2. Reframe: What's actually happening
3. Evidence: Proof this isn't an issue
4. Guarantee: How we de-risk it

Use social proof from {testimonial_source}.

End with: "Still unsure? Here's what to do..."

Tone: Understanding, reassuring, proof-based
Length: 250-300 words""",
        "fate_focus": 0.25,
        "fate_authority": 0.35,
        "fate_tribe": 0.2,
        "fate_emotion": 0.2,
        "cta_strength": "direct",
    },
    {
        "name": "Before/After Transformation",
        "description": "Shows the complete transformation your product enables",
        "template_type": "post",
        "awareness_level": "product_aware",
        "prompt_text": """Show the before/after transformation with {offer} for {icp}.

Hook: "The difference {offer} makes..."

BEFORE using {offer}:
- {before_point_1}
- {before_point_2}
- {before_point_3}

AFTER using {offer}:
- {after_point_1}
- {after_point_2}
- {after_point_3}

Timeline: {transformation_timeframe}

Include one specific customer example: {customer_name}

Tone: Transformative, visual, contrast-driven
Length: 200-250 words""",
        "fate_focus": 0.2,
        "fate_authority": 0.25,
        "fate_tribe": 0.25,
        "fate_emotion": 0.3,
        "cta_strength": "direct",
    },
    {
        "name": "Walkthrough Demo",
        "description": "Step-by-step walkthrough of using your product",
        "template_type": "post",
        "awareness_level": "product_aware",
        "prompt_text": """Create a walkthrough of {icp} using {offer} to achieve {outcome}.

Hook: "Here's exactly how to use {offer} to {outcome}..."

Steps:
1. {step_1} - Takes {time_1}
   What you'll see: {result_1}

2. {step_2} - Takes {time_2}
   What you'll see: {result_2}

3. {step_3} - Takes {time_3}
   What you'll see: {result_3}

Total time: {total_time}
Difficulty: {difficulty_level}

Tone: Tutorial, step-by-step, beginner-friendly
Length: 250-300 words""",
        "fate_focus": 0.45,
        "fate_authority": 0.25,
        "fate_tribe": 0.1,
        "fate_emotion": 0.2,
        "cta_strength": "direct",
    },
    {
        "name": "Competitive Positioning",
        "description": "Shows why your solution is different from alternatives",
        "template_type": "post",
        "awareness_level": "product_aware",
        "prompt_text": """Position {offer} against {competitor} for {icp}.

Hook: "{offer} vs {competitor}: What's actually different?"

Comparison:
- Approach: How each works differently
- Best for: Who should choose each
- Price: Cost comparison with context
- Results: Timeline and outcome differences
- Philosophy: Different beliefs

Be fair but clear about your advantages.

End with: "Choose {offer} if {criteria}."

Tone: Comparative, fair, differentiated
Length: 300-350 words""",
        "fate_focus": 0.35,
        "fate_authority": 0.35,
        "fate_tribe": 0.15,
        "fate_emotion": 0.15,
        "cta_strength": "direct",
    },

    # ===================================================
    # MOST-AWARE TEMPLATES (4)
    # ===================================================
    {
        "name": "Offer Reminder",
        "description": "Simple reminder of your offer with CTA",
        "template_type": "post",
        "awareness_level": "most_aware",
        "prompt_text": """Remind {icp} about {offer}.

Hook: "{offer} is open. Here's what you get..."

Include:
- What it is: {one_sentence_description}
- Who it's for: {ideal_customer}
- What's included: {deliverables}
- Price: {price}
- Timeline: {delivery_timeline}

Strong, clear CTA: {cta_text}

Tone: Direct, clear, no-nonsense
Length: 150-200 words""",
        "fate_focus": 0.3,
        "fate_authority": 0.25,
        "fate_tribe": 0.2,
        "fate_emotion": 0.25,
        "cta_strength": "direct",
    },
    {
        "name": "Bonus & Deadline",
        "description": "Highlights limited-time bonus or deadline",
        "template_type": "post",
        "awareness_level": "most_aware",
        "prompt_text": """Announce a bonus or deadline for {offer}.

Hook: "{deadline_or_bonus_announcement}"

Details:
- What's ending: {what_expires}
- When it ends: {deadline}
- What you get if you act now: {bonus_items}
- What you lose if you wait: {loss}

Create urgency without manipulation.

CTA: {cta_text} - {cta_link}

Tone: Urgent, value-focused, clear
Length: 150-200 words""",
        "fate_focus": 0.25,
        "fate_authority": 0.2,
        "fate_tribe": 0.2,
        "fate_emotion": 0.35,
        "cta_strength": "direct",
    },
    {
        "name": "Guarantee & Risk Reversal",
        "description": "Emphasizes the guarantee to remove final hesitation",
        "template_type": "post",
        "awareness_level": "most_aware",
        "prompt_text": """Highlight the guarantee for {offer}.

Hook: "Still on the fence about {offer}? Here's our guarantee..."

Guarantee details:
- What we guarantee: {guarantee_promise}
- How long: {guarantee_period}
- What happens if you're not satisfied: {refund_process}
- Why we can offer this: {confidence_reason}

Include testimonial: {testimonial}

CTA: Try {offer} risk-free: {cta_link}

Tone: Reassuring, confident, de-risking
Length: 200-250 words""",
        "fate_focus": 0.2,
        "fate_authority": 0.35,
        "fate_tribe": 0.15,
        "fate_emotion": 0.3,
        "cta_strength": "direct",
    },
    {
        "name": "Exactly What You Get",
        "description": "Complete breakdown of all deliverables",
        "template_type": "post",
        "awareness_level": "most_aware",
        "prompt_text": """List everything included in {offer}.

Hook: "Here's exactly what you get with {offer}..."

Deliverables:
1. {deliverable_1} - Value: ${value_1}
2. {deliverable_2} - Value: ${value_2}
3. {deliverable_3} - Value: ${value_3}
4. {deliverable_4} - Value: ${value_4}

Total value: ${total_value}
Your price: ${actual_price}

Timeline: When you get each component

Strong CTA: {cta_text} - {cta_link}

Tone: Value-stacking, comprehensive, clear
Length: 250-300 words""",
        "fate_focus": 0.35,
        "fate_authority": 0.25,
        "fate_tribe": 0.15,
        "fate_emotion": 0.25,
        "cta_strength": "direct",
    },
]


async def seed_templates():
    """Seed the database with content templates"""

    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
    )

    logger.info(f"🌱 Seeding content templates to {db_url}")

    engine = create_engine(db_url)

    created_count = 0
    updated_count = 0

    with Session(engine) as session:
        for template_data in TEMPLATES:
            # Check if template with this name already exists
            existing = session.query(ContentTemplate).filter(
                ContentTemplate.name == template_data["name"]
            ).first()

            if existing:
                logger.info(f"⏭️  Template '{template_data['name']}' already exists, skipping")
                updated_count += 1
                continue

            # Create new template
            template = ContentTemplate(
                name=template_data["name"],
                description=template_data["description"],
                template_type=template_data["template_type"],
                prompt_text=template_data["prompt_text"],
                fate_focus=template_data["fate_focus"],
                fate_authority=template_data["fate_authority"],
                fate_tribe=template_data["fate_tribe"],
                fate_emotion=template_data["fate_emotion"],
                awareness_level=template_data["awareness_level"],
                cta_strength=template_data["cta_strength"],
                is_active=True,
                created_by="system_seed"
            )

            # Extract required variables
            import re
            pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
            variables = list(set(re.findall(pattern, template.prompt_text)))
            template.required_variables = variables

            session.add(template)
            created_count += 1
            logger.success(f"✓ Created template: {template.name} ({template.awareness_level})")

        session.commit()

    logger.success(f"""
╔══════════════════════════════════════════╗
║  Template Seeding Complete!              ║
╠══════════════════════════════════════════╣
║  Created: {created_count:2d} templates                   ║
║  Skipped: {updated_count:2d} (already exist)             ║
║  Total:   {created_count + updated_count:2d} templates                   ║
╚══════════════════════════════════════════╝

Templates by Awareness Level:
- Problem-Aware:  8 templates
- Solution-Aware: 7 templates
- Product-Aware:  6 templates
- Most-Aware:     4 templates

All templates support variable substitution using {{variable}} syntax.

Use the API to:
- List templates: GET /api/templates
- Create posts: POST /api/templates/render
- Fork winners: POST /api/templates/{{id}}/fork
""")


if __name__ == "__main__":
    asyncio.run(seed_templates())
