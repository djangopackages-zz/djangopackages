from django.core.management.base import NoArgsCommand

from pypi.handler import update_outdated_packages


class Command(NoArgsCommand):
    help = 'WARNING! Pulls the entirety of the PyPI data. Please don\'t do '\
        'this unless you for sure know what you\'re doing.'
    
    def handle(self, *args, **options):
        print 'Beginning full package import from PyPI at %s UTC.' % \
            datetime.utcnow().strftime('%d %b %Y %H:%M:%S')

        update_outdated_packages(allow_initial_full_download=True)

        print 'Completed full package import from PyPI at %s UTC.' % \
            datetime.utcnow().strftime('%d %b %Y %H:%M:%S')
