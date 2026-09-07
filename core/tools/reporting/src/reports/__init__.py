"""Report renderers. Import the concrete modules to register generators:

    from src.reports import weekly_report, quarterly_report  # noqa: F401
    from src.reports.registry import get_report_generator

Blob storage and history-store (Azure) are intentionally not vendored.
"""
