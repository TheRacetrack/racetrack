# Generated by Django 3.2.13 on 2022-12-07 10:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registry', '0025_auto_20220831_0912'),
    ]

    operations = [
        migrations.AddField(
            model_name='deployment',
            name='infrastructure_target',
            field=models.CharField(max_length=256, null=True),
        ),
        migrations.AddField(
            model_name='fatman',
            name='infrastructure_target',
            field=models.CharField(max_length=256, null=True),
        ),
        migrations.AddField(
            model_name='trashfatman',
            name='infrastructure_target',
            field=models.CharField(max_length=256, null=True),
        ),
    ]