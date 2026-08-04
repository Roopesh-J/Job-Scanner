from job_scanner.models import Category, Posting, Requirement, Responsibility


def test_posting_all_ids_combines_requirements_and_responsibilities():
    posting = Posting(
        title="Backend Engineer",
        company="Acme",
        location="Remote",
        seniority="Senior",
        responsibilities=[Responsibility(id="resp-1", text="Own the API", source_quote="own our public API")],
        requirements=[Requirement(id="req-1", text="Python", category=Category.REQUIRED, source_quote="Python")],
    )
    assert posting.all_ids() == {"resp-1", "req-1"}
