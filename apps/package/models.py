# TODO - cleanup regex to do proper string subs
# TODO - add is_other field to repo
# TODO - add repo.user_url

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.translation import ugettext_lazy as _
from github2.client import Github
from package.fields import CreationDateTimeField, ModificationDateTimeField
from package.handlers import github
from package.utils import uniquer
from distutils.version import LooseVersion as versioner
from urllib import urlopen
import logging
import os
import re
import sys




class NoPyPiVersionFound(Exception):
    pass

class BaseModel(models.Model):
    """ Base abstract base class to give creation and modified times """
    created     = CreationDateTimeField(_('created'))
    modified    = ModificationDateTimeField(_('modified'))
    
    class Meta:
        abstract = True

class Category(BaseModel):
    
    title = models.CharField(_("Title"), max_length="50")
    slug  = models.SlugField(_("slug"))
    description = models.TextField(_("description"), blank=True)
    title_plural = models.CharField(_("Title Plural"), max_length="50", blank=True) 
    show_pypi = models.BooleanField(_("Show pypi stats & version"), default=True)
    
    class Meta:
        ordering = ['title']
        verbose_name_plural = 'Categories'
    
    def __unicode__(self):
        return self.title
        
REPO_CHOICES = (
    ("package.handlers.unsupported", "Unsupported"),
    ("package.handlers.bitbucket", "Bitbucket"),
    ("package.handlers.github", "Github")
)

class Repo(BaseModel):
    
    is_supported = models.BooleanField(_("Supported?"), help_text="Does Django Packages support this repo site?", default=False)
    title        = models.CharField(_("Title"), max_length="50")
    description  = models.TextField(_("description"), blank=True)
    url          = models.URLField(_("base URL of repo"))
    is_other     = models.BooleanField(_("Is Other?"), default=False, help_text="Only one can be set this way")
    user_regex   = models.CharField(_("User Regex"), help_text="Regex to calculate user's name or id",max_length="100", blank=True)
    repo_regex   = models.CharField(_("Repo Regex"), help_text="Regex to get repo's name", max_length="100", blank=True)
    slug_regex   = models.CharField(_("Slug Regex"), help_text="Regex to get repo's slug", max_length="100", blank=True)    
    handler      = models.CharField(_("Handler"), 
        help_text="Warning: Don't change this unless you know what you are doing!", 
        choices=REPO_CHOICES,
        max_length="200",
        default="package.handlers.unsupported")
    
    class Meta:
        ordering = ['-is_supported', 'title']
    
    def __unicode__(self):
        if not self.is_supported:
            return '%s (unsupported)' % self.title
        
        return self.title

downloads_re = re.compile(r'<td style="text-align: right;">[0-9]{1,}</td>')
doap_re      = re.compile(r"/pypi\?\:action=doap\&amp;name=[a-zA-Z0-9\.\-\_]+\&amp;version=[a-zA-Z0-9\.\-\_]+")
version_re   = re.compile(r'<revision>[a-zA-Z0-9\.\-\_]+</revision>')

repo_url_help_text = "Enter your project repo hosting URL here.<br />Example: https://bitbucket.com/ubernostrum/django-registration"
pypi_url_help_text = "<strong>Leave this blank if this package does not have a PyPI release.</strong><br />What PyPI uses to index your package. <br />Example: django-registration"
category_help_text = """
<ul>
 <li><strong>Apps</strong> is anything that is installed by placing in settings.INSTALLED_APPS.</li>
 <li><strong>Frameworks</strong> are large efforts that combine many python modules or apps to build things like Pinax.</li>
 <li><strong>Other</strong> are not installed by settings.INSTALLED_APPS, are not frameworks or sites but still help Django in some way.</li>
 <li><strong>Projects</strong> are individual projects such as Django Packages, DjangoProject.com, and others.</li>
</ul>
"""

