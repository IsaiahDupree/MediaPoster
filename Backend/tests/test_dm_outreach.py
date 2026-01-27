"""
Tests for DM Outreach System
Tests prospect discovery, DM list management, and outreach sequencing.
"""

import pytest
from datetime import datetime, timezone, date


class TestDMOutreachImports:
    """Test that all DM outreach components can be imported."""
    
    def test_dm_list_manager_imports(self):
        """Test DMListManager can be imported."""
        from services.dm_outreach import DMListManager, get_dm_list_manager
        assert DMListManager is not None
        assert get_dm_list_manager is not None
    
    def test_prospect_model_imports(self):
        """Test Prospect model can be imported."""
        from services.dm_outreach import Prospect, DMListEntry, Offer
        assert Prospect is not None
        assert DMListEntry is not None
        assert Offer is not None
    
    def test_enums_import(self):
        """Test enums can be imported."""
        from services.dm_outreach import (
            ProspectStatus,
            OutreachPhase,
            DiscoverySource
        )
        assert ProspectStatus is not None
        assert OutreachPhase is not None
        assert DiscoverySource is not None
    
    def test_outreach_sequencer_imports(self):
        """Test OutreachSequencer can be imported."""
        from services.dm_outreach import OutreachSequencer, get_outreach_sequencer
        assert OutreachSequencer is not None
        assert get_outreach_sequencer is not None
    
    def test_prospect_finder_imports(self):
        """Test ProspectFinder can be imported."""
        from services.dm_outreach import ProspectFinder, get_prospect_finder
        assert ProspectFinder is not None
        assert get_prospect_finder is not None
    
    def test_templates_import(self):
        """Test message templates can be imported."""
        from services.dm_outreach import TEMPLATES
        assert TEMPLATES is not None
        assert "introduction" in TEMPLATES
        assert "value" in TEMPLATES
        assert "relationship" in TEMPLATES
        assert "offer" in TEMPLATES
    
    def test_account_offers_import(self):
        """Test account offers mapping can be imported."""
        from services.dm_outreach import ACCOUNT_OFFERS
        assert ACCOUNT_OFFERS is not None
        assert "instagram" in ACCOUNT_OFFERS
        assert "tiktok" in ACCOUNT_OFFERS


class TestProspectModel:
    """Tests for Prospect dataclass."""
    
    def test_prospect_creation(self):
        """Test Prospect creation with defaults."""
        from services.dm_outreach import Prospect
        
        prospect = Prospect(
            platform="instagram",
            account_id=807,
            username="testuser"
        )
        
        assert prospect.id is not None
        assert prospect.platform == "instagram"
        assert prospect.account_id == 807
        assert prospect.username == "testuser"
        assert prospect.fit_score == 0
        assert prospect.qualified == False
    
    def test_prospect_to_dict(self):
        """Test Prospect serialization."""
        from services.dm_outreach import Prospect
        
        prospect = Prospect(
            platform="tiktok",
            account_id=710,
            username="creator123",
            display_name="Test Creator",
            fit_score=75,
            qualified=True
        )
        
        data = prospect.to_dict()
        
        assert "id" in data
        assert data["platform"] == "tiktok"
        assert data["username"] == "creator123"
        assert data["fit_score"] == 75
        assert data["qualified"] == True
    
    def test_prospect_with_full_context(self):
        """Test Prospect with all fields populated."""
        from services.dm_outreach import Prospect, DiscoverySource
        
        prospect = Prospect(
            platform="instagram",
            account_id=807,
            username="engaged_user",
            display_name="Engaged User",
            bio="Creator | Entrepreneur | Coach",
            follower_count=5000,
            source=DiscoverySource.COMMENT.value,
            source_comment="This is amazing! How did you do this?",
            fit_score=85,
            offer_match="coaching",
            qualified=True
        )
        
        assert prospect.follower_count == 5000
        assert prospect.source == "comment"
        assert prospect.offer_match == "coaching"


