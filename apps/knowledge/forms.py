from django import forms
from django.forms import inlineformset_factory

from apps.core.i18n import translate_text

from .models import Category, CodeSnippet, CommonMistake, Concept, ConceptAlias, ConceptRelation, Tag, normalized


FORM_LABELS = {
    "title": "Title", "parent": "Parent", "description": "Description", "category": "Category",
    "difficulty": "Difficulty", "quick_definition": "Quick definition", "simple_explanation": "Simple explanation",
    "deep_dive": "Deep dive", "is_favorite": "Favorite", "tag_names": "Tags", "value": "Value",
    "language": "Language", "code": "Code", "explanation": "Explanation", "sort_order": "Sort order",
    "correction": "Correction", "target": "Related concept", "relation_type": "Relation type", "DELETE": "Delete",
}


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
    tag_names = forms.CharField(required=False, help_text="Separate tags with commas.")

    class Meta:
        model = Concept
        fields = ["title", "category", "difficulty", "quick_definition", "simple_explanation", "deep_dive", "is_favorite"]
        widgets = {
            "quick_definition": forms.Textarea(attrs={"rows": 3}),
            "simple_explanation": forms.Textarea(attrs={"rows": 5}),
            "deep_dive": forms.Textarea(attrs={"rows": 8}),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.instance.owner = user
        self.fields["category"].queryset = Category.objects.filter(owner=user)
        self.fields["tag_names"].help_text = translate_text("Separate tags with commas.")
        if self.instance.pk:
            self.fields["tag_names"].initial = ", ".join(self.instance.tags.values_list("name", flat=True))

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
        for value in self.cleaned_data["tag_names"].split(","):
            name = " ".join(value.split())
            if not name:
                continue
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
        widgets = {"code": forms.Textarea(attrs={"rows": 7, "class": "ltr"})}


class MistakeForm(LocalizedModelForm):
    class Meta:
        model = CommonMistake
        fields = ["title", "description", "correction", "sort_order"]


class RelationForm(LocalizedModelForm):
    class Meta:
        model = ConceptRelation
        fields = ["target", "relation_type"]

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["target"].queryset = Concept.objects.filter(owner=user).exclude(pk=self.instance.source_id)


AliasFormSet = inlineformset_factory(Concept, ConceptAlias, form=AliasForm, extra=2, can_delete=True)
SnippetFormSet = inlineformset_factory(Concept, CodeSnippet, form=SnippetForm, extra=1, can_delete=True)
MistakeFormSet = inlineformset_factory(Concept, CommonMistake, form=MistakeForm, extra=1, can_delete=True)
RelationFormSet = inlineformset_factory(Concept, ConceptRelation, fk_name="source", form=RelationForm, extra=2, can_delete=True)
