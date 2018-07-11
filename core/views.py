from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.conf import settings
from django.db.models import F
from django.urls import reverse
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from .forms import UploadForm, FILE_TYPE_CHOICES
from .utils import Headline, run_shell_command
from mpages.models import Page


class SearchView(TemplateView):
    template_name = "core/search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_string = self.request.GET.get("search", "")
        if len(search_string) >= 3:
            search_query = SearchQuery(search_string)
            title_vector = SearchVector("title", weight="A")

            content_vector = SearchVector("content", weight="B")
            page_vectors = title_vector + content_vector

            context["text_search_results"] = (
                Page.objects.annotate(search=page_vectors)
                .filter(search=search_query)
                .annotate(rank=SearchRank(page_vectors, search_query))
                .order_by("-rank")
                .annotate(title_highlight=Headline(F("title"), search_query))
                .annotate(content_highlight=Headline(F("content"), search_query))
            )

            context["title_string_search_results"] = Page.objects.filter(
                title__icontains=search_string
            )
            context["content_string_search_results"] = Page.objects.filter(
                content__icontains=search_string
            )
        else:
            context["error"] = "Search term must be at least 3 characters"
        context["search_string"] = search_string
        return context


class UploadView(LoginRequiredMixin, FormView):
    template_name = "core/upload.html"
    form_class = UploadForm

    def form_valid(self, form):
        upload_file = form.cleaned_data["upload_file"]
        upload_file_type = form.cleaned_data["upload_type"]
        with open(
            f"{settings.MEDIA_ROOT}/{upload_file_type}/{upload_file.name}", "wb+"
        ) as destination:
            for chunk in upload_file.chunks():
                destination.write(chunk)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        cwd = settings.BASE_DIR
        uploads = []
        for upload_type in FILE_TYPE_CHOICES:
            for filename in run_shell_command(
                f"ls media/{upload_type.directory}", cwd
            ).split():
                uploads.append(
                    {
                        "type": upload_type.label,
                        "directory": upload_type.directory,
                        "filename": filename,
                    }
                )

        context["uploads"] = uploads

        return context

    def get_success_url(self):
        return reverse("upload")
