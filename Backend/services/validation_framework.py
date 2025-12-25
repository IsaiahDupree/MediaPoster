"""
Comprehensive Validation Framework
==================================
Validates all components of the application before they're used.
Provides pre-flight checks for critical operations.
"""
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio
from loguru import logger


class ValidationSeverity(Enum):
    """Severity levels for validation issues"""
    CRITICAL = "critical"  # Will definitely cause failure
    WARNING = "warning"     # May cause issues but might work
    INFO = "info"           # Informational only


@dataclass
class ValidationIssue:
    """A single validation issue"""
    component: str
    severity: ValidationSeverity
    message: str
    details: Optional[str] = None
    fix_suggestion: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of validating a component"""
    component: str
    valid: bool = True
    issues: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    validated_at: datetime = field(default_factory=datetime.now)
    
    def add_issue(self, severity: ValidationSeverity, message: str, 
                  details: Optional[str] = None, fix_suggestion: Optional[str] = None,
                  metadata: Optional[Dict[str, Any]] = None):
        """Add a validation issue"""
        issue = ValidationIssue(
            component=self.component,
            severity=severity,
            message=message,
            details=details,
            fix_suggestion=fix_suggestion,
            metadata=metadata or {}
        )
        if severity == ValidationSeverity.CRITICAL:
            self.issues.append(issue)
            self.valid = False
        else:
            self.warnings.append(issue)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "valid": self.valid,
            "issues": [
                {
                    "severity": issue.severity.value,
                    "message": issue.message,
                    "details": issue.details,
                    "fix_suggestion": issue.fix_suggestion,
                    "metadata": issue.metadata
                }
                for issue in self.issues
            ],
            "warnings": [
                {
                    "severity": issue.severity.value,
                    "message": issue.message,
                    "details": issue.details,
                    "fix_suggestion": issue.fix_suggestion,
                    "metadata": issue.metadata
                }
                for issue in self.warnings
            ],
            "metadata": self.metadata,
            "validated_at": self.validated_at.isoformat()
        }


class ValidationFramework:
    """Main validation framework that orchestrates all validators"""
    
    def __init__(self):
        self.validators: Dict[str, Callable] = {}
        self.register_default_validators()
    
    def register_validator(self, name: str, validator_func: Callable):
        """Register a validator function"""
        self.validators[name] = validator_func
    
    async def validate_all(self, components: Optional[List[str]] = None) -> Dict[str, ValidationResult]:
        """
        Validate all registered components or specific ones.
        
        Args:
            components: List of component names to validate. If None, validates all.
        
        Returns:
            Dictionary mapping component names to validation results
        """
        components_to_validate = components or list(self.validators.keys())
        results = {}
        
        # Run validations in parallel
        tasks = []
        for component in components_to_validate:
            if component in self.validators:
                tasks.append(self._run_validator(component, self.validators[component]))
        
        validation_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for component, result in zip(components_to_validate, validation_results):
            if isinstance(result, Exception):
                # Validator itself failed
                validation_result = ValidationResult(
                    component=component,
                    valid=False
                )
                validation_result.add_issue(
                    ValidationSeverity.CRITICAL,
                    f"Validator failed: {str(result)}",
                    details=str(result)
                )
                results[component] = validation_result
            else:
                results[component] = result
        
        return results
    
    async def _run_validator(self, component: str, validator_func: Callable) -> ValidationResult:
        """Run a single validator and handle errors"""
        try:
            if asyncio.iscoroutinefunction(validator_func):
                return await validator_func()
            else:
                return validator_func()
        except Exception as e:
            logger.error(f"Validator {component} failed: {e}", exc_info=True)
            result = ValidationResult(component=component, valid=False)
            result.add_issue(
                ValidationSeverity.CRITICAL,
                f"Validator error: {str(e)}",
                details=str(e)
            )
            return result
    
    def register_default_validators(self):
        """Register all default validators"""
        from services.validators import (
            validate_configuration,
            validate_database,
            validate_external_apis,
            validate_social_accounts,
            validate_scheduled_posts,
            validate_narrative_setup,
            validate_experiment_setup,
            validate_file_system,
            validate_event_bus,
            validate_media_processing
        )
        
        self.register_validator("configuration", validate_configuration)
        self.register_validator("database", validate_database)
        self.register_validator("external_apis", validate_external_apis)
        self.register_validator("social_accounts", validate_social_accounts)
        self.register_validator("scheduled_posts", validate_scheduled_posts)
        self.register_validator("narrative_setup", validate_narrative_setup)
        self.register_validator("experiment_setup", validate_experiment_setup)
        self.register_validator("file_system", validate_file_system)
        self.register_validator("event_bus", validate_event_bus)
        self.register_validator("media_processing", validate_media_processing)


# Global instance
_framework_instance: Optional[ValidationFramework] = None


def get_validation_framework() -> ValidationFramework:
    """Get the global validation framework instance"""
    global _framework_instance
    if _framework_instance is None:
        _framework_instance = ValidationFramework()
    return _framework_instance

