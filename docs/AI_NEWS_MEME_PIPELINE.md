# AI News-to-Meme Pipeline Plan

## 1. Overall Flow (End-to-End)
**Goal:** Daily automated creation of AI news meme videos featuring you (Isaiah) and cat variants, optimized for different video models (Sora, Veo 3, NanoBanana).

**Daily Loop:**
1.  **Pick the Story:** Pull top AI news from APIs (NewsAPI, NewsData) and YouTube channels.
2.  **Distill into "Memeable Beats":** LLM converts news into a script with a core conflict, villain, and protagonist.
3.  **Generate "Multi-Model Prompt Pack":** Create prompt variations for:
    *   **Human-Isaiah Meme:** You as protagonist.
    *   **Cat Meme:** Cat versions of the same roles.
    *   **Model Variants:** Tailored text prompts for Sora, Veo 3, NanoBanana.
4.  **Render Videos:** Call video generation APIs (NanoBanana, etc.).
5.  **Publish & Log:** Upload to TikTok/Reels/Shorts via Blotato and log performance.
6.  **Scoreboard:** Track which model/format wins over time.

---

## 2. Data Model: "Story Package"
Object representing a single chosen news story.

```json
{
  "id": "ai-news-2025-11-20-001",
  "source": {
    "type": "article",
    "url": "https://example.com/ai-story",
    "title": "Anthropic Releases New Claude Model",
    "primary_entities": ["Anthropic", "Claude", "AI safety"]
  },
  "analysis": {
    "serious_summary": "...",
    "core_conflict": "open-source vs closed AI power",
    "stakes_for_viewer": "how this affects solo builders and agencies",
    "emotion": "excited but cautiously skeptical"
  },
  "roles": {
    "protagonist": "Isaiah",
    "antagonists": ["Corporate AI Overlord", "Regulation Chaos"],
    "neutral": ["Confused friend", "ChatGPT-using normie"]
  }
}
```

---

## 3. Script Structure (Isaiah as Protagonist)
**Format:** 15-30s video, no punctuation (spoken lines).

**Beats:**
1.  **Cold Open (Hook):** Reaction to headline.
2.  **Set Up Conflict:** Villain's action.
3.  **Relatable Translation:** What it means for the viewer.
4.  **Punchline/Twist:** Visual gag or meme moment.
5.  **Soft CTA:** "Follow for real breakdowns."

**Example Script:**
```text
scene 1 hook
isaiah
bro this ai headline sounds like a side quest from a dystopian video game

antagonist corporate ai overlord
we are totally not replacing your job we are just augmenting it

isaiah
translation they are testing how much chaos they can ship before anyone notices
```

---

## 4. Multi-Model Prompt Pack
JSON object containing prompts tailored for specific video generation models.

```json
{
  "story_id": "ai-news-2025-11-20-001",
  "characters": {
    "isaiah_reference_image": "https://cdn.yoursite.com/isaiah-portrait-1.png",
    "antagonist_style": "sleek corporate villain in glowing blue boardroom",
    "neutral_friend_style": "casual hoodie gamer friend"
  },
  "models": {
    "sora_style": {
      "prompt": "15 second vertical video of Isaiah standing in a neon lit home office...",
      "duration_sec": 15,
      "aspect_ratio": "9:16"
    },
    "veo3_style": {
      "prompt": "dynamic handheld camera shot of Isaiah in a small apartment studio...",
      "duration_sec": 20,
      "aspect_ratio": "9:16"
    },
    "nanobanana_style": {
      "prompt": "closeup shot of Isaiah looking at a floating holographic news headline...",
      "duration_sec": 15,
      "aspect_ratio": "9:16"
    }
  }
}
```

---

## 5. Cat Meme Variant
Duplicate structure, mapped to cat roles.

*   **Protagonist:** IsaiahCat
*   **Antagonist:** Corporate Overlord Cat
*   **Neutral:** Confused House Cat

**Example Script:**
```text
scene 1
isaiahcat
human news says ai is coming for your job again

overlordcat
correction we are coming for your snacks and wifi password
```

---

## 6. Story Selection Automation
**Trigger:** Daily at 8am or on-demand.

**Sources:**
*   **NewsAPI:** Query "AI OR artificial intelligence OR large language model".
*   **YouTube API:** Watch specific channels ("Two Minute Papers", "Latent Space").

**Filtering:**
*   Must mention top entities (OpenAI, Google, etc.).
*   Must be < 24 hours old.
*   **LLM Scoring:** "Pick 1-3 stories that are most memeable and high stakes. Return `memeability_score`."

---

## 7. Automation Blueprint (Make.com / n8n)
1.  **Trigger:** New filtered story found.
2.  **LLM (Story -> Package):** Summarize, assign roles, identify conflict.
3.  **LLM (Package -> Script):** Generate Isaiah script and Cat script.
4.  **LLM (Script -> Prompt Pack):** Create JSON prompts for Sora/Veo/NanoBanana.
5.  **Video Generation:** Call NanoBanana API (and others) with prompts + reference images.
6.  **Asset Storage:** Save video/thumbnail to Drive/Supabase.
7.  **Publishing:** Post via Blotato (Isaiah version primary, Cat version reply/secondary).
8.  **Logging:** Record publish time, platform, and model used.

---

## 8. Performance Scoring
Track which model/format wins.

**Table:** `model_performance`
*   `story_id`
*   `model_name` (sora, veo3, cat_variant)
*   `platform`
*   `views`, `watch_pct`, `shares`, `saves`

**Meme Score Formula:**
`meme_score = 0.4 * normalized_watch_pct + 0.3 * normalized_shares + 0.3 * normalized_saves`

---

## 9. Next Steps
1.  **LLM Prompts:** Write the exact system prompts for the "Story -> Script" and "Script -> Prompt Pack" steps.
2.  **Supabase Schema:** Define tables for `stories`, `prompt_packs`, and `model_performance`.
