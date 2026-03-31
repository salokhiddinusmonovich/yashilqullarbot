import os
import sys
import django

# Добавляем корневую папку в пути, чтобы Python видел dj_ac
sys.path.append("/usr/src/app") 
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dj_ac.settings")
django.setup()