class Package(BaseModel):
    
    title           = models.CharField(_("Title"), max_length="100")
    slug            = models.SlugField(_("Slug"), help_text="Slugs will be lowercased", unique=True)
    category        = models.ForeignKey(Category, verbose_name="Installation", help_text=category_help_text)
    repo            = models.ForeignKey(Repo, null=True)
    repo_description= models.TextField(_("Repo Description"), blank=True)
    repo_url        = models.URLField(_("repo URL"), help_text=repo_url_help_text, blank=True, unique=True)
    repo_watchers   = models.IntegerField(_("repo watchers"), default=0)
    repo_forks      = models.IntegerField(_("repo forks"), default=0)
    repo_commits    = models.IntegerField(_("repo commits"), default=0)
    pypi_url        = models.URLField(_("PyPI slug"), help_text=pypi_url_help_text, blank=True, default='', unique=True)
    pypi_homepage_url = models.URLField(_("PyPI package homepage"), blank=True, verify_exists=False)
    #pypi_version    = models.CharField(_("Current Pypi version"), max_length="20", blank=True)
    pypi_downloads  = models.IntegerField(_("Pypi downloads"), default=0)
    related_packages    = models.ManyToManyField("self", blank=True)
    participants    = models.TextField(_("Participants"),
                        help_text="List of collaborats/participants on the project", blank=True)
    usage           = models.ManyToManyField(User, blank=True)
    created_by = models.ForeignKey(User, blank=True, null=True, related_name="creator")    
    last_modified_by = models.ForeignKey(User, blank=True, null=True, related_name="modifier")
    pypi_updated_ts = models.DateTimeField(null=True)
    
    @property
    def pypi_version(self):
        string_ver_list = self.version_set.values_list('number', flat=True)
        if string_ver_list:
            vers_list = [versioner(v) for v in string_ver_list]
            latest = sorted(vers_list)[-1]
            return str(latest)
        return ''

    @property     
    def pypi_name(self):
        """ return the pypi name of a package"""
        
        if not self.pypi_url.strip():
            return ""
            
        name = self.pypi_url.replace("http://pypi.python.org/pypi/","")
        if "/" in name:
            return name[:name.index("/")]
        return name

    def active_examples(self):
        return self.packageexample_set.filter(active=True)
    
    def grids(self):
        
        return (x.grid for x in self.gridpackage_set.all())
    
    def repo_name(self):
        return self.repo_url.replace(self.repo.url + '/','')
    
    def participant_list(self):
        
        return self.participants.split(',')
    
    def commits_over_52(self):
        from package.templatetags.package_tags import commits_over_52
        return commits_over_52(self)
    
    def fetch_all_updates(self):
        """Fetches available updates from PyPI and the project repo."""
        from pypi.handler import update_or_create_package
        update_or_create_package(self.pypi_url)
        self.fetch_repo_data()
        self.save()

    def fetch_repo_data(self):
        # Get the repo watchers number
        base_handler = __import__(self.repo.handler)
        handler = sys.modules[self.repo.handler]
        self = handler.pull(self)

    class Meta:
        ordering = ['title']
    
    def __unicode__(self):
        
        return self.title
        
    @models.permalink
    def get_absolute_url(self):
        return ("package", [self.slug])
        

class PackageExample(BaseModel):
    
    package = models.ForeignKey(Package)
    title = models.CharField(_("Title"), max_length="100")
    url = models.URLField(_("URL"))
    active = models.BooleanField(_("Active"), default=True, help_text="Moderators have to approve links before they are provided")
    
    class Meta:
        ordering = ['title']
    
    def __unicode__(self):
        return self.title

class Commit(BaseModel):
    
    package      = models.ForeignKey(Package)
    commit_date  = models.DateTimeField(_("Commit Date"))
    
    class Meta:
        ordering = ['-commit_date']
        
    def __unicode__(self):
        return "Commit for '%s' on %s" % (self.package.title, unicode(self.commit_date))    
        
class Version(BaseModel):
    
    package = models.ForeignKey(Package, blank=True, null=True)
    number = models.CharField(_("Version"), max_length="100", default="", blank="")
    downloads = models.IntegerField(_("downloads"), default=0)
    license = models.CharField(_("license"), max_length="100")
    hidden = models.BooleanField(_("hidden"), default=False)    

    # Since PyPI packages can have wacky version "numbers" like 1.1b2 or
    # 2011-3 or really anything, we'll want to capture their official ordering
    # with higher order numbers being more recent releases
    order = models.IntegerField(_("Order"))
    
    class Meta:
        get_latest_by = 'order'
        ordering = ['-order']
    
    def __unicode__(self):
        return "%s: %s" % (self.package.title, self.number)
    
