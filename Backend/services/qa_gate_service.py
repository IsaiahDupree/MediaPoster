"""
QA Gate Service (OPS-009)
==========================
Quality assurance gate for generated content before publishing.

Checks:
1. FATE Score Validation - Ensure minimum FATE scores
2. Awareness Match - Verify content matches target awareness level
3. Length Constraints - Check character/word limits for platform
4. Forbidden Content - Detect banned phrases, topics
5. CTA Presence - Ensure call-to-action exists
6. Link Validation - Verify shortlinks/URLs are present and valid

Gate Result:
- PASS: Content approved for publishing
- WARN: Issues detected but not blocking
- FAIL: Critical issues, reject content

Usage:
    qa_gate = QAGateService()
    result = qa_gate.check(
        content="Generated content...",
        template_id="tpl_001",
        awareness_level=2,
        platform="x",
        fate_scores={"F": 0.75, "A": 0.68, "T": 0.82, "E": 0.71}
    )

    if result.status == "PASS":
        # Publish content
    elif result.status == "WARN":
        # Publish with warnings
    else:
        # Reject content
"""

import re
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field
from loguru import logger


class QAStatus(str, Enum):
    """QA gate status"""
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class QAIssue(BaseModel):
    """QA issue detected"""
    severity: str = Field(..., description="error|warning|info")
    category: str = Field(..., description="fate|awareness|length|forbidden|cta|link")
    message: str = Field(..., description="Human-readable issue description")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class QAResult(BaseModel):
    """QA gate result"""
    status: QAStatus
    passed: bool
    issues: List[QAIssue] = Field(default_factory=list)
    scores: Dict[str, float] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PlatformConstraints(BaseModel):
    """Platform-specific constraints"""
    platform: str
    max_length: int
    recommended_length: int
    requires_media: bool = False
    supports_links: bool = True


# Platform constraints
PLATFORM_CONSTRAINTS = {
    "x": PlatformConstraints(platform="x", max_length=280, recommended_length=240, supports_links=True),
    "twitter": PlatformConstraints(platform="twitter", max_length=280, recommended_length=240, supports_links=True),
    "instagram": PlatformConstraints(platform="instagram", max_length=2200, recommended_length=150, requires_media=True),
    "tiktok": PlatformConstraints(platform="tiktok", max_length=2200, recommended_length=100, requires_media=True),
    "youtube": PlatformConstraints(platform="youtube", max_length=5000, recommended_length=200, supports_links=True),
    "threads": PlatformConstraints(platform="threads", max_length=500, recommended_length=200, supports_links=True),
    "linkedin": PlatformConstraints(platform="linkedin", max_length=3000, recommended_length=150, supports_links=True),
}