class TestDMListEntry:
    """Tests for DMListEntry dataclass."""
    
    def test_dm_list_entry_creation(self):
        """Test DMListEntry creation."""
        from services.dm_outreach import DMListEntry, ProspectStatus, OutreachPhase
        
        entry = DMListEntry(
            prospect_id="prospect123"
        )
        
        assert entry.id is not None
        assert entry.prospect_id == "prospect123"
        assert entry.status == ProspectStatus.NEW.value
        assert entry.phase == OutreachPhase.INTRODUCTION.value
    
    def test_dm_list_entry_to_dict(self):
        """Test DMListEntry serialization."""
        from services.dm_outreach import DMListEntry
        
        entry = DMListEntry(
            prospect_id="prospect456",
            status="nurturing",
            phase="relationship",
            trust_score=45
        )
        
        data = entry.to_dict()
        
        assert "id" in data
        assert data["status"] == "nurturing"
        assert data["phase"] == "relationship"
        assert data["trust_score"] == 45


class TestOfferModel:
    """Tests for Offer dataclass."""
    
    def test_offer_creation(self):
        """Test Offer creation."""
        from services.dm_outreach import Offer
        
        offer = Offer(
            name="1-on-1 Coaching",
            offer_type="coaching",
            price_range="$500-$5000"
        )
        
        assert offer.id is not None
        assert offer.name == "1-on-1 Coaching"
        assert offer.offer_type == "coaching"
        assert offer.is_active == True
    
    def test_offer_with_signals(self):
        """Test Offer with fit signals and disqualifiers."""
        from services.dm_outreach import Offer
        
        offer = Offer(
            name="Content Course",
            offer_type="course",
            fit_signals=["learning", "beginner", "how to start"],
            disqualifiers=["already expert", "just curious"]
        )
        
        assert "learning" in offer.fit_signals
        assert "already expert" in offer.disqualifiers


class TestProspectStatusEnum:
    """Tests for ProspectStatus enum."""
    
    def test_all_statuses_defined(self):
        """Test all prospect statuses are defined."""
        from services.dm_outreach import ProspectStatus
        
        expected = ["new", "contacted", "replied", "nurturing", "offer_ready", "converted", "archived"]
        actual = [s.value for s in ProspectStatus]
        
        for status in expected:
            assert status in actual


class TestOutreachPhaseEnum:
    """Tests for OutreachPhase enum."""
    
    def test_all_phases_defined(self):
        """Test all outreach phases are defined."""
        from services.dm_outreach import OutreachPhase
        
        expected = ["introduction", "value", "relationship", "offer"]
        actual = [p.value for p in OutreachPhase]
        
        for phase in expected:
            assert phase in actual


class TestDMListManager:
    """Tests for DMListManager operations."""
    
    def test_manager_initialization(self):
        """Test DMListManager initializes correctly."""
        from services.dm_outreach import DMListManager
        
        manager = DMListManager()
        assert manager is not None
        assert manager.engine is not None
    
    def test_manager_singleton(self):
        """Test get_dm_list_manager returns same instance."""
        from services.dm_outreach import get_dm_list_manager
        
        m1 = get_dm_list_manager()
        m2 = get_dm_list_manager()
        
        assert m1 is m2
    
    def test_add_prospect(self):
        """Test adding a prospect."""
        from services.dm_outreach import get_dm_list_manager, Prospect
        
        manager = get_dm_list_manager()
        
        prospect = Prospect(
            platform="instagram",
            account_id=807,
            username=f"test_prospect_{datetime.now().timestamp()}",
            display_name="Test Prospect",
            source="manual"
        )
        
        result = manager.add_prospect(prospect)
        assert result.id == prospect.id
    
    def test_get_stats(self):
        """Test getting outreach statistics."""
        from services.dm_outreach import get_dm_list_manager
        
        manager = get_dm_list_manager()
        stats = manager.get_stats()
        
        assert "total_in_list" in stats
        assert "total_prospects" in stats
        assert "by_status" in stats
        assert "by_phase" in stats


