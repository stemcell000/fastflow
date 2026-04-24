from django.db import models


class Sample(models.Model):
    SAMPLE_TYPE_CHOICES = [
        ('cell_line', 'Cell Line'),
        ('primary_culture', 'Primary Culture'),
        ('tissue', 'Tissue'),
        ('organoid', 'Organoid'),
        ('other', 'Other'),
    ]

    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=255)
    project_name = models.CharField(max_length=255)
    sample_type = models.CharField(max_length=50, choices=SAMPLE_TYPE_CHOICES, blank=True)
    plasmid_number = models.IntegerField(null=True, blank=True)
    production_number = models.IntegerField(null=True, blank=True)
    biological_model = models.CharField(max_length=255, blank=True)
    organ = models.CharField(max_length=255, blank=True)
    serotype = models.CharField(max_length=255, blank=True)
    condition = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=1000, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.project_name})"


class Protocol(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    primer_pair = models.CharField(max_length=255, blank=True)
    commentary = models.CharField(max_length=1000, blank=True)
    protocol_description_file = models.FileField(
        upload_to='protocols/descriptions/', blank=True, null=True
    )
    sample = models.ForeignKey(
        Sample, on_delete=models.CASCADE, related_name='protocols'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Protocol #{self.pk} — {self.primer_pair}"


class NgsSample(models.Model):
    index = models.CharField(max_length=255, blank=True)
    final_concentration = models.FloatField(null=True, blank=True)
    bioanalyzer_file = models.FileField(
        upload_to='ngs_samples/bioanalyzer/', blank=True, null=True
    )
    protocol = models.ForeignKey(
        Protocol, on_delete=models.CASCADE, related_name='ngs_samples'
    )

    def __str__(self):
        return f"NGS Sample #{self.pk} (index: {self.index})"


class SequencingBatch(models.Model):
    ngs_sample = models.ForeignKey(
        NgsSample, on_delete=models.CASCADE, related_name='sequencing_batches'
    )

    def __str__(self):
        return f"Sequencing Batch #{self.pk}"


class SequencingBatchFile(models.Model):
    file = models.FileField(upload_to='sequencing_batches/files/', blank=True, null=True)
    table_de_calcul = models.FileField(
        upload_to='sequencing_batches/tables/', blank=True, null=True
    )
    sequencing_batch = models.ForeignKey(
        SequencingBatch, on_delete=models.CASCADE, related_name='batch_files'
    )

    def __str__(self):
        return f"Batch File #{self.pk} (Batch #{self.sequencing_batch_id})"


class SequencingProduct(models.Model):
    date = models.CharField(max_length=50, blank=True)
    summary_file = models.FileField(
        upload_to='sequencing_products/summaries/', blank=True, null=True
    )
    sequencing_machine = models.CharField(max_length=255, blank=True)
    flowcell = models.CharField(max_length=255, blank=True)
    read_length = models.IntegerField(null=True, blank=True)
    read_depth = models.IntegerField(null=True, blank=True)
    phix_proportion = models.FloatField(null=True, blank=True)
    custom_recipe = models.BooleanField(default=False)
    custom_recipe_start = models.IntegerField(null=True, blank=True)
    custom_recipe_end = models.IntegerField(null=True, blank=True)
    sequencing_batch = models.ForeignKey(
        SequencingBatch, on_delete=models.CASCADE, related_name='sequencing_products'
    )

    def __str__(self):
        return f"Sequencing Product #{self.pk} — {self.sequencing_machine}"


class Fastq(models.Model):
    sequencing_product = models.ForeignKey(
        SequencingProduct, on_delete=models.CASCADE, related_name='fastqs'
    )

    def __str__(self):
        return f"FASTQ #{self.pk}"


class FastqFile(models.Model):
    file = models.FileField(upload_to='fastq/files/', blank=True, null=True)
    fastq = models.ForeignKey(
        Fastq, on_delete=models.CASCADE, related_name='fastq_files'
    )

    def __str__(self):
        return f"FASTQ File #{self.pk}"


class Pipeline(models.Model):
    fastq = models.ForeignKey(
        Fastq, on_delete=models.CASCADE, related_name='pipelines'
    )

    def __str__(self):
        return f"Pipeline #{self.pk}"


class Script(models.Model):
    script_file = models.FileField(upload_to='pipelines/scripts/', blank=True, null=True)
    pipeline = models.ForeignKey(
        Pipeline, on_delete=models.CASCADE, related_name='scripts'
    )

    def __str__(self):
        return f"Script #{self.pk} (Pipeline #{self.pipeline_id})"


class Setting(models.Model):
    settings_json = models.FileField(
        upload_to='pipelines/settings/', blank=True, null=True
    )
    script = models.ForeignKey(
        Script, on_delete=models.CASCADE, related_name='settings'
    )

    def __str__(self):
        return f"Settings #{self.pk} (Script #{self.script_id})"


class Count(models.Model):
    counts_file = models.FileField(upload_to='pipelines/counts/', blank=True, null=True)
    pipeline = models.ForeignKey(
        Pipeline, on_delete=models.CASCADE, related_name='counts'
    )

    def __str__(self):
        return f"Count #{self.pk} (Pipeline #{self.pipeline_id})"


class Analysis(models.Model):
    trimming_table_file = models.FileField(
        upload_to='pipelines/analysis/trimming/', blank=True, null=True
    )
    logo_plot_file = models.FileField(
        upload_to='pipelines/analysis/logo/', blank=True, null=True
    )
    pipeline = models.ForeignKey(
        Pipeline, on_delete=models.CASCADE, related_name='analyses'
    )

    def __str__(self):
        return f"Analysis #{self.pk} (Pipeline #{self.pipeline_id})"