class QAGateService:
    """
    QA Gate Service

    Validates generated content before publishing.
    Checks FATE scores, awareness level, platform constraints, and content quality.

    Usage:
        qa_gate = QAGateService.get_instance()
        result = qa_gate.check(content, template_id, awareness_level, platform, fate_scores)
    """

    _instance: Optional["QAGateService"] = None

    # Minimum FATE scores (can be overridden per template)
    DEFAULT_MIN_FATE_SCORES = {
        "F": 0.3,  # Minimum focus score
        "A": 0.2,  # Minimum authority score
        "T": 0.2,  # Minimum tribe score
        "E": 0.3,  # Minimum emotion score
    }

    # Forbidden patterns (banned phrases, topics)
    FORBIDDEN_PATTERNS = [
        r'\bget\s+rich\s+quick\b',
        r'\bguaranteed\s+\w+\b',
        r'\b100%\s+free\b',
        r'\bno\s+risk\b',
        r'\bunlimited\s+money\b',
        r'\blose\s+weight\s+overnight\b',
        r'\bmiracle\s+cure\b',
        r'\bmake\s+money\s+fast\b',
        r'\bwork\s+from\s+home\s+opportunity\b',
        r'\bbe\s+your\s+own\s+boss\b',
        # Add more as needed
    ]

    # Awareness level indicators (for validation)
    AWARENESS_PATTERNS = {
        1: [r'\bimagine\b', r'\bwhat\s+if\b', r'\bstory\b'],  # Unaware - story-driven
        2: [r'\bproblem\b', r'\bpain\b', r'\bfrustration\b', r'\bstruggl'],  # Problem-aware
        3: [r'\bsolution\b', r'\bapproach\b', r'\bhow\s+to\b', r'\bmethod\b'],  # Solution-aware
        4: [r'\bour\s+product\b', r'\bthis\s+tool\b', r'\bwe\s+help\b', r'\bfeatures?\b'],  # Product-aware
        5: [r'\bbuy\s+now\b', r'\bget\s+started\b', r'\btry\s+it\b', r'\bclaim\b'],  # Most-aware
    }

    def __init__(self, db=None):
        """Initialize QA gate service"""
        if QAGateService._instance is not None:
            raise RuntimeError("Use QAGateService.get_instance()")
        self.db = db
        self.forbidden_regexes = [re.compile(pattern, re.IGNORECASE) for pattern in self.FORBIDDEN_PATTERNS]
        logger.info("🛡️ QA Gate Service initialized")

    @classmethod
    def get_instance(cls, db=None) -> "QAGateService":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
            cls._instance.db = db
            cls._instance.forbidden_regexes = [re.compile(pattern, re.IGNORECASE) for pattern in cls.FORBIDDEN_PATTERNS]
            logger.info("🛡️ QA Gate Service initialized")
        return cls._instance

    async def check(
        self,
        content: Dict[str, Any]
    ) -> QAResult:
        """
        Check content quality

        Args:
            content: Content dict with:
                - text: Generated content to check
                - fate_scores: Dict with FATE scores (focus, authority, tribe, emotion)
                - awareness_level: Classified awareness level (1-5)
                - target_awareness: Target awareness level (1-5)
                - platform: Target platform
                - template_id: Template ID (optional)
                - intent: Content intent (optional)

        Returns:
            QA result with status and issues
        """
        text = content.get("text", "")
        fate_scores = content.get("fate_scores", {})
        awareness_level = content.get("awareness_level", 0)
        target_awareness = content.get("target_awareness", awareness_level)
        platform = content.get("platform", "twitter")
        template_id = content.get("template_id", "")
        intent = content.get("intent")

        logger.info(f"🛡️ QA check | Platform: {platform} | Awareness: {awareness_level}")

        issues = []

        # Check 0: Empty content
        if not text or len(text.strip()) == 0:
            issues.append(QAIssue(
                severity="error",
                category="length",
                message="Content cannot be empty",
                details={"length": len(text)}
            ))

        # Check 1: FATE Score Validation
        if fate_scores:
            fate_issues = self._check_fate_scores(fate_scores)
            issues.extend(fate_issues)

        # Check 2: Awareness Level Match
        if awareness_level > 0 and target_awareness > 0:
            awareness_issues = self._check_awareness_match(text, target_awareness, awareness_level)
            issues.extend(awareness_issues)

        # Check 3: Platform Length Constraints
        length_issues = self._check_length(text, platform)
        issues.extend(length_issues)

        # Check 4: Forbidden Content
        forbidden_issues = self._check_forbidden_content(text)
        issues.extend(forbidden_issues)

        # Check 5: CTA Presence
        cta_issues = self._check_cta_presence(text, awareness_level)
        issues.extend(cta_issues)

        # Check 6: Link Validation
        link_issues = self._check_links(text, platform, intent)
        issues.extend(link_issues)

        # Determine status
        has_errors = any(issue.severity == "error" for issue in issues)
        has_warnings = any(issue.severity == "warning" for issue in issues)

        if has_errors:
            status = QAStatus.FAIL
            passed = False
        elif has_warnings:
            status = QAStatus.WARN
            passed = True  # Can still publish with warnings
        else:
            status = QAStatus.PASS
            passed = True

        logger.info(f"✓ QA check complete | Status: {status.value} | Issues: {len(issues)}")

        return QAResult(
            status=status,
            passed=passed,
            issues=issues,
            scores=fate_scores or {},
            metadata={
                "template_id": template_id,
                "awareness_level": awareness_level,
                "target_awareness": target_awareness,
                "platform": platform,
                "content_length": len(text)
            }
        )

    def _check_fate_scores(self, fate_scores: Dict[str, float]) -> List[QAIssue]:
        """Check if FATE scores meet minimum thresholds"""
        issues = []

        # Normalize FATE score keys (support both "F"/"focus", "A"/"authority", etc.)
        normalized_scores = {}
        for key, value in fate_scores.items():
            key_lower = key.lower()
            if key_lower in ["f", "focus"]:
                normalized_scores["F"] = value
            elif key_lower in ["a", "authority"]:
                normalized_scores["A"] = value
            elif key_lower in ["t", "tribe"]:
                normalized_scores["T"] = value
            elif key_lower in ["e", "emotion"]:
                normalized_scores["E"] = value

        for element, min_score in self.DEFAULT_MIN_FATE_SCORES.items():
            actual_score = normalized_scores.get(element, 0.0)

            if actual_score < min_score:
                issues.append(QAIssue(
                    severity="warning",
                    category="fate",
                    message=f"Low {element} score: {actual_score:.2f} (minimum: {min_score:.2f})",
                    details={"element": element, "score": actual_score, "minimum": min_score}
                ))

        return issues

    def _check_awareness_match(self, content: str, target: int, classified: int) -> List[QAIssue]:
        """Check if classified awareness matches target"""
        issues = []

        if abs(classified - target) > 1:
            issues.append(QAIssue(
                severity="warning",
                category="awareness",
                message=f"Awareness mismatch: target {target}, classified as {classified}",
                details={"target": target, "classified": classified, "difference": abs(classified - target)}
            ))

        # Check for awareness indicators
        if target in self.AWARENESS_PATTERNS:
            patterns = self.AWARENESS_PATTERNS[target]
            matches = sum(1 for pattern in patterns if re.search(pattern, content, re.IGNORECASE))

            if matches == 0:
                issues.append(QAIssue(
                    severity="info",
                    category="awareness",
                    message=f"No clear awareness level {target} indicators detected",
                    details={"target": target, "matches": matches}
                ))

        return issues

    def _check_length(self, content: str, platform: str) -> List[QAIssue]:
        """Check platform length constraints"""
        issues = []

        constraints = PLATFORM_CONSTRAINTS.get(platform.lower())
        if not constraints:
            logger.warning(f"No constraints defined for platform: {platform}")
            return issues

        content_length = len(content)

        # Check max length
        if content_length > constraints.max_length:
            issues.append(QAIssue(
                severity="error",
                category="length",
                message=f"Content length exceeds maximum: {content_length} chars (max: {constraints.max_length})",
                details={"length": content_length, "max": constraints.max_length, "overflow": content_length - constraints.max_length}
            ))

        # Check recommended length
        elif content_length > constraints.recommended_length:
            issues.append(QAIssue(
                severity="info",
                category="length",
                message=f"Content exceeds recommended length: {content_length} chars (recommended: {constraints.recommended_length})",
                details={"length": content_length, "recommended": constraints.recommended_length}
            ))

        return issues

    def _check_forbidden_content(self, content: str) -> List[QAIssue]:
        """Check for forbidden phrases/patterns"""
        issues = []

        for regex in self.forbidden_regexes:
            if regex.search(content):
                issues.append(QAIssue(
                    severity="error",
                    category="forbidden",
                    message=f"Forbidden pattern detected: {regex.pattern}",
                    details={"pattern": regex.pattern}
                ))

        return issues

    def _check_cta_presence(self, content: str, awareness_level: int) -> List[QAIssue]:
        """Check for call-to-action presence"""
        issues = []

        # CTA patterns
        cta_patterns = [
            r'\bclick\b',
            r'\btry\b',
            r'\bget\b',
            r'\blearn\s+more\b',
            r'\bsign\s+up\b',
            r'\bcheck\s+out\b',
            r'\bvisit\b',
            r'\bdiscover\b',
            r'\bstart\b',
            r'\bjoin\b',
            r'\bdownload\b',
        ]

        has_cta = any(re.search(pattern, content, re.IGNORECASE) for pattern in cta_patterns)

        # Higher awareness levels should have stronger CTAs
        if awareness_level >= 4 and not has_cta:
            issues.append(QAIssue(
                severity="warning",
                category="cta",
                message=f"No clear CTA detected for awareness level {awareness_level}",
                details={"awareness_level": awareness_level}
            ))

        return issues

    def _check_links(self, content: str, platform: str, intent: Optional[str] = None) -> List[QAIssue]:
        """Check for link presence and validity"""
        issues = []

        constraints = PLATFORM_CONSTRAINTS.get(platform.lower())
        if not constraints or not constraints.supports_links:
            return issues

        # URL pattern
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, content)

        # Check for links - warn if lead_generation intent but no link
        if intent == "lead_generation" and not urls:
            issues.append(QAIssue(
                severity="warning",
                category="link",
                message="Lead generation content lacks URL/link",
                details={"platform": platform, "intent": intent}
            ))
        elif not urls:
            issues.append(QAIssue(
                severity="info",
                category="link",
                message="No links detected in content",
                details={"platform": platform}
            ))

        return issues


# Singleton
_qa_gate_instance = None

def get_qa_gate_service() -> QAGateService:
    """Get singleton QA gate service"""
    global _qa_gate_instance
    if _qa_gate_instance is None:
        _qa_gate_instance = QAGateService()
    return _qa_gate_instance
