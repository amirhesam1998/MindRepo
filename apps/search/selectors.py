"""Owner-scoped concept discovery queries shared by search surfaces."""

from collections.abc import Mapping

from django.db import connection
from django.db.models import Case, Exists, IntegerField, OuterRef, Q, Value, When

from apps.knowledge.models import Concept, ConceptAlias, Tag


MAX_QUERY_LENGTH = 200
PALETTE_RESULT_LIMIT = 8


def normalize_search_query(value: str) -> str:
    """Conservatively normalize whitespace, case, and common Arabic Persian glyphs."""
    value = " ".join(value.replace("\u200c", " ").split())[:MAX_QUERY_LENGTH]
    return value.replace("ي", "ی").replace("ك", "ک").casefold()


def query_variants(query: str) -> list[str]:
    variants = [query]
    arabic = query.replace("ی", "ي").replace("ک", "ك")
    if arabic != query:
        variants.append(arabic)
    return variants


def filter_concepts(queryset, *, user, filters: Mapping | None = None):
    filters = filters or {}
    if category_id := filters.get("category"):
        queryset = queryset.filter(category_id=category_id, category__owner=user)
    if tag_id := filters.get("tag"):
        queryset = queryset.filter(tags__id=tag_id, tags__owner=user)
    if difficulty := filters.get("difficulty"):
        if difficulty in Concept.Difficulty.values:
            queryset = queryset.filter(difficulty=difficulty)
    if filters.get("favorite"):
        queryset = queryset.filter(is_favorite=True)
    return queryset


def _portable_search(user, query: str):
    variants = query_variants(query)
    def matches(field, lookup):
        expression = Q()
        for variant in variants:
            expression |= Q(**{f"{field}__{lookup}": variant})
        return expression

    title_exact = matches("title", "iexact")
    title_prefix = matches("title", "istartswith")
    title_partial = matches("title", "icontains")
    category_exact = matches("category__title", "iexact")
    category_partial = matches("category__title", "icontains")
    alias_exact = Q(aliases__normalized_value__in=variants)
    alias_partial = Q(aliases__normalized_value__icontains=query)
    tag_exact = Q(tags__normalized_name__in=variants)
    tag_partial = Q(tags__normalized_name__icontains=query)
    quick_match = matches("quick_definition", "icontains")
    simple_match = matches("simple_explanation", "icontains")
    deep_match = matches("deep_dive", "icontains")
    section_title = matches("sections__title", "icontains")
    section_content = matches("sections__content", "icontains")
    source_title = matches("sources__title", "icontains")
    source_note = matches("sources__note", "icontains")
    context_technology = matches("contexts__technology", "icontains") | matches("contexts__version", "icontains")
    card_question = matches("review_cards__question", "icontains")
    card_answer = matches("review_cards__answer", "icontains")
    content = quick_match | simple_match | deep_match | section_title | section_content | source_title | source_note | context_technology | card_question | card_answer

    alias_base = ConceptAlias.objects.filter(concept_id=OuterRef("pk"))
    tag_base = Tag.objects.filter(concepts__pk=OuterRef("pk"), owner=user)
    annotations = {
        "alias_exact_match": Exists(alias_base.filter(normalized_value__in=variants)),
        "alias_partial_match": Exists(alias_base.filter(normalized_value__icontains=query)),
        "tag_exact_match": Exists(tag_base.filter(normalized_name__in=variants)),
        "tag_partial_match": Exists(tag_base.filter(normalized_name__icontains=query)),
    }
    relevance = Case(
        When(title_exact, then=Value(1000)),
        When(title_prefix, then=Value(900)),
        When(alias_exact_match=True, then=Value(850)),
        When(alias_partial_match=True, then=Value(800)),
        When(tag_exact_match=True, then=Value(760)),
        When(tag_partial_match=True, then=Value(700)),
        When(category_exact, then=Value(680)),
        When(category_partial, then=Value(640)),
        When(title_partial, then=Value(600)),
        When(quick_match, then=Value(500)),
        When(simple_match, then=Value(400)),
        When(deep_match, then=Value(300)),
        When(card_question, then=Value(280)),
        When(section_title, then=Value(260)),
        When(source_title, then=Value(240)),
        When(context_technology, then=Value(220)),
        When(section_content, then=Value(180)),
        When(card_answer, then=Value(160)),
        When(source_note, then=Value(140)),
        default=Value(0),
        output_field=IntegerField(),
    )
    matches = (
        title_exact
        | title_prefix
        | title_partial
        | category_exact
        | category_partial
        | alias_exact
        | alias_partial
        | tag_exact
        | tag_partial
        | content
    )
    return Concept.objects.filter(owner=user).annotate(**annotations).filter(matches).annotate(search_score=relevance)


def search_concepts(*, user, query: str, filters: Mapping | None = None, limit: int | None = None):
    """Return one owner-scoped ranked queryset for Search, Library, and the palette."""
    normalized = normalize_search_query(query)
    if not normalized:
        return Concept.objects.none()

    queryset = _portable_search(user, normalized)
    if connection.vendor == "postgresql":
        from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

        document = (
            SearchVector("title", weight="A")
            + SearchVector("quick_definition", weight="B")
            + SearchVector("simple_explanation", weight="C")
            + SearchVector("deep_dive", weight="D")
        )
        query_object = SearchQuery(normalized, search_type="websearch")
        queryset = queryset.annotate(fts_rank=SearchRank(document, query_object))
        ordering = ("-search_score", "-fts_rank", "-updated_at", "pk")
    else:
        ordering = ("-search_score", "-updated_at", "pk")

    queryset = filter_concepts(queryset, user=user, filters=filters).select_related("category", "review_state").prefetch_related(
        "tags", "aliases"
    ).distinct().order_by(*ordering)
    return queryset[:limit] if limit else queryset
