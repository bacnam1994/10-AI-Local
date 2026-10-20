"""Research Module: Gathers and tracks regulatory standards and official references."""

import logging
from typing import Optional
from datetime import datetime, timezone

from app.core.models import SourceReference, utc_now
from app.core.state_store import StateStore

logger = logging.getLogger(__name__)

# Verification status constants
STATUS_CATALOG_SUGGESTION = "Đối chiếu danh mục chuẩn (Cần kiểm tra hiệu lực thực tế)"
STATUS_UNVERIFIED = "Chưa xác minh — cần tra cứu thủ công"
STATUS_VERIFIED_ONLINE = "Đã xác minh trực tuyến"
STATUS_NEEDS_REVIEW = "Cần kiểm tra lại hiệu lực văn bản"

# Curated Vietnamese Pharmaceutical Regulatory References (Suggested Catalog)
KNOWN_GMP_REFERENCES = [
    {
        "doc_number": "35/2018/TT-BYT",
        "title": "Thông tư 35/2018/TT-BYT quy định về Thực hành tốt sản xuất thuốc, nguyên liệu làm thuốc (GMP)",
        "issuing_body": "Bộ Y Tế",
        "doc_type": "Thông tư Quy chuẩn",
        "issue_date": "2018-11-22",
        "url": "https://moh.gov.vn/van-ban-chi-dao-dieu-hanh/-/asset_publisher/vTXGwh6tqybb/content/thong-tu-so-35-2018-tt-byt",
        "is_mandatory": True,
        "status": STATUS_CATALOG_SUGGESTION
    },
    {
        "doc_number": "29/2020/TT-BYT",
        "title": "Thông tư 29/2020/TT-BYT sửa đổi, bổ sung một số điều của Thông tư 35/2018/TT-BYT",
        "issuing_body": "Bộ Y Tế",
        "doc_type": "Thông tư Sửa đổi bổ sung",
        "issue_date": "2020-12-31",
        "url": "https://dav.gov.vn/van-ban-phap-quy",
        "is_mandatory": True,
        "status": STATUS_CATALOG_SUGGESTION
    },
    {
        "doc_number": "DĐVN V",
        "title": "Dược điển Việt Nam V - Phụ lục kiểm nghiệm vi sinh và môi trường vô trùng",
        "issuing_body": "Hội đồng Dược điển Việt Nam",
        "doc_type": "Dược điển Quốc gia",
        "issue_date": "2018-01-01",
        "url": None,
        "is_mandatory": True,
        "status": STATUS_CATALOG_SUGGESTION
    },
    {
        "doc_number": "WHO TRS 986 Annex 2",
        "title": "WHO Good Manufacturing Practices for pharmaceutical products: main principles",
        "issuing_body": "World Health Organization (WHO)",
        "doc_type": "Technical Report Series",
        "issue_date": "2014-01-01",
        "url": "https://www.who.int/publications/m/item/trs986-annex2",
        "is_mandatory": False,
        "status": "Khuyến nghị kỹ thuật quốc tế (Cần kiểm tra phạm vi áp dụng)"
    }
]


class ResearchEngine:
    """Handles reference gathering, legal verification, and source record tracking."""

    def __init__(self, state_store: StateStore):
        self.state_store = state_store

    async def research_for_job(self, job_id: str, query_terms: list[str]) -> list[SourceReference]:
        """Lookup and store source references for a job.
        
        Important: Curated references are suggestions from internal catalog and are
        NOT marked as verified_at unless an actual verification has occurred.
        """
        recorded_refs: list[SourceReference] = []

        for idx, term in enumerate(query_terms):
            matched = False
            # Check against curated reference suggestions
            for known in KNOWN_GMP_REFERENCES:
                if (known["doc_number"] and known["doc_number"].lower() in term.lower()) or \
                   any(w in term.lower() for w in ["35/2018", "gmp", "dược điển", "who trs"]):
                    ref = SourceReference(
                        reference_id=f"ref_{job_id}_{idx + 1}",
                        job_id=job_id,
                        title=known["title"],
                        issuing_body=known["issuing_body"],
                        doc_number=known["doc_number"],
                        doc_type=known["doc_type"],
                        issue_date=known["issue_date"],
                        url=known["url"],
                        status=known["status"],
                        clause_used=None,  # Do not speculate on specific clauses without concrete basis
                        is_mandatory=known["is_mandatory"],
                        verified_at=None   # Online verification not performed; do not auto-stamp timestamp
                    )
                    self.state_store.save_source_reference(ref)
                    recorded_refs.append(ref)
                    matched = True
                    break

            # If not in curated catalog, flag explicitly as UNVERIFIED
            if not matched:
                ref = SourceReference(
                    reference_id=f"ref_{job_id}_{idx + 1}",
                    job_id=job_id,
                    title=term,
                    issuing_body="Chưa xác minh",
                    doc_number=None,
                    doc_type="Tài liệu tham khảo",
                    issue_date=None,
                    url=None,
                    status=STATUS_UNVERIFIED,
                    clause_used=None,
                    is_mandatory=False,
                    verified_at=None
                )
                self.state_store.save_source_reference(ref)
                recorded_refs.append(ref)

        catalog_count = sum(1 for r in recorded_refs if r.status != STATUS_UNVERIFIED)
        unverified_count = len(recorded_refs) - catalog_count

        self.state_store.append_log(
            job_id, "INFO",
            f"Đã lập hồ sơ {len(recorded_refs)} nguồn tham chiếu: {catalog_count} từ danh mục gợi ý (chờ kiểm tra thực tế), {unverified_count} chưa xác minh."
        )
        return recorded_refs

    def mark_reference_verified(
        self,
        reference: SourceReference,
        verified_status: str = STATUS_VERIFIED_ONLINE,
        clause_used: Optional[str] = None
    ) -> SourceReference:
        """Mark a reference as verified after actual manual or online check."""
        reference.status = verified_status
        reference.verified_at = utc_now()
        if clause_used:
            reference.clause_used = clause_used
        self.state_store.save_source_reference(reference)
        return reference

