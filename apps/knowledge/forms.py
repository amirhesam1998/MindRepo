import json

from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from apps.core.i18n import translate_text

from .models import Category, CodeSnippet, CommonMistake, Concept, ConceptAlias, ConceptContext, ConceptRelation, ConceptSection, ConceptSource, Tag, normalized
from apps.reviews.models import ReviewCard


FORM_LABELS = {
    "title": "Title", "parent": "Parent", "description": "Description", "category": "Category",
    "difficulty": "Difficulty", "quick_definition": "Quick definition", "simple_explanation": "Simple explanation",
    "deep_dive": "Deep dive", "is_favorite": "Favorite", "tag_names": "Tags", "value": "Value",
    "language": "Language", "code": "Code", "explanation": "Explanation", "sort_order": "Sort order",
    "correction": "Correction", "target": "Related concept", "relation_type": "Relation type", "DELETE": "Delete",
}

CODE_LANGUAGE_CHOICES = [
    ("plaintext", "Plain text"), ("python", "Python"), ("php", "PHP"),
    ("javascript", "JavaScript"), ("typescript", "TypeScript"), ("html", "HTML"),
    ("css", "CSS"), ("scss", "SCSS"), ("sql", "SQL"), ("bash", "Bash"),
    ("shell", "Shell"), ("json", "JSON"), ("yaml", "YAML"), ("xml", "XML"),
    ("java", "Java"), ("c", "C"), ("cpp", "C++"), ("csharp", "C#"),
    ("go", "Go"), ("rust", "Rust"), ("ruby", "Ruby"), ("swift", "Swift"),
    ("kotlin", "Kotlin"), ("dart", "Dart"), ("dockerfile", "Dockerfile"),
    ("markdown", "Markdown"),
]


class LocalizedModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.label = translate_text(FORM_LABELS.get(name, field.label))
            if getattr(field, "choices", None):
                field.choices = [(value, translate_text(label)) for value, label in field.choices]


class CategoryForm(LocalizedModelForm):
    class Meta:
        model = Category
        fields = ["title", "parent", "description"]

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.instance.owner = user
        self.fields["parent"].queryset = Category.objects.filter(owner=user).exclude(pk=self.instance.pk)

    def save(self, commit=True):
        category = super().save(commit=False)
        category.owner = self.user
        if not category.slug or category.title != self.initial.get("title"):
            category.set_slug(category.title)
        if commit:
            category.full_clean()
            category.save()
        return category


