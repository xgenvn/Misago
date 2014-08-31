"""
Module with basic views for use by inheriting actions
"""
from django.contrib import messages
from django.db.models import Q
from django.db.transaction import atomic
from django.shortcuts import redirect, render
from django.utils.translation import ugettext_lazy, ugettext as _
from django.views.generic import View

from misago.acl import add_acl
from misago.core.shortcuts import get_object_or_404, paginate, validate_slug
from misago.forums.lists import get_forums_list, get_forum_path
from misago.forums.models import Forum
from misago.forums.permissions import allow_see_forum, allow_browse_forum

from misago.threads.posting import (PostingInterrupt, EditorFormset,
                                    START, REPLY, EDIT)
from misago.threads.models import ANNOUNCEMENT, Thread, Post
from misago.threads.permissions import allow_see_thread, allow_start_thread


class ForumMixin(object):
    """
    Mixin for getting forums
    """
    def get_forum(self, request, lock=False, **kwargs):
        forum = self.fetch_forum(request, lock, **kwargs)
        self.check_forum_permissions(request, forum)

        if kwargs.get('forum_slug'):
            validate_slug(forum, kwargs.get('forum_slug'))

        return forum

    def fetch_forum(self, request, lock=False, **kwargs):
        queryset = Forum.objects
        if lock:
            queryset = queryset.select_for_update()

        return get_object_or_404(
            queryset, id=kwargs.get('forum_id'), role='forum')

    def check_forum_permissions(self, request, forum):
        add_acl(request.user, forum)
        allow_see_forum(request.user, forum)
        allow_browse_forum(request.user, forum)


class ThreadMixin(object):
    """
    Mixin for getting thread
    """
    def get_thread(self, request, lock=False, **kwargs):
        thread = self.fetch_thread(request, lock, **kwargs)
        self.check_thread_permissions(request, thread)

        if kwargs.get('thread_slug'):
            validate_slug(thread, kwargs.get('thread_slug'))

        return thread

    def fetch_thread(self, request, lock=False, select_related=None, **kwargs):
        queryset = Thread.objects
        if lock:
            queryset = queryset.select_for_update()
        if select_related:
            queryset = queryset.select_related(*select_related)

        return get_object_or_404(queryset, id=kwargs.get('thread_id'))

    def check_thread_permissions(self, request, thread):
        add_acl(request.user, thread)
        allow_see_thread(request.user, thread)


class PostMixin(object):
    pass


class ViewBase(ForumMixin, ThreadMixin, PostMixin, View):
    templates_dir = ''
    template = ''

    def final_template(self):
        return '%s/%s' % (self.templates_dir, self.template)

    def process_context(self, request, context):
        """
        Simple hook for extending and manipulating template context.
        """
        return context

    def render(self, request, context=None, template=None):
        context = self.process_context(request, context or {})
        template = template or self.final_template()
        return render(request, template, context)


class OrderThreadsMixin(object):
    order_by = (
        ('recently-replied', ugettext_lazy("Recently replied")),
        ('last-replied', ugettext_lazy("Last replied")),
        ('most-replied', ugettext_lazy("Most replied")),
        ('least-replied', ugettext_lazy("Least replied")),
        ('newest', ugettext_lazy("Newest")),
        ('oldest', ugettext_lazy("Oldest")),
    )

    def get_ordering(self, kwargs):
        if kwargs.get('sort') in [o[0] for o in self.order_by]:
            return kwargs.get('sort')
        else:
            return self.order_by[0][0]

    def is_ordering_default(self, order_by):
        return self.order_by[0][0] == order_by

    def get_ordering_name(self, order_by):
        for ordering in self.order_by:
            if ordering[0] == order_by:
                return ordering[1]

    def get_orderings_dicts(self):
        dicts = []
        for ordering in self.order_by:
            dicts.append({
                'url': ordering[0],
                'name': ordering[1],
            })
        return dicts


