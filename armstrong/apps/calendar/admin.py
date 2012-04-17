import datetime

from django import forms
from django.conf import settings
from django.contrib import admin
from django.utils.translation import ugettext as _
from django.contrib.admin import widgets

from armstrong.core.arm_content.admin import fieldsets as fs
from armstrong.apps.related_content.admin import RelatedContentInline
from armstrong.core.arm_sections.admin import SectionTreeAdminMixin
from armstrong import hatband

from reversion.admin import VersionAdmin

from .models import Event
from .widgets import UpdateDeleteSeries
from .utils import copy_model_instance, copy_many_to_many, copy_inlines

REPEAT_CHOICES = (
  ('none', _('None')),
  ('15', _('15 Minutues')),
  ('30', _('Half Hour')),
  ('hour', _('Hourly')),
  ('day', _('Daily')),
  ('week', _('Weekly')),
  ('month_num', _('Monthly (Example: 3rd of every month)')),
  ('month', _('Monthly same day (Example: First Monday of the month)')),
  ('year', _('Yearly'))
)

UPDATE_CHOICES = (
  ('me', _('Update just this event')),
  ('all', _('Update all events in series'))
)

class EventForm (forms.ModelForm):
  repeat = forms.ChoiceField(choices=REPEAT_CHOICES, required=False)
  repeat_until = forms.DateTimeField(required=False, widget=widgets.AdminSplitDateTime())
  update = forms.ChoiceField(choices=UPDATE_CHOICES, initial="me", required=False, widget=UpdateDeleteSeries)
  
  #TODO: add repeat validation
  
  class Meta:
    model = Event
    
class EventAdmin (SectionTreeAdminMixin, VersionAdmin, hatband.ModelAdmin):
  list_display = ('title', 'start_dt', 'end_dt', 'series', 'pub_date', 'pub_status')
  list_filter = ('sections', 'pub_status')
  search_fields = ('title', 'slug', 'summary', 'body')
  date_hierarchy = 'start_dt'
  
  form = EventForm
  fieldsets = (
      ('Update', {
          'fields': ('update',),
      }),
      
      (None, {
          'fields': ('title', 'slug', 'summary', 'body'),
      }),
      
      (_('Event Time'), {
          'fields': (('start_dt', 'end_dt'), 'series'),
      }),

      fs.TAXONOMY,
      fs.PUBLICATION,
      fs.AUTHORS,
  )
  
  fieldsets_add = (
      (None, {
          'fields': ('title', 'slug', 'summary', 'body'),
      }),
      
      (_('Event Time'), {
          'fields': (
            ('start_dt', 'end_dt'),
            ('repeat', 'repeat_until'),
            'series'
          ),
      }),

      fs.TAXONOMY,
      fs.PUBLICATION,
      fs.AUTHORS,
  )
  
  raw_id_fields = ('series',)
  inlines = [RelatedContentInline]
  
  def save_related (self, request, form, formsets, change):
    super(EventAdmin, self).save_related(request, form, formsets, change)
    
    if change:
      self.update_series(request, form.instance, form)
      
    else:
      self.save_new_series(request, form.instance, form)
      
  #TODO: tags not always saving
  def update_series (self, request, obj, form):
    if form.cleaned_data.has_key('update') and form.cleaned_data['update'] == 'all':
      for updobj in Event.objects.filter(series=obj.series).exclude(id=obj.id):
        copy_many_to_many(obj, updobj)
        copy_inlines(obj, updobj)
        
  def save_new_series (self, request, obj, form):
    if form.cleaned_data.has_key('repeat') and form.cleaned_data['repeat'] != 'none':
      delta = None
      end_delta = None
      
      if form['repeat'].data == '15':
        delta = datetime.timedelta(minutes=15)
        
      elif form['repeat'].data == '30':
        delta = datetime.timedelta(minutes=30)
        
      elif form['repeat'].data == 'hour':
        delta = datetime.timedelta(hours=1)
        
      elif form.cleaned_data['repeat'] == 'day':
        delta = datetime.timedelta(days=1)
        
      elif form.cleaned_data['repeat'] == 'week':
        delta = datetime.timedelta(days=7)
        
      elif form.cleaned_data['repeat'] == 'month':
        delta = datetime.timedelta(days=28)
        
      elif form.cleaned_data['repeat'] == 'month_num':
        delta = 'month'
        
      elif form.cleaned_data['repeat'] == 'year':
        delta = 'year'
        
      if obj.end_dt:
        end_delta = obj.end_dt - obj.start_dt
        
      if delta:
        obj.series = obj
        obj.save()
        
        start = obj.start_dt
        while 1:
          if delta == 'year':
            start = start.replace(year=start.year + 1)
            
          elif delta == 'month':
            if start.month == 12:
              start = start.replace(year=start.year + 1, month=1)
              
            else:
              start = start.replace(month=start.month + 1)
            
          else:
            start += delta
            
          if start <= form.cleaned_data['repeat_until']:
            newobj = copy_model_instance(obj)
            newobj.start_dt = start
            if obj.end_dt:
              newobj.end_dt = newobj.start_dt + end_delta
              
            newobj.save()
            copy_many_to_many(obj, newobj)
            copy_inlines(obj, newobj)
            
          else:
            break
          
  def get_fieldsets (self, request, obj=None):
    if obj is None:
      return self.fieldsets_add
      
    return self.fieldsets
    
admin.site.register(Event, EventAdmin)