class TestOutreachSequencer:
    """Tests for OutreachSequencer."""
    
    def test_sequencer_initialization(self):
        """Test OutreachSequencer initializes correctly."""
        from services.dm_outreach import OutreachSequencer
        
        sequencer = OutreachSequencer()
        assert sequencer is not None
    
    def test_sequencer_singleton(self):
        """Test get_outreach_sequencer returns same instance."""
        from services.dm_outreach import get_outreach_sequencer
        
        s1 = get_outreach_sequencer()
        s2 = get_outreach_sequencer()
        
        assert s1 is s2
    
    def test_get_next_message_introduction(self):
        """Test getting next message for introduction phase."""
        from services.dm_outreach import get_outreach_sequencer
        
        sequencer = get_outreach_sequencer()
        
        suggestion = sequencer.get_next_message(
            phase="introduction",
            prospect_data={"username": "testuser", "display_name": "Test User"},
            conversation_history=[]
        )
        
        assert suggestion is not None
        assert suggestion.content is not None
        assert len(suggestion.content) > 10
        assert suggestion.phase == "introduction"
    
    def test_get_next_message_value(self):
        """Test getting next message for value phase."""
        from services.dm_outreach import get_outreach_sequencer
        
        sequencer = get_outreach_sequencer()
        
        suggestion = sequencer.get_next_message(
            phase="value",
            prospect_data={"username": "learner", "display_name": "Eager Learner"},
            conversation_history=[{"direction": "sent", "content": "Hey!"}]
        )
        
        assert suggestion is not None
        assert suggestion.phase == "value"
    
    def test_get_recommended_timing(self):
        """Test getting recommended timing."""
        from services.dm_outreach import get_outreach_sequencer
        
        sequencer = get_outreach_sequencer()
        
        timing = sequencer.get_recommended_timing(
            phase="introduction",
            last_interaction=None
        )
        
        assert "next_date" in timing
        assert "days_to_wait" in timing
        assert "optimal_hour" in timing
        assert "urgency" in timing
    
    def test_should_advance_phase_no(self):
        """Test phase advancement check - not ready."""
        from services.dm_outreach import get_outreach_sequencer
        
        sequencer = get_outreach_sequencer()
        
        result = sequencer.should_advance_phase(
            current_phase="introduction",
            interaction_count=1,
            trust_score=5
        )
        
        assert result["should_advance"] == False
    
    def test_should_advance_phase_yes(self):
        """Test phase advancement check - ready."""
        from services.dm_outreach import get_outreach_sequencer
        
        sequencer = get_outreach_sequencer()
        
        result = sequencer.should_advance_phase(
            current_phase="introduction",
            interaction_count=5,
            trust_score=30
        )
        
        assert result["should_advance"] == True
        assert result["next_phase"] == "value"
    
    def test_detect_offer_ready_signals(self):
        """Test detecting offer-ready signals."""
        from services.dm_outreach import get_outreach_sequencer
        
        sequencer = get_outreach_sequencer()
        
        messages = [
            {"direction": "received", "content": "I've been struggling with content creation"},
            {"direction": "received", "content": "How much do you charge for coaching?"},
        ]
        
        result = sequencer.detect_offer_ready_signals(messages)
        
        assert result["is_ready"] == True
        assert result["ready_score"] >= 2


class TestProspectFinder:
    """Tests for ProspectFinder."""
    
    def test_finder_initialization(self):
        """Test ProspectFinder initializes correctly."""
        from services.dm_outreach import ProspectFinder
        
        finder = ProspectFinder()
        assert finder is not None
    
    def test_finder_singleton(self):
        """Test get_prospect_finder returns same instance."""
        from services.dm_outreach import get_prospect_finder
        
        f1 = get_prospect_finder()
        f2 = get_prospect_finder()
        
        assert f1 is f2
    
    def test_get_account_info(self):
        """Test getting account info."""
        from services.dm_outreach import get_prospect_finder
        
        finder = get_prospect_finder()
        
        info = finder.get_account_info("instagram", 807)
        
        assert info["username"] == "@the_isaiah_dupree"
        assert "coaching" in info["offers"]
    
    def test_add_manual_prospect(self):
        """Test manually adding a prospect."""
        from services.dm_outreach import get_prospect_finder
        
        finder = get_prospect_finder()
        
        prospect = finder.add_manual_prospect(
            platform="twitter",
            account_id=4151,
            username=f"manual_test_{datetime.now().timestamp()}",
            display_name="Manual Test",
            bio="Entrepreneur building cool stuff",
            source_note="Found through Twitter engagement"
        )
        
        assert prospect is not None
        assert prospect.platform == "twitter"
        assert prospect.fit_score > 0
    
    def test_calculate_fit_score(self):
        """Test fit score calculation."""
        from services.dm_outreach import get_prospect_finder, Prospect
        
        finder = get_prospect_finder()
        
        prospect = Prospect(
            platform="instagram",
            account_id=807,
            username="high_fit_user",
            follower_count=5000,
            source="comment"
        )
        
        context = "I've been struggling with growing my business. Can you help me learn how to create better content?"
        
        score = finder._calculate_fit_score(prospect, context)
        
        assert score >= 50  # Should be a good fit
    
    def test_match_offer(self):
        """Test offer matching."""
        from services.dm_outreach import get_prospect_finder
        
        finder = get_prospect_finder()
        
        context = "I need help with my business strategy and scaling my team"
        available_offers = ["coaching", "course", "consulting"]
        
        matched = finder._match_offer(80, context, available_offers)
        
        assert matched == "consulting"  # Should match consulting signals


