# Phase 3: Pre/Post Social Score + Coaching - Progress

## Status: ~50% Complete

### ✅ Completed Items

#### 1. Post-Social Score Calculation
**Status:** ✅ **COMPLETE**

**Implementation:**
- **Location:** `Backend/services/post_social_score.py`
- **API Endpoints:** `Backend/api/endpoints/post_social_score.py`

**Features:**
- ✅ **Post-social score calculation** (0-100 normalized score)
- ✅ **Follower count normalization** - Accounts for account size
- ✅ **Platform behavior normalization** - Platform-specific baselines
- ✅ **Time-since-posting normalization** - Time decay factors
- ✅ **"Top X% of your Reels" calculation** - Percentile ranking

**Normalization Details:**

1. **Follower Count Normalization (40% weight)**
   - Calculates expected views/engagement based on follower count
   - Compares actual vs expected performance
   - Accounts for larger accounts getting more views naturally

2. **Platform Behavior Normalization (35% weight)**
   - Platform-specific baselines:
     - Instagram Reels: 500 views/1k followers, 5% engagement
     - TikTok: 800 views/1k followers, 8% engagement
     - YouTube Shorts: 400 views/1k followers, 4% engagement
   - Scores based on how much above/below baseline

3. **Time-Since-Posting Normalization (25% weight)**
   - Time decay factors:
     - 0-6h: 1.0x (peak engagement)
     - 6-24h: 0.9x
     - 24-48h: 0.7x
     - 48-72h: 0.5x
     - 72h+: 0.3x
   - Earlier engagement = better score

4. **Percentile Ranking**
   - Compares post to user's other content
   - Returns "Top X% of your Reels" description
   - Calculates rank and percentile

**API Endpoints:**
- `GET /api/post-social-score/post/{post_id}` - Get score for a post
- `POST /api/post-social-score/post/{post_id}/calculate` - Calculate and store score
- `GET /api/post-social-score/account/{account_id}/summary` - Get account summary

---

### ⚠️ In Progress

#### 2. Goals System UI
**Status:** ⚠️ **PARTIAL**

**Current State:**
- ✅ Basic Goals page exists (`Frontend/src/app/goals/page.tsx`)
- ✅ `posting_goals` table exists in database
- ⚠️ Missing goal selection UI
- ⚠️ Missing goal-based recommendations
- ⚠️ Missing "Post 3 more videos like these" suggestions
- ⚠️ Missing format recommendations

**Next Steps:**
- Enhance Goals page with goal types
- Add goal-based recommendation engine
- Create recommendation UI components

#### 3. Coaching System
**Status:** ❌ **NOT STARTED**

**Required:**
- ❌ Coach screen/UI
- ❌ Chat interface for recommendations
- ❌ Content brief recommendations
- ❌ Script suggestions
- ❌ AI-powered coaching based on data

---

## Files Created

1. `Backend/services/post_social_score.py` - Post-social score calculation service
2. `Backend/api/endpoints/post_social_score.py` - API endpoints for post-social scores

---

## Next Steps

### Immediate (Week 1)
1. **Enhance Goals System UI**
   - Add goal type selection ("Grow followers", "Increase views", etc.)
   - Create goal-based recommendation engine
   - Display recommendations in Goals page

2. **Create Coaching System**
   - Build coach chat interface
   - Implement AI coaching service
   - Add content brief and script generation

### Short Term (Weeks 2-3)
3. **Integrate Post-Social Score into UI**
   - Display scores in analytics pages
   - Show percentile rankings
   - Compare pre vs post scores

4. **Goal-Based Recommendations**
   - "Post 3 more videos like these" suggestions
   - Format recommendations ("Try 9:16 + talking head")
   - Content strategy recommendations

---

## Testing

### Test Post-Social Score Calculation
```bash
# Calculate score for a post
curl http://localhost:5555/api/post-social-score/post/123

# Get account summary
curl http://localhost:5555/api/post-social-score/account/1/summary
```

---

## Known Issues

1. **Database Schema**: Post-social score needs to be stored in a dedicated column
2. **UI Integration**: Scores need to be displayed in analytics pages
3. **Goal Recommendations**: Recommendation engine needs implementation
4. **Coaching System**: Complete system needs to be built

---

## Phase 3 Completion: ~50%

**Remaining Work:**
- Goals System UI enhancements
- Goal-based recommendations
- Coaching System (complete)
- UI integration for post-social scores

**Estimated Time to 100%:** 2-3 weeks






