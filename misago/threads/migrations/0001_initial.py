# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations
import django.db.models.deletion
import django.utils.timezone

from misago.core.pgutils import CreatePartialIndex, CreatePartialCompositeIndex


class Migration(migrations.Migration):

    dependencies = [
        ('misago_categories', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('poster_name', models.CharField(max_length=255)),
                ('poster_ip', models.GenericIPAddressField()),
                ('original', models.TextField()),
                ('parsed', models.TextField()),
                ('checksum', models.CharField(max_length=64, default='-')),
                ('has_attachments', models.BooleanField(default=False)),
                ('pickled_attachments', models.TextField(null=True, blank=True)),
                ('posted_on', models.DateTimeField()),
                ('updated_on', models.DateTimeField()),
                ('edits', models.PositiveIntegerField(default=0)),
                ('last_editor_name', models.CharField(max_length=255, null=True, blank=True)),
                ('last_editor_slug', models.SlugField(max_length=255, null=True, blank=True)),
                ('hidden_by', models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('hidden_by_name', models.CharField(max_length=255, null=True, blank=True)),
                ('hidden_by_slug', models.SlugField(max_length=255, null=True, blank=True)),
                ('hidden_on', models.DateTimeField(default=django.utils.timezone.now)),
                ('has_reports', models.BooleanField(default=False)),
                ('has_open_reports', models.BooleanField(default=False)),
                ('is_unapproved', models.BooleanField(default=False, db_index=True)),
                ('is_hidden', models.BooleanField(default=False)),
                ('is_protected', models.BooleanField(default=False)),
                ('category', models.ForeignKey(to='misago_categories.Category')),
                ('last_editor', models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('mentions', models.ManyToManyField(related_name='mention_set', to=settings.AUTH_USER_MODEL)),
                ('poster', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        CreatePartialIndex(
            field='Post.has_open_reports',
            index_name='misago_post_has_open_reports_partial',
            condition='has_open_reports = TRUE',
        ),
        CreatePartialIndex(
            field='Post.is_hidden',
            index_name='misago_post_is_hidden_partial',
            condition='is_hidden = FALSE',
        ),
        migrations.CreateModel(
            name='Thread',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=255)),
                ('slug', models.CharField(max_length=255)),
                ('replies', models.PositiveIntegerField(default=0, db_index=True)),
                ('has_reported_posts', models.BooleanField(default=False)),
                ('has_open_reports', models.BooleanField(default=False)),
                ('has_unapproved_posts', models.BooleanField(default=False)),
                ('has_hidden_posts', models.BooleanField(default=False)),
                ('has_events', models.BooleanField(default=False)),
                ('started_on', models.DateTimeField(db_index=True)),
                ('starter_name', models.CharField(max_length=255)),
                ('starter_slug', models.CharField(max_length=255)),
                ('last_post_on', models.DateTimeField(db_index=True)),
                ('last_poster_name', models.CharField(max_length=255, null=True, blank=True)),
                ('last_poster_slug', models.CharField(max_length=255, null=True, blank=True)),
                ('weight', models.PositiveIntegerField(default=0)),
                ('is_poll', models.BooleanField(default=False)),
                ('is_unapproved', models.BooleanField(default=False, db_index=True)),
                ('is_hidden', models.BooleanField(default=False)),
                ('is_closed', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        CreatePartialIndex(
            field='Thread.weight',
            index_name='misago_thread_is_global',
            condition='weight = 2',
        ),
        CreatePartialIndex(
            field='Thread.weight',
            index_name='misago_thread_is_local',
            condition='weight < 2',
        ),
        migrations.CreateModel(
            name='ThreadParticipant',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('thread', models.ForeignKey(to='misago_threads.Thread')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('is_owner', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='thread',
            name='participants',
            field=models.ManyToManyField(related_name='private_thread_set', through='misago_threads.ThreadParticipant', through_fields=('thread', 'user'), to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('author_name', models.CharField(max_length=255)),
                ('author_slug', models.CharField(max_length=255)),
                ('icon', models.CharField(max_length=255)),
                ('occured_on', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ('message', models.CharField(max_length=255)),
                ('checksum', models.CharField(max_length=64, default='-')),
                ('is_hidden', models.BooleanField(default=False)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('category', models.ForeignKey(to='misago_categories.Category')),
                ('thread', models.ForeignKey(to='misago_threads.Thread')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        CreatePartialIndex(
            field='Thread.has_reported_posts',
            index_name='misago_thread_has_reported_posts_partial',
            condition='has_reported_posts = TRUE',
        ),
        CreatePartialIndex(
            field='Thread.has_unapproved_posts',
            index_name='misago_thread_has_unapproved_posts_partial',
            condition='has_unapproved_posts = TRUE',
        ),
        CreatePartialIndex(
            field='Thread.is_hidden',
            index_name='misago_thread_is_hidden_partial',
            condition='is_hidden = FALSE',
        ),
        CreatePartialIndex(
            field='Thread.weight',
            index_name='misago_thread_is_pinned_globally_partial',
            condition='weight = 2',
        ),
        CreatePartialIndex(
            field='Thread.weight',
            index_name='misago_thread_is_pinned_locally_partial',
            condition='weight = 1',
        ),
        CreatePartialIndex(
            field='Thread.weight',
            index_name='misago_thread_is_unpinned_partial',
            condition='weight = 0',
        ),
        migrations.AddField(
            model_name='post',
            name='thread',
            field=models.ForeignKey(to='misago_threads.Thread'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='thread',
            name='first_post',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, blank=True, to='misago_threads.Post', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='thread',
            name='category',
            field=models.ForeignKey(to='misago_categories.Category'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='thread',
            name='last_post',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, blank=True, to='misago_threads.Post', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='thread',
            name='last_poster',
            field=models.ForeignKey(related_name='last_poster_set', on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='thread',
            name='starter',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AlterIndexTogether(
            name='thread',
            index_together=set([
                ('category', 'id'),
                ('category', 'last_post_on'),
                ('category', 'replies'),
            ]),
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('last_read_on', models.DateTimeField(default=django.utils.timezone.now)),
                ('send_email', models.BooleanField(default=False)),
                ('category', models.ForeignKey(to='misago_categories.Category')),
                ('thread', models.ForeignKey(to='misago_threads.Thread')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
