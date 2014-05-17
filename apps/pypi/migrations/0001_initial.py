# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'PyPIUpdateLog'
        db.create_table('pypi_pypiupdatelog', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('changelog_pulled_ts', self.gf('django.db.models.fields.IntegerField')(default=1300139855)),
        ))
        db.send_create_signal('pypi', ['PyPIUpdateLog'])


    def backwards(self, orm):
        
        # Deleting model 'PyPIUpdateLog'
        db.delete_table('pypi_pypiupdatelog')


    models = {
        'pypi.pypiupdatelog': {
            'Meta': {'object_name': 'PyPIUpdateLog'},
            'changelog_pulled_ts': ('django.db.models.fields.IntegerField', [], {'default': '1300139855'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['pypi']