class ThreadsView(ViewBase):
    def get_threads(self, request, kwargs):
        queryset = self.get_threads_queryset(request, forum)

        threads_qs = queryset.filter(weight__lt=ANNOUNCEMENT)
        threads_qs = threads_qs.order_by('-weight', '-last_post_id')

        page = paginate(threads_qs, kwargs.get('page', 0), 30, 10)
        threads = []

        for announcement in queryset.filter(weight=ANNOUNCEMENT):
            threads.append(announcement)
        for thread in page.object_list:
            threads.append(thread)

        for thread in threads:
            thread.forum = forum

        return page, threads

    def get_threads_queryset(self, request):
        return forum.thread_set.all().order_by('-last_post_id')

    def add_threads_reads(self, request, threads):
        for thread in threads:
            thread.is_new = False

        import random
        for thread in threads:
            thread.is_new = random.choice((True, False))


class ForumView(OrderThreadsMixin, ThreadsView):
    """
    Basic view for threads lists
    """
    template = 'list.html'

    def get_threads(self, request, forum, kwargs, order_by=None, limit=None):
        queryset = self.get_threads_queryset(request, forum)
        queryset = self.filter_all_querysets(request, forum, queryset)

        announcements_qs = queryset.filter(weight=ANNOUNCEMENT)
        threads_qs = queryset.filter(weight__lt=ANNOUNCEMENT)

        announcements_qs = self.filter_announcements_queryset(
            request, forum, announcements_qs)
        threads_qs = self.filter_threads_queryset(request, forum, threads_qs)

        threads_qs, announcements_qs = self.order_querysets(
            order_by, threads_qs, announcements_qs)

        page = paginate(threads_qs, kwargs.get('page', 0), 20, 10)
        threads = []

        for announcement in announcements_qs:
            threads.append(announcement)
        for thread in page.object_list:
            threads.append(thread)

        for thread in threads:
            thread.forum = forum

        return page, threads

    def order_querysets(self, order_by, threads, announcements):
        if order_by == 'recently-replied':
            threads = threads.order_by('-weight', '-last_post')
            announcements = announcements.order_by('-last_post')
        if order_by == 'last-replied':
            threads = threads.order_by('weight', 'last_post')
            announcements = announcements.order_by('last_post')
        if order_by == 'most-replied':
            threads = threads.order_by('-weight', '-replies')
            announcements = announcements.order_by('-replies')
        if order_by == 'least-replied':
            threads = threads.order_by('weight', 'replies')
            announcements = announcements.order_by('replies')
        if order_by == 'newest':
            threads = threads.order_by('-weight', '-id')
            announcements = announcements.order_by('-id')
        if order_by == 'oldest':
            threads = threads.order_by('weight', 'id')
            announcements = announcements.order_by('id')

        return threads, announcements

    def filter_all_querysets(self, request, forum, queryset):
        if request.user.is_authenticated():
            condition_author = Q(starter_id=request.user.id)

            can_mod = forum.acl['can_review_moderated_content']
            can_hide = forum.acl['can_hide_threads']

            if not can_mod and not can_hide:
                condition = Q(is_moderated=False) & Q(is_hidden=False)
                queryset = queryset.filter(condition_author | condition)
            elif not can_mod:
                condition = Q(is_moderated=False)
                queryset = queryset.filter(condition_author | condition)
            elif not can_hide:
                condition = Q(is_hidden=False)
                queryset = queryset.filter(condition_author | condition)
        else:
            if not forum.acl['can_review_moderated_content']:
                queryset = queryset.filter(is_moderated=False)
            if not forum.acl['can_hide_threads']:
                queryset = queryset.filter(is_hidden=False)

        return queryset

    def filter_threads_queryset(self, request, forum, queryset):
        if forum.acl['can_see_own_threads']:
            if request.user.is_authenticated():
                queryset = queryset.filter(starter_id=request.user.id)
            else:
                queryset = queryset.filter(starter_id=0)

        return queryset

    def filter_announcements_queryset(self, request, forum, queryset):
        return queryset

    def get_threads_queryset(self, request, forum):
        return forum.thread_set.all().order_by('-last_post_id')

    def dispatch(self, request, *args, **kwargs):
        forum = self.get_forum(request, **kwargs)
        links_params = {'forum_slug': forum.slug, 'forum_id': forum.id}

        forum.subforums = get_forums_list(request.user, forum)

        order_by = self.get_ordering(kwargs)
        if self.is_ordering_default(kwargs.get('sort')):
            kwargs.pop('sort')
            return redirect('misago:forum', **kwargs)
        else:
            links_params['sort'] = order_by

        page, threads = self.get_threads(request, forum, kwargs, order_by)
        self.add_threads_reads(request, threads)

        return self.render(request, {
            'forum': forum,
            'path': get_forum_path(forum),
            'page': page,
            'paginator': page.paginator,
            'threads': threads,
            'links_params': links_params,
            'order_name': self.get_ordering_name(order_by),
            'order_by': self.get_orderings_dicts(),
        })


