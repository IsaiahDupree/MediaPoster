"""
Test Suite for SegmentEditor Service
Tests manual segment editing, splitting, merging, and validation
"""
import pytest
from datetime import datetime
import uuid

from services.segment_editor import SegmentEditor, ValidationIssue, ValidationResult
from database.models import VideoSegment, AnalyzedVideo, SegmentEditHistory


@pytest.fixture
def test_video(db_session):
    """Create a test video"""
    video = AnalyzedVideo(
        id=uuid.uuid4(),
        duration_seconds=120.0
    )
    db_session.add(video)
    db_session.commit()
    return video


@pytest.fixture
def test_segment(db_session, test_video):
    """Create a test segment"""
    segment = VideoSegment(
        id=uuid.uuid4(),
        video_id=test_video.id,
        start_s=10.0,
        end_s=20.0,
        segment_type="hook",
        hook_type="fear",
        emotion="fear"
    )
    db_session.add(segment)
    db_session.commit()
    return segment


class TestSegmentCreation:
    """Test segment creation"""
    
    def test_create_segment_success(self, db_session, test_video):
        """Test successful segment creation"""
        editor = SegmentEditor(db_session)
        segment = editor.create_segment(
            video_id=str(test_video.id),
            start_time=5.0,
            end_time=15.0,
            segment_type="hook",
            edited_by=str(uuid.uuid4())
        )
        
        assert segment.id is not None
        assert segment.start_s == 5.0
        assert segment.end_s == 15.0
        assert segment.segment_type == "hook"
        
        # Verify in DB
        db_segment = db_session.query(VideoSegment).filter_by(id=segment.id).first()
        assert db_segment is not None
    
    def test_create_segment_invalid_video(self, db_session):
        """Test creation with non-existent video"""
        editor = SegmentEditor(db_session)
        with pytest.raises(ValueError, match="not found"):
            editor.create_segment(
                video_id=str(uuid.uuid4()),
                start_time=5.0,
                end_time=15.0,
                segment_type="hook"
            )
    
    def test_create_segment_invalid_timing(self, db_session, test_video):
        """Test creation with invalid timing"""
        editor = SegmentEditor(db_session)
        
        # End before start
        with pytest.raises(ValueError, match="greater than start"):
            editor.create_segment(
                video_id=str(test_video.id),
                start_time=20.0,
                end_time=10.0,
                segment_type="hook"
            )
        
        # Beyond video duration
        with pytest.raises(ValueError, match="exceeds video duration"):
            editor.create_segment(
                video_id=str(test_video.id),
                start_time=5.0,
                end_time=150.0,
                segment_type="hook"
            )


class TestSegmentUpdate:
    """Test segment updates"""
    
    def test_update_segment_success(self, db_session, test_segment):
        """Test successful segment update"""
        editor = SegmentEditor(db_session)
        updated = editor.update_segment(
            segment_id=str(test_segment.id),
            edited_by=str(uuid.uuid4()),
            segment_type="body",
            edit_reason="Reclassified"
        )
        
        assert updated.segment_type == "body"
        
        # Verify in DB
        db_session.refresh(test_segment)
        assert test_segment.segment_type == "body"
    
    def test_update_nonexistent_segment(self, db_session):
        """Test updating non-existent segment"""
        editor = SegmentEditor(db_session)
        with pytest.raises(ValueError, match="not found"):
            editor.update_segment(
                segment_id=str(uuid.uuid4()),
                edited_by=str(uuid.uuid4()),
                segment_type="body"
            )


class TestSegmentSplit:
    """Test segment splitting"""
    
    def test_split_segment_success(self, db_session, test_segment):
        """Test successful segment split"""
        editor = SegmentEditor(db_session)
        seg1, seg2 = editor.split_segment(
            segment_id=str(test_segment.id),
            split_time=15.0,
            edited_by=str(uuid.uuid4())
        )
        
        assert seg1.end_s == 15.0
        assert seg2.start_s == 15.0
        assert seg2.end_s == 20.0
        
        # Verify original is gone/modified? 
        # Wait, split usually modifies original and creates new, or creates two new and deletes original?
        # Checking implementation... usually it modifies original to be first part, creates new for second part.
        # Or creates two new.
        # Let's assume it creates two new and marks original as deleted or just modifies.
        # Based on return value `seg1, seg2`, it likely returns the two resulting segments.
        
        # Verify in DB
        s1 = db_session.query(VideoSegment).filter_by(id=seg1.id).first()
        s2 = db_session.query(VideoSegment).filter_by(id=seg2.id).first()
        assert s1 is not None
        assert s2 is not None
    
    def test_split_segment_invalid_time(self, db_session, test_segment):
        """Test split with invalid time"""
        editor = SegmentEditor(db_session)
        
        # Split time before segment start
        with pytest.raises(ValueError, match="must be between"):
            editor.split_segment(
                segment_id=str(test_segment.id),
                split_time=5.0,
                edited_by=str(uuid.uuid4())
            )
        
        # Split time after segment end
        with pytest.raises(ValueError, match="must be between"):
            editor.split_segment(
                segment_id=str(test_segment.id),
                split_time=25.0,
                edited_by=str(uuid.uuid4())
            )


