from django import forms

from .models import Memo, MemoGroup


class StyledModelForm(forms.ModelForm):
    """为表单字段统一附加样式类。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css_class = "form-check-input" if isinstance(field.widget, forms.CheckboxInput) else "form-input"
            field.widget.attrs["class"] = css_class
            if name == "title":
                field.widget.attrs["placeholder"] = "例如：周三 19:30 参加产品评审"
            if name == "content":
                field.widget.attrs["placeholder"] = "补充细节、上下文、下一步行动..."


class MemoForm(StyledModelForm):
    class Meta:
        model = Memo
        fields = ["title", "content", "group", "priority", "due_date", "is_pinned", "is_completed"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 5}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }


class MemoGroupForm(StyledModelForm):
    class Meta:
        model = MemoGroup
        fields = ["name", "description", "color"]
        widgets = {
            "color": forms.TextInput(attrs={"type": "color"}),
        }
