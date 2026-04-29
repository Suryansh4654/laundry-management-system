from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_seed_services"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="username",
            field=models.CharField(max_length=150),
        ),
    ]