class ThreadView(ViewBase):
    """
    Basic view for threads
    """
    template = 'thread.html'

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST':
            with atomic():
                return self.real_dispatch(request, *args, **kwargs)
        else:
            return self.real_dispatch(request, *args, **kwargs)

    def real_dispatch(self, request, *args, **kwargs):
        relations = ['forum', 'starter', 'last_poster', 'first_post']
        thread = self.fetch_thread(request, select_related=relations, **kwargs)
        forum = thread.forum

        self.check_forum_permissions(request, forum)
        self.check_thread_permissions(request, thread)

        return self.render(request, {
            'forum': forum,
            'path': get_forum_path(forum),
            'thread': thread
        })

class PostView(ViewBase):
    """
    Basic view for posts
    """
    def fetch_post(self, request, **kwargs):
        pass

    def dispatch(self, request, *args, **kwargs):
        post = self.fetch_post(request, **kwargs)


class EditorView(ViewBase):
    """
    Basic view for starting/replying/editing
    """
    template = 'editor.html'

    def find_mode(self, request, *args, **kwargs):
        """
        First step: guess from request what kind of view we are
        """
        is_post = request.method == 'POST'

        if 'forum_id' in kwargs:
            mode = START
            user = request.user

            forum = self.get_forum(request, lock=is_post, **kwargs)
            thread = Thread(forum=forum)
            post = Post(forum=forum, thread=thread)
            quote = Post(0)
        elif 'thread_id' in kwargs:
            thread = self.get_thread(request, lock=is_post, **kwargs)
            forum = thread.forum

        return mode, forum, thread, post, quote

    def allow_mode(self, user, mode, forum, thread, post, quote):
        """
        Second step: check start/reply/edit permissions
        """
        if mode == START:
            self.allow_start(user, forum)
        if mode == REPLY:
            self.allow_reply(user, forum, thread, quote)
        if mode == EDIT:
            self.allow_edit(user, forum, thread, post)

    def allow_start(self, user, forum):
        allow_start_thread(user, forum)

    def allow_reply(self, user, forum, thread, quote):
        raise NotImplementedError()

    def allow_edit(self, user, forum, thread, post):
        raise NotImplementedError()

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST':
            with atomic():
                return self.real_dispatch(request, *args, **kwargs)
        else:
            return self.real_dispatch(request, *args, **kwargs)

    def real_dispatch(self, request, *args, **kwargs):
        mode_context = self.find_mode(request, *args, **kwargs)
        self.allow_mode(request.user, *mode_context)

        mode, forum, thread, post, quote = mode_context
        formset = EditorFormset(request=request,
                                mode=mode,
                                user=request.user,
                                forum=forum,
                                thread=thread,
                                post=post,
                                quote=quote)

        if request.method == 'POST':
            if 'submit' in request.POST and formset.is_valid():
                try:
                    formset.save()
                    return redirect(thread.get_absolute_url())
                except PostingInterrupt as e:
                    messages.error(request, e.message)
            else:
                formset.update()

        return self.render(request, {
            'mode': mode,
            'formset': formset,
            'forms': formset.get_forms_list(),
            'main_forms': formset.get_main_forms(),
            'supporting_forms': formset.get_supporting_forms(),
            'forum': forum,
            'path': get_forum_path(forum),
            'thread': thread,
            'post': post,
            'quote': quote,
        })