import datetime

from django.apps import apps
from django.core.management.base import BaseCommand
from django.conf import settings

from share.models import ShareUser
from share.tasks import HarvesterTask
from share.provider import ProviderAppConfig


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='Run all harvester')
        parser.add_argument('harvester', nargs='*', type=str, help='The name of the harvester to run')
        parser.add_argument('--async', action='store_true', help='Whether or not to use Celery')
        parser.add_argument('--days-back', type=int, help='The number of days to go back')

    def handle(self, *args, **options):
        user = ShareUser.objects.get(username=settings.APPLICATION_USERNAME)

        task_kwargs = {}
        if options['days_back']:
            task_kwargs['end'] = (datetime.datetime.utcnow() + datetime.timedelta(days=-(options['days_back'] - 1))).isoformat() + 'Z'
            task_kwargs['start'] = (datetime.datetime.utcnow() + datetime.timedelta(days=-options['days_back'])).isoformat() + 'Z'

        if not options['harvester'] and options['all']:
            options['harvester'] = [x.label for x in apps.get_app_configs() if isinstance(x, ProviderAppConfig)]

        for harvester in options['harvester']:
            apps.get_app_config(harvester)  # Die if the AppConfig can not be loaded

            task_args = (harvester, user.id,)
            if options['async']:
                HarvesterTask().apply_async(task_args, task_kwargs)
                self.stdout.write('Started job for harvester {}'.format(harvester))
            else:
                self.stdout.write('Running harvester for {}'.format(harvester))
                HarvesterTask().apply(task_args, task_kwargs, throw=True)
