import datetime

from django.test import TestCase

from .models import Event
from .utils import copy_model_instance, copy_many_to_many, update_attrs, copy_inlines
  
class EventTestCase (TestCase):
  def setUp (self):
    self.bday = Event(
      title = 'My Birthday',
      start_dt = datetime.datetime(1978, 11, 15),
      all_day = True,
      body = '<strong>Most awesome day of the year.</strong>',
      pub_date = datetime.datetime.now()
    )
    
    self.bday.save()
    
    self.death = Event(
      title = 'My Birthday',
      start_dt = datetime.datetime(2178, 11, 15, 4, 30, 33),
      end_dt = datetime.datetime(2178, 11, 15, 6, 0, 12),
      body = 'So sad but every dog has its day.',
      pub_date = datetime.datetime.now()
    )
    
    self.death.save()
    
  def tearDown (self):
    self.bday.delete()
    self.death.delete()
    
  def test_copy (self):
    self.bday.series = self.bday
    self.bday.save()
    
    for i in range(1, 3):
      newobj = copy_model_instance(self.bday)
      newobj.start_dt = self.bday.start_dt.replace(year=self.bday.start_dt.year + i)
      newobj.save()
      copy_many_to_many(self.bday, newobj)
      copy_inlines(self.bday, newobj)
      
    qs = Event.objects.filter(series=self.bday)
    self.assertEqual(qs.count(), 3)
    
    self.bday.title = 'updated title'
    self.bday.save()
    
    for updobj in qs.exclude(id=self.bday.id):
      update_attrs(self.bday, updobj, ('start_dt', 'end_dt'))
      copy_many_to_many(self.bday, updobj)
      copy_inlines(self.bday, updobj)
      
    for obj in qs:
      self.assertEqual(obj.title, 'updated title')
      