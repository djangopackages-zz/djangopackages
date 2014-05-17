from datetime import datetime

from django.core.management.base import NoArgsCommand

from pypi.handler import update_outdated_packages


class Command(NoArgsCommand):
    help = 'Updates all outdated packages on PyPI.'
    
    def handle(self, *args, **options):
        print 'Beginning package update from PyPI at %s UTC.' % \
            datetime.utcnow().strftime('%d %b %Y %H:%M:%S')

        update_outdated_packages()

        print 'Completed package update from PyPI at %s UTC.' % \
            datetime.utcnow().strftime('%d %b %Y %H:%M:%S')
