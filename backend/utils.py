import errno
import logging
from os import path, makedirs, remove, rmdir, listdir
import sched, time, datetime
from django.conf import settings
from .models import Schedule

logger = logging.getLogger(__name__)

def create_dir(dirname):
  if not path.exists(dirname):
    try:
      makedirs(dirname)
    except OSError as e:
      if e.errno != errno.EEXIST:
        raise

def run_backup(schedule):
  from subprocess import run

  logger.info('Running scheduled backup for {}'.format(schedule))

  create_dir(schedule.backup_path())
  run(schedule.backup_command(), shell=True)
  remove_expired_backups(schedule)

def run_backups(schedules):
  from multiprocessing import Process

  processes = []

  for schedule in schedules:
    process = Process(target=run_backup, args=(schedule,))
    processes.append(process)
    process.start()

  for process in processes:
    process.join()



def run_eligible_backups():
  import calendar
  now = datetime.datetime.now()
  day_string = calendar.day_name[now.weekday()]
  logger.info('Look for and run eligible backups at {}'.format(now))
  # Filter out weekly schedules that aren't due today
  schedules = filter(lambda s : True if s.schedule == 'daily' else s.day == day_string, Schedule.objects.all())
  print(list(schedules))



def remove_deleted_backups():
  logger.info('Remove folders for non-existent schedules')

  ids = list(map(lambda s: s.id, Schedule.objects.all()))

  for backup_dir in listdir(settings.FILES_ROOT):
    if int(backup_dir) not in ids:
      rmdir(path.join(settings.FILES_ROOT, backup_dir))


def remove_expired_backups(schedule):
  backups = schedule.list_backups()

  if len(backups) is 0:
    return

  backups.sort(key=lambda b : path.getmtime(path.join(schedule.backup_path(), b)))

  num_to_delete = len(backups) - schedule.keep

  if num_to_delete > 0:
    for b in backups[:num_to_delete]:
      try:
        remove(path.join(schedule.backup_path(), b))
      except OSError:
        pass


def scheduled_tasks():
  remove_deleted_backups()
  run_elibile_backups()

