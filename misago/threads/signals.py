from django.db import transaction
from django.dispatch import receiver, Signal

from misago.categories.models import Category
from misago.core.pgutils import batch_update, batch_delete

from misago.threads.models import Thread, Post, Event


delete_post = Signal()
delete_thread = Signal()
merge_post = Signal()
merge_thread = Signal(providing_args=["other_thread"])
move_post = Signal()
move_thread = Signal()
remove_thread_participant = Signal(providing_args=["user"])


"""
Signal handlers
"""
@receiver(merge_thread)
def merge_threads_posts(sender, **kwargs):
    other_thread = kwargs['other_thread']
    other_thread.post_set.update(category=sender.category, thread=sender)


@receiver(move_thread)
def move_thread_content(sender, **kwargs):
    sender.post_set.update(category=sender.category)
    sender.event_set.update(category=sender.category)


from misago.categories.signals import (delete_category_content,
                                       move_category_content)
@receiver(delete_category_content)
def delete_category_threads(sender, **kwargs):
    sender.event_set.all().delete()
    sender.thread_set.all().delete()
    sender.post_set.all().delete()


@receiver(move_category_content)
def move_category_threads(sender, **kwargs):
    new_category = kwargs['new_category']

    Thread.objects.filter(category=sender).update(category=new_category)
    Post.objects.filter(category=sender).update(category=new_category)
    Event.objects.filter(category=sender).update(category=new_category)


from misago.users.signals import delete_user_content, username_changed
@receiver(delete_user_content)
def delete_user_threads(sender, **kwargs):
    recount_categories = set()
    recount_threads = set()

    for thread in batch_delete(sender.thread_set.all(), 50):
        recount_categories.add(thread.category_id)
        with transaction.atomic():
            thread.delete()

    for post in batch_delete(sender.post_set.all(), 50):
        recount_categories.add(post.category_id)
        recount_threads.add(post.thread_id)
        with transaction.atomic():
            post.delete()

    if recount_threads:
        changed_threads_qs = Thread.objects.filter(id__in=recount_threads)
        for thread in batch_update(changed_threads_qs, 50):
            thread.synchronize()
            thread.save()

    if recount_categories:
        for category in Category.objects.filter(id__in=recount_categories):
            category.synchronize()
            category.save()


@receiver(username_changed)
def update_usernames(sender, **kwargs):
    Thread.objects.filter(starter=sender).update(
        starter_name=sender.username,
        starter_slug=sender.slug
    )

    Thread.objects.filter(last_poster=sender).update(
        last_poster_name=sender.username,
        last_poster_slug=sender.slug
    )

    Post.objects.filter(poster=sender).update(poster_name=sender.username)

    Post.objects.filter(last_editor=sender).update(
        last_editor_name=sender.username,
        last_editor_slug=sender.slug
    )

    Event.objects.filter(author=sender).update(
        author_name=sender.username,
        author_slug=sender.slug
    )


from django.contrib.auth import get_user_model
from django.db.models.signals import pre_delete
@receiver(pre_delete, sender=get_user_model())
def remove_unparticipated_private_threads(sender, **kwargs):
    threads_qs = kwargs['instance'].private_thread_set.all()
    for thread in batch_update(threads_qs, 50):
        if thread.participants.count() == 1:
            with transaction.atomic():
                thread.delete()
