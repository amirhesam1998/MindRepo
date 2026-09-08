import hashlib

from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.core.cache import cache

from apps.core.i18n import translate_text


class MindRepoLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True
    max_attempts = 5
    lock_seconds = 15 * 60

    def throttle_key(self):
        raw = f"{self.request.META.get('REMOTE_ADDR', '')}\0{self.request.POST.get('username', '').casefold()}"
        return f"login-throttle:{hashlib.sha256(raw.encode()).hexdigest()}"

    def post(self, request, *args, **kwargs):
        if cache.get(self.throttle_key(), 0) >= self.max_attempts:
            form = self.get_form()
            form.add_error(None, "Please wait a few minutes before trying again.")
            return self.form_invalid(form)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        key = self.throttle_key()
        cache.set(key, cache.get(key, 0) + 1, self.lock_seconds)
        return super().form_invalid(form)

    def form_valid(self, form):
        cache.delete(self.throttle_key())
        messages.success(self.request, translate_text("Welcome back to MindRepo."))
        return super().form_valid(form)


class MindRepoLogoutView(LogoutView):
    def dispatch(self, request, *args, **kwargs):
        messages.info(request, translate_text("You have been logged out."))
        return super().dispatch(request, *args, **kwargs)
