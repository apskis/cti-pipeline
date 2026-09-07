"""Vendored stack-neutral report package for the CTI pipeline.

Only the docx report renderers and the config/reporting-period helpers are
vendored here (from the cti-report-generator project). The Azure OpenAI
analysis layer is NOT vendored: in this pipeline Claude Code produces the
analysis_result, and these renderers turn it into the .docx. No azure-*,
semantic-kernel, or openai imports live under this tree.
"""
