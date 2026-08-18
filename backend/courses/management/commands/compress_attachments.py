"""Recomprime PDFs de anexos já no storage (gs /printer, ~8x sem perda perceptível).

Dry-run por padrão (só relatório); `--apply` sobrescreve. Segurança: copia o original pra
`_backup/<key>` antes de trocar, valida (encolheu + mesmo nº de páginas via compress_pdf) e
NUNCA deleta o anexo. Anexo que não encolhe é pulado. Idempotente.

    uv run python manage.py compress_attachments            # relatório
    uv run python manage.py compress_attachments --apply     # aplica
"""

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from courses.helpers import compress_pdf
from courses.models import LessonAttachment


MIN_SAVE = 200_000  # só troca se economizar ao menos isso; evita churn de PDF minúsculo por alguns KB


class Command(BaseCommand):
    help = 'Recomprime PDFs de anexos no storage (gs /printer).'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Sobrescreve (default: só relatório).')
        parser.add_argument('--setting', default='/printer', help='PDFSETTINGS do ghostscript.')

    def handle(self, *args, **opts):
        apply = opts['apply']
        setting = opts['setting']
        qs = LessonAttachment.objects.filter(file_url__iendswith='.pdf').order_by('id')

        tot_before = tot_after = saved = skipped = 0
        for att in qs:
            name = att.file_url.name
            try:
                with att.file_url.open('rb') as f:
                    orig = f.read()
            except Exception as e:  # noqa: BLE001
                self.stderr.write(f'  #{att.id} {name}: erro ao ler ({e}), pulado')
                skipped += 1
                continue

            blob = compress_pdf(orig, setting=setting)
            b, a = len(orig), len(blob)
            tot_before += b
            if b - a < MIN_SAVE:  # não encolheu o suficiente (compress_pdf devolve original em falha)
                tot_after += b
                skipped += 1
                self.stdout.write(f'  #{att.id} {att.title[:40]:40} {b/1e6:6.1f}MB  já ok, pulado')
                continue

            tot_after += a
            saved += 1
            pct = 100 * (1 - a / b)
            flag = 'APLICA' if apply else 'dry   '
            self.stdout.write(f'  #{att.id} {att.title[:40]:40} {b/1e6:6.1f}MB -> {a/1e6:5.1f}MB  -{pct:2.0f}%  [{flag}]')

            if apply:
                default_storage.save(f'_backup/{name}', ContentFile(orig))  # insurance: original preservado
                default_storage.delete(name)  # file_overwrite=False: libera a key p/ regravar mesma
                default_storage.save(name, ContentFile(blob))
                att.size_bytes = a
                att.save(update_fields=['size_bytes'])

        self.stdout.write('')
        self.stdout.write(
            f'{qs.count()} PDFs | {saved} {"comprimidos" if apply else "a comprimir"} | {skipped} pulados | '
            f'{tot_before/1e6:.0f}MB -> {tot_after/1e6:.0f}MB'
        )
        if not apply and saved:
            self.stdout.write('Rode de novo com --apply pra aplicar.')