class ConceptForm(LocalizedModelForm):
    tag_names = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Concept
        fields = ["title", "category", "difficulty", "quick_definition", "simple_explanation", "deep_dive", "freshness_status", "last_verified_at", "verification_note", "is_favorite"]
        widgets = {
            "quick_definition": forms.Textarea(attrs={"rows": 3}),
            "simple_explanation": forms.Textarea(attrs={"rows": 5, "class": "markdown-source"}),
            "deep_dive": forms.Textarea(attrs={"rows": 8, "class": "markdown-source"}),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.instance.owner = user
        categories = list(Category.objects.filter(owner=user).order_by("title"))
        self.fields["category"].queryset = Category.objects.filter(owner=user)
        by_parent = {}
        for category in categories:
            by_parent.setdefault(category.parent_id, []).append(category)
        choices = [("", translate_text("Uncategorized"))]

        def add_children(parent_id, depth=0):
            for category in by_parent.get(parent_id, []):
                choices.append((category.pk, f"{'— ' * depth}{category.title}"))
                add_children(category.pk, depth + 1)

        add_children(None)
        self.fields["category"].choices = choices
        self.fields["is_favorite"].widget.attrs["class"] = "favorite-input"
        self.fields["freshness_status"].required = False
        self.fields["last_verified_at"].required = False
        self.fields["verification_note"].required = False
        if self.instance.pk:
            self.fields["tag_names"].initial = json.dumps(list(self.instance.tags.values_list("name", flat=True)))

    def clean_tag_names(self):
        raw = self.cleaned_data["tag_names"].strip()
        if not raw:
            return []
        try:
            values = json.loads(raw) if raw.startswith("[") else raw.split(",")
        except json.JSONDecodeError:
            raise forms.ValidationError("Tags could not be read.")
        if not isinstance(values, list):
            raise forms.ValidationError("Tags could not be read.")
        unique = {}
        for value in values:
            name = " ".join(str(value).split())
            if name:
                unique.setdefault(normalized(name), name)
        return list(unique.values())

    def save(self, commit=True):
        concept = super().save(commit=False)
        concept.owner = self.user
        if not concept.slug or concept.title != self.initial.get("title"):
            concept.set_slug(concept.title)
        if commit:
            concept.full_clean()
            concept.save()
            self.save_tags(concept)
        return concept

    def save_tags(self, concept):
        tags = []
        for name in self.cleaned_data["tag_names"]:
            tag, _ = Tag.objects.get_or_create(
                owner=self.user, normalized_name=normalized(name), defaults={"name": name}
            )
            tags.append(tag)
        concept.tags.set(tags)


class AliasForm(LocalizedModelForm):
    class Meta:
        model = ConceptAlias
        fields = ["value"]


class SnippetForm(LocalizedModelForm):
    class Meta:
        model = CodeSnippet
        fields = ["title", "language", "code", "explanation", "sort_order"]
        widgets = {
            "code": forms.Textarea(attrs={"rows": 7, "class": "ltr code-source"}),
            "sort_order": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current = self.instance.language or "plaintext"
        choices = CODE_LANGUAGE_CHOICES[:]
        if current not in {value for value, _ in choices}:
            choices.append((current, f"Legacy: {current}"))
        self.fields["language"] = forms.ChoiceField(
            choices=choices,
            label=translate_text("Language"),
            widget=forms.Select(attrs={"class": "form-select"}),
        )


class MistakeForm(LocalizedModelForm):
    class Meta:
        model = CommonMistake
        fields = ["title", "description", "correction", "sort_order"]
        widgets = {"sort_order": forms.HiddenInput()}


class RelationForm(LocalizedModelForm):
    class Meta:
        model = ConceptRelation
        fields = ["target", "relation_type"]

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["target"].queryset = Concept.objects.filter(owner=user).exclude(pk=self.instance.source_id)


class SectionForm(LocalizedModelForm):
    class Meta:
        model = ConceptSection
        fields = ["section_type", "title", "content", "sort_order"]
        widgets = {"content": forms.Textarea(attrs={"rows": 8, "class": "markdown-source"}), "sort_order": forms.HiddenInput()}


class SourceForm(LocalizedModelForm):
    class Meta:
        model = ConceptSource
        fields = ["source_type", "title", "url", "author", "publisher", "version", "note", "accessed_at", "sort_order"]
        widgets = {"sort_order": forms.HiddenInput(), "accessed_at": forms.DateInput(attrs={"type": "date"})}

    def clean_url(self):
        url = self.cleaned_data["url"]
        if url and not url.startswith(("https://", "http://")):
            raise forms.ValidationError("Use an http or https URL.")
        return url


class ContextForm(LocalizedModelForm):
    class Meta:
        model = ConceptContext
        fields = ["technology", "version", "note", "sort_order"]
        widgets = {"sort_order": forms.HiddenInput()}


class ReviewCardForm(LocalizedModelForm):
    class Meta:
        model = ReviewCard
        fields = ["question", "answer", "hint", "sort_order", "is_active"]
        widgets = {"answer": forms.Textarea(attrs={"rows": 6, "class": "markdown-source"}), "sort_order": forms.HiddenInput()}


class EditorInlineFormSet(BaseInlineFormSet):
    def add_fields(self, form, index):
        super().add_fields(form, index)
        if "DELETE" in form.fields:
            form.fields["DELETE"].widget = forms.HiddenInput()


AliasFormSet = inlineformset_factory(Concept, ConceptAlias, form=AliasForm, formset=EditorInlineFormSet, extra=0, can_delete=True)
SnippetFormSet = inlineformset_factory(Concept, CodeSnippet, form=SnippetForm, formset=EditorInlineFormSet, extra=0, can_delete=True)
MistakeFormSet = inlineformset_factory(Concept, CommonMistake, form=MistakeForm, formset=EditorInlineFormSet, extra=0, can_delete=True)
RelationFormSet = inlineformset_factory(Concept, ConceptRelation, fk_name="source", form=RelationForm, formset=EditorInlineFormSet, extra=0, can_delete=True)
SectionFormSet = inlineformset_factory(Concept, ConceptSection, form=SectionForm, formset=EditorInlineFormSet, extra=0, can_delete=True)
SourceFormSet = inlineformset_factory(Concept, ConceptSource, form=SourceForm, formset=EditorInlineFormSet, extra=0, can_delete=True)
ContextFormSet = inlineformset_factory(Concept, ConceptContext, form=ContextForm, formset=EditorInlineFormSet, extra=0, can_delete=True)
ReviewCardFormSet = inlineformset_factory(Concept, ReviewCard, form=ReviewCardForm, formset=EditorInlineFormSet, extra=0, can_delete=False)