class TestDMOutreachAPI:
    """Tests for DM Outreach API endpoints."""
    
    def test_api_router_exists(self):
        """Test API router can be imported."""
        from api.endpoints.dm_outreach import router
        assert router is not None
    
    def test_prospect_endpoints_exist(self):
        """Test prospect management endpoints exist."""
        from api.endpoints.dm_outreach import (
            get_prospects,
            get_prospect,
            add_prospect,
            run_discovery
        )
        assert get_prospects is not None
        assert get_prospect is not None
        assert add_prospect is not None
        assert run_discovery is not None
    
    def test_list_endpoints_exist(self):
        """Test DM list endpoints exist."""
        from api.endpoints.dm_outreach import (
            get_dm_list,
            get_ready_to_contact,
            add_to_list,
            update_status,
            update_phase
        )
        assert get_dm_list is not None
        assert get_ready_to_contact is not None
        assert add_to_list is not None
        assert update_status is not None
        assert update_phase is not None
    
    def test_messaging_endpoints_exist(self):
        """Test messaging endpoints exist."""
        from api.endpoints.dm_outreach import (
            record_message,
            add_note,
            get_message_suggestion,
            check_phase_advancement
        )
        assert record_message is not None
        assert add_note is not None
        assert get_message_suggestion is not None
        assert check_phase_advancement is not None
    
    def test_offer_endpoints_exist(self):
        """Test offer management endpoints exist."""
        from api.endpoints.dm_outreach import (
            get_offers,
            create_offer,
            get_account_offers
        )
        assert get_offers is not None
        assert create_offer is not None
        assert get_account_offers is not None
    
    def test_stats_endpoints_exist(self):
        """Test statistics endpoints exist."""
        from api.endpoints.dm_outreach import (
            get_stats,
            get_funnel
        )
        assert get_stats is not None
        assert get_funnel is not None


class TestMessageTemplates:
    """Tests for message templates."""
    
    def test_introduction_templates_exist(self):
        """Test introduction templates exist."""
        from services.dm_outreach import TEMPLATES
        
        assert "first_touch" in TEMPLATES["introduction"]
        assert "follow_up" in TEMPLATES["introduction"]
        assert len(TEMPLATES["introduction"]["first_touch"]) >= 3
    
    def test_value_templates_exist(self):
        """Test value delivery templates exist."""
        from services.dm_outreach import TEMPLATES
        
        assert "share_resource" in TEMPLATES["value"]
        assert "check_in" in TEMPLATES["value"]
    
    def test_relationship_templates_exist(self):
        """Test relationship templates exist."""
        from services.dm_outreach import TEMPLATES
        
        assert "celebrate" in TEMPLATES["relationship"]
        assert "support" in TEMPLATES["relationship"]
        assert "personal" in TEMPLATES["relationship"]
    
    def test_offer_templates_exist(self):
        """Test offer templates exist."""
        from services.dm_outreach import TEMPLATES
        
        assert "soft_intro" in TEMPLATES["offer"]
        assert "direct" in TEMPLATES["offer"]


class TestAccountOffersMapping:
    """Tests for account-to-offer mapping."""
    
    def test_instagram_accounts_mapped(self):
        """Test Instagram accounts have offers."""
        from services.dm_outreach import ACCOUNT_OFFERS
        
        ig = ACCOUNT_OFFERS["instagram"]
        assert 807 in ig
        assert "offers" in ig[807]
    
    def test_tiktok_accounts_mapped(self):
        """Test TikTok accounts have offers."""
        from services.dm_outreach import ACCOUNT_OFFERS
        
        tt = ACCOUNT_OFFERS["tiktok"]
        assert 710 in tt
        assert "offers" in tt[710]
    
    def test_twitter_accounts_mapped(self):
        """Test Twitter accounts have offers."""
        from services.dm_outreach import ACCOUNT_OFFERS
        
        tw = ACCOUNT_OFFERS["twitter"]
        assert 4151 in tw
        assert "consulting" in tw[4151]["offers"]