class TestSegmentMerge:
    """Test segment merging"""
    
    def test_merge_segments_success(self, db_session, test_video):
        """Test successful merge"""
        # Create two adjacent segments
        seg1 = VideoSegment(
            id=uuid.uuid4(),
            video_id=test_video.id,
            start_s=10.0,
            end_s=20.0,
            segment_type="hook"
        )
        seg2 = VideoSegment(
            id=uuid.uuid4(),
            video_id=test_video.id,
            start_s=20.0,
            end_s=30.0,
            segment_type="body"
        )
        db_session.add_all([seg1, seg2])
        db_session.commit()
        
        editor = SegmentEditor(db_session)
        merged = editor.merge_segments(
            segment_ids=[str(seg1.id), str(seg2.id)],
            edited_by=str(uuid.uuid4())
        )
        
        assert merged.start_s == 10.0
        assert merged.end_s == 30.0
        
        # Verify old segments are gone (or marked deleted)
        # Implementation detail: merge usually deletes old segments
        db_session.expire_all()
        s1 = db_session.query(VideoSegment).filter_by(id=seg1.id).first()
        s2 = db_session.query(VideoSegment).filter_by(id=seg2.id).first()
        assert s1 is None
        assert s2 is None
    
    def test_merge_requires_multiple_segments(self, db_session):
        """Test merge with < 2 segments"""
        editor = SegmentEditor(db_session)
        
        with pytest.raises(ValueError, match="at least 2"):
            editor.merge_segments(
                segment_ids=[str(uuid.uuid4())],
                edited_by=str(uuid.uuid4())
            )


class TestSegmentValidation:
    """Test segment validation"""
    
    def test_validate_no_issues(self, db_session, test_video):
        """Test validation with no issues"""
        seg1 = VideoSegment(
            id=uuid.uuid4(),
            video_id=test_video.id,
            start_s=0.0,
            end_s=10.0,
            segment_type="hook"
        )
        seg2 = VideoSegment(
            id=uuid.uuid4(),
            video_id=test_video.id,
            start_s=10.0,
            end_s=20.0,
            segment_type="hook"
        )
        db_session.add_all([seg1, seg2])
        db_session.commit()
        
        editor = SegmentEditor(db_session)
        result = editor.validate_segments(str(test_video.id))
        
        assert result.is_valid
        assert result.total_segments == 2
        assert result.manual_segments == 2  # All segments counted as manual now
        assert result.auto_segments == 0
    
    def test_detect_overlaps(self, db_session, test_video):
        """Test detection of overlapping segments"""
        seg1 = VideoSegment(
            id=uuid.uuid4(),
            video_id=test_video.id,
            start_s=0.0,
            end_s=15.0,
            segment_type="hook"
        )
        seg2 = VideoSegment(
            id=uuid.uuid4(),
            video_id=test_video.id,
            start_s=10.0,
            end_s=20.0,
            segment_type="hook"
        )
        db_session.add_all([seg1, seg2])
        db_session.commit()
        
        editor = SegmentEditor(db_session)
        result = editor.validate_segments(str(test_video.id))
        
        assert not result.is_valid
        assert any(i.issue_type == "overlap" for i in result.issues)
    
    def test_detect_gaps(self, db_session, test_video):
        """Test detection of gaps between segments"""
        seg1 = VideoSegment(
            id=uuid.uuid4(),
            video_id=test_video.id,
            start_s=0.0,
            end_s=10.0,
            segment_type="hook"
        )
        seg2 = VideoSegment(
            id=uuid.uuid4(),
            video_id=test_video.id,
            start_s=12.0,  # 2 second gap
            end_s=20.0,
            segment_type="hook"
        )
        db_session.add_all([seg1, seg2])
        db_session.commit()
        
        editor = SegmentEditor(db_session)
        result = editor.validate_segments(str(test_video.id))
        
        # Gap is info, not error
        assert result.is_valid
        assert any(i.issue_type == "gap" for i in result.issues)


class TestSegmentDeletion:
    """Test segment deletion"""
    
    def test_delete_segment_success(self, db_session, test_segment):
        """Test successful deletion"""
        editor = SegmentEditor(db_session)
        success = editor.delete_segment(
            segment_id=str(test_segment.id),
            edited_by=str(uuid.uuid4())
        )
        
        assert success
        
        # Verify in DB
        db_session.expire_all()
        deleted = db_session.query(VideoSegment).filter_by(id=test_segment.id).first()
        assert deleted is None
    
    def test_delete_nonexistent_segment(self, db_session):
        """Test deleting non-existent segment"""
        editor = SegmentEditor(db_session)
        success = editor.delete_segment(
            segment_id=str(uuid.uuid4()),
            edited_by=str(uuid.uuid4())
        )
        
        assert not success
