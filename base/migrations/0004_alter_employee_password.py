# Generated by Django 5.1.3 on 2024-12-29 16:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0003_remove_attendancelog_description_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employee',
            name='password',
            field=models.CharField(max_length=100),
        ),
    ]