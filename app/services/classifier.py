from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config.settings import Settings
from app.models.domain import CASE_TO_DEPARTMENT, CaseType, Department, Severity
from app.schemas.ticket import TicketRequest, TicketResponse
from app.services.audit_log import SQLiteAuditLog
from app.services.keyword_extraction import KeywordExtractor
from app.services.ml_classifier import MLPrediction, TfidfLogisticTicketClassifier
from app.services.preprocessing import TicketPreprocessor
from app.services.review import HumanReviewPolicy
from app.services.rules import KeywordRuleEngine, RulePrediction
from app.services.safety import SummarySafetyFilter
from app.services.summary import AgentSummaryGenerator

logger = logging.getLogger(__name__)

SEVERITY_RANK = {
    Severity.LOW: 0,
    Severity.MEDIUM: 1,
    Severity.HIGH: 2,
    Severity.CRITICAL: 3,
}


@dataclass(frozen=True)
class FinalDecision:
    case_type: CaseType
    severity: Severity
    department: Department
    confidence: float


class TicketSortingService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.preprocessor = TicketPreprocessor()
        self.keyword_extractor = KeywordExtractor()
        self.rules = KeywordRuleEngine()
        self.ml = TfidfLogisticTicketClassifier(settings.model_path, settings.training_data_path)
        self.summary_generator = AgentSummaryGenerator()
        self.safety_filter = SummarySafetyFilter()
        self.review_policy = HumanReviewPolicy()
        self.audit_log = SQLiteAuditLog(settings.sqlite_path)

    def warmup(self) -> None:
        self.ml.load_or_train()
        if self.settings.enable_audit_log:
            self.audit_log.initialize()

    def sort(self, request: TicketRequest) -> TicketResponse:
        preprocessed = self.preprocessor.preprocess(request.message)
        keywords = self.keyword_extractor.extract(preprocessed)
        rule_prediction = self.rules.predict(preprocessed)

        if not preprocessed.normalized:
            decision = FinalDecision(
                case_type=CaseType.OTHER,
                severity=Severity.LOW,
                department=Department.CUSTOMER_SUPPORT,
                confidence=0.2,
            )
        else:
            ml_prediction = self.ml.predict(preprocessed.normalized)
            decision = self._combine(rule_prediction, ml_prediction)

        summary = self.summary_generator.generate(
            preprocessed,
            decision.case_type,
            decision.severity,
        )
        summary = self.safety_filter.validate(summary)
        human_review = self.review_policy.required(
            decision.case_type,
            decision.severity,
            decision.confidence,
        )

        response = TicketResponse(
            ticket_id=request.ticket_id,
            case_type=decision.case_type,
            severity=decision.severity,
            department=decision.department,
            agent_summary=summary,
            human_review_required=human_review,
            confidence=round(decision.confidence, 4),
        )
        self._audit(request, response)
        logger.info(
            "ticket_sorted",
            extra={
                "ticket_id": request.ticket_id,
                "case_type": response.case_type.value,
                "severity": response.severity.value,
                "confidence": response.confidence,
                "keywords": keywords,
            },
        )
        return response

    def _combine(self, rule: RulePrediction, ml: MLPrediction) -> FinalDecision:
        # Rule wins for high-risk and high-precision fintech mappings.
        if rule.case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING and rule.case_score >= 0.75:
            case_type = rule.case_type
            case_confidence = max(rule.case_score, 0.92)
        elif rule.case_score >= 0.8:
            case_type = rule.case_type
            agreement_bonus = 0.06 if ml.case_type == rule.case_type else 0.0
            case_confidence = min(0.98, max(rule.case_score, ml.case_confidence) + agreement_bonus)
        elif ml.case_confidence >= self.settings.confidence_threshold:
            case_type = ml.case_type
            case_confidence = ml.case_confidence
        else:
            case_type = CaseType.OTHER
            case_confidence = max(0.35, ml.case_confidence * 0.85)

        severity = self._combine_severity(rule, ml, case_type)
        department = (
            rule.department
            if case_type == rule.case_type
            else CASE_TO_DEPARTMENT[case_type]
        )
        if case_type == CaseType.REFUND_REQUEST and department == Department.FRAUD_RISK:
            department = Department.CUSTOMER_SUPPORT

        confidence = self._calibrate_confidence(case_confidence, rule, ml, case_type, severity)
        return FinalDecision(
            case_type=case_type,
            severity=severity,
            department=department,
            confidence=confidence,
        )

    def _combine_severity(
        self,
        rule: RulePrediction,
        ml: MLPrediction,
        case_type: CaseType,
    ) -> Severity:
        if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
            return Severity.CRITICAL if rule.severity == Severity.CRITICAL else Severity.HIGH
        if rule.severity_score >= 0.8:
            return rule.severity
        if ml.severity_confidence >= 0.68:
            return ml.severity
        return max([rule.severity, ml.severity], key=lambda severity: SEVERITY_RANK[severity])

    def _calibrate_confidence(
        self,
        case_confidence: float,
        rule: RulePrediction,
        ml: MLPrediction,
        case_type: CaseType,
        severity: Severity,
    ) -> float:
        confidence = case_confidence
        if ml.case_type == case_type:
            confidence += 0.04
        if rule.case_type == case_type and rule.case_score >= 0.7:
            confidence += 0.05
        if severity == Severity.CRITICAL or case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
            confidence = max(confidence, 0.9)
        return min(max(confidence, 0.05), 0.99)

    def _audit(self, request: TicketRequest, response: TicketResponse) -> None:
        if not self.settings.enable_audit_log:
            return
        try:
            self.audit_log.record(
                request.ticket_id,
                request.model_dump(),
                response.model_dump(mode="json"),
            )
        except Exception:  # noqa: BLE001 - audit failure must not block core response
            logger.exception("audit_log_failed", extra={"ticket_id": request.ticket_id})
