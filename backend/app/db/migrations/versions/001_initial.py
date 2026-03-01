"""Initial schema: journals, papers, orgs, categories.

Revision ID: 001
Revises:
Create Date: 2025-01-27

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "journals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("issn_online", sa.String(32), nullable=True),
        sa.Column("openalex_source_id", sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_journals_code"),
    )
    op.create_index("ix_journals_code", "journals", ["code"], unique=True)
    op.create_index("ix_journals_openalex_source_id", "journals", ["openalex_source_id"], unique=False)

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_categories_name"),
    )

    op.create_table(
        "papers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("openalex_work_id", sa.String(128), nullable=False),
        sa.Column("title", sa.String(1024), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("doi", sa.String(256), nullable=True),
        sa.Column("published_date", sa.String(32), nullable=True),
        sa.Column("primary_url", sa.String(512), nullable=True),
        sa.Column("journal_id", sa.Integer(), nullable=False),
        sa.Column("abstract_text", sa.Text(), nullable=True),
        sa.Column("concepts_hint", sa.Text(), nullable=True),
        sa.Column("raw_json", sa.JSON(), nullable=True),
        sa.Column("best_category_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["journal_id"], ["journals.id"]),
        sa.ForeignKeyConstraint(["best_category_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("openalex_work_id", name="uq_papers_openalex_work_id"),
    )
    op.create_index("ix_papers_openalex_work_id", "papers", ["openalex_work_id"], unique=True)
    op.create_index("ix_papers_journal_id", "papers", ["journal_id"], unique=False)

    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("openalex_org_id", sa.String(128), nullable=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("country_code", sa.String(8), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("openalex_org_id", name="uq_organizations_openalex_org_id"),
    )
    op.create_index("ix_organizations_openalex_org_id", "organizations", ["openalex_org_id"], unique=True)

    op.create_table(
        "paper_org",
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("paper_id", "org_id"),
        sa.UniqueConstraint("paper_id", "org_id", name="uq_paper_org"),
    )

    op.create_table(
        "paper_categories",
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("why", sa.Text(), nullable=True),
        sa.Column("model", sa.String(64), nullable=True),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("paper_id", "category_id"),
        sa.UniqueConstraint("paper_id", "category_id", name="uq_paper_category"),
    )


def downgrade() -> None:
    op.drop_table("paper_categories")
    op.drop_table("paper_org")
    op.drop_table("organizations")
    op.drop_table("papers")
    op.drop_table("categories")
    op.drop_table("journals")
