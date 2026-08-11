import io
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.test import TestCase
from django.utils import timezone
from PIL import Image

from courses.models import Course, Lesson, Module

from .api import (
    delete_certificate_signature,
    download_certificate,
    get_or_issue_certificate,
    my_certificates,
    update_certificate_config,
    upload_certificate_signature,
    upsert_progress,
    verify_certificate,
)
from .certificate_pdf import course_hours, render_certificate_pdf
from .models import Certificate, CertificateConfig, CourseEnrollment, LessonProgress
from .schemas import CertificateConfigIn, CertificateVerifyOut, ProgressIn, _mask_cpf

CPF_OK = '52998224725'


def _png(size=(600, 200)) -> bytes:
    buf = io.BytesIO()
    Image.new('RGBA', size, (0, 0, 0, 0)).save(buf, 'PNG')
    return buf.getvalue()


def _jpg() -> bytes:
    buf = io.BytesIO()
    Image.new('RGB', (100, 100), (255, 255, 255)).save(buf, 'JPEG')
    return buf.getvalue()


def _req(user):
    return SimpleNamespace(auth=user)


class CertificateFlowTests(TestCase):
    def setUp(self):
        U = get_user_model()
        self.aluno = U.objects.create_user(email='aluno@x.com', password='x', name='Aluno Teste', cpf=CPF_OK)
        self.outro = U.objects.create_user(email='outro@x.com', password='x', name='Outro')

        self.course = Course.objects.create(name='Curso X', category='sales', is_active=True, certificate_enabled=True)
        self.module = Module.objects.create(course=self.course, name='M1', order=0, is_published=True)
        self.l1 = Lesson.objects.create(module=self.module, name='A1', order=0, is_published=True, duration_seconds=3600)
        self.l2 = Lesson.objects.create(module=self.module, name='A2', order=1, is_published=True, duration_seconds=1800)
        CourseEnrollment.objects.create(user=self.aluno, course=self.course, is_active=True)

    def _complete(self, user, *lessons):
        for lesson in lessons:
            LessonProgress.objects.create(user=user, lesson=lesson, completed_at=timezone.now())

    # --- opt-in ---
    def test_curso_sem_certificado_habilitado_404(self):
        self.course.certificate_enabled = False
        self.course.save()
        self._complete(self.aluno, self.l1, self.l2)
        res = get_or_issue_certificate(_req(self.aluno), self.course.id)
        self.assertEqual(res.status_code, 404)
        self.assertEqual(Certificate.objects.count(), 0)

    # --- gate de 100% ---
    def test_incompleto_403_e_nao_emite(self):
        self._complete(self.aluno, self.l1)  # 1 de 2
        res = get_or_issue_certificate(_req(self.aluno), self.course.id)
        self.assertEqual(res.status_code, 403)
        self.assertEqual(Certificate.objects.count(), 0)

    # --- gate de CPF ---
    def test_cem_por_cento_sem_cpf_409(self):
        CourseEnrollment.objects.create(user=self.outro, course=self.course, is_active=True)
        self._complete(self.outro, self.l1, self.l2)
        res = get_or_issue_certificate(_req(self.outro), self.course.id)
        self.assertEqual(res.status_code, 409)
        self.assertEqual(Certificate.objects.count(), 0)

    # --- emissão idempotente ---
    def test_cem_por_cento_com_cpf_emite_uma_vez(self):
        self._complete(self.aluno, self.l1, self.l2)
        res = get_or_issue_certificate(_req(self.aluno), self.course.id)
        self.assertEqual(res.status_code, 200)
        cert = Certificate.objects.get()
        self.assertEqual(cert.student_cpf, CPF_OK)
        self.assertEqual(cert.student_name, 'Aluno Teste')
        self.assertEqual(cert.hours, 2)  # 3600+1800 = 1.5h → arredonda 2

        get_or_issue_certificate(_req(self.aluno), self.course.id)  # 2º hit
        self.assertEqual(Certificate.objects.count(), 1)

    # --- acesso negado a curso não matriculado ---
    def test_sem_acesso_403(self):
        res = get_or_issue_certificate(_req(self.outro), self.course.id)
        self.assertEqual(res.status_code, 403)

    # --- aula em módulo despublicado não trava o 100% ---
    def test_aula_em_modulo_despublicado_nao_bloqueia(self):
        rascunho = Module.objects.create(course=self.course, name='Rascunho', order=1, is_published=False)
        Lesson.objects.create(module=rascunho, name='Oculta', order=0, is_published=True)  # o aluno não vê
        self._complete(self.aluno, self.l1, self.l2)  # conclui só o visível
        res = get_or_issue_certificate(_req(self.aluno), self.course.id)
        self.assertEqual(res.status_code, 200)  # a aula oculta não conta

    # --- regressão: progresso de OUTRO usuário não infla o total (bug do JOIN sem distinct) ---
    def test_completion_nao_infla_com_progresso_de_outros(self):
        from enrollments.api import _completion

        CourseEnrollment.objects.create(user=self.outro, course=self.course, is_active=True)
        LessonProgress.objects.create(user=self.outro, lesson=self.l1)  # started, não concluído
        LessonProgress.objects.create(user=self.outro, lesson=self.l2, completed_at=timezone.now())
        self._complete(self.aluno, self.l1, self.l2)
        self.assertEqual(_completion(self.aluno, self.course.id), (2, 2))  # sem distinct daria (4, ...)

    # --- nome obrigatório (impresso no certificado) ---
    def test_sem_nome_409(self):
        U = get_user_model()
        sem_nome = U.objects.create_user(email='sn@x.com', password='x', name='', cpf=CPF_OK)
        CourseEnrollment.objects.create(user=sem_nome, course=self.course, is_active=True)
        self._complete(sem_nome, self.l1, self.l2)
        res = get_or_issue_certificate(_req(sem_nome), self.course.id)
        self.assertEqual(res.status_code, 409)
        self.assertEqual(Certificate.objects.count(), 0)

    # --- download só do dono, PDF válido ---
    def test_download_do_dono_pdf(self):
        self._complete(self.aluno, self.l1, self.l2)
        get_or_issue_certificate(_req(self.aluno), self.course.id)
        cert = Certificate.objects.get()

        resp = download_certificate(_req(self.aluno), cert.code)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertTrue(resp.content.startswith(b'%PDF'))

        with self.assertRaises(Http404):  # outro usuário não baixa
            download_certificate(_req(self.outro), cert.code)

    # --- gancho automático no progresso ---
    def test_hook_emite_ao_fechar_100(self):
        upsert_progress(_req(self.aluno), self.l1.id, ProgressIn(completed=True))
        self.assertEqual(Certificate.objects.count(), 0)  # ainda 1 de 2
        upsert_progress(_req(self.aluno), self.l2.id, ProgressIn(completed=True))
        self.assertEqual(Certificate.objects.count(), 1)  # fechou 100%

    # --- lista do aluno ---
    def test_my_certificates_lista(self):
        self._complete(self.aluno, self.l1, self.l2)
        get_or_issue_certificate(_req(self.aluno), self.course.id)
        self.assertEqual([c.course_id for c in my_certificates(_req(self.aluno))], [self.course.id])

    # --- carga horária: manual sobrepõe soma ---
    def test_course_hours_manual_e_derivada(self):
        self.assertEqual(course_hours(self.course), 2)  # soma 5400s vídeo → 1.5h → 2
        self.course.certificate_hours = 40
        self.assertEqual(course_hours(self.course), 40)  # manual manda

    def test_course_hours_soma_video_e_exercicio(self):
        # exercício conta o time_limit_seconds; vídeo conta duration_seconds
        Lesson.objects.create(
            module=self.module, name='Prova', order=2, is_published=True,
            kind='quiz', duration_seconds=0, time_limit_seconds=1800,
        )
        self.assertEqual(course_hours(self.course), 2)  # 3600+1800(vídeo)+1800(prova)=7200 → 2h

    def test_render_pdf_sem_carga(self):
        cert = Certificate(course=self.course, student_name='Sem Horas', student_cpf=CPF_OK, hours=None, issued_at=timezone.now())
        cert.code = 'ABC123XYZ456'
        self.assertTrue(render_certificate_pdf(cert).startswith(b'%PDF'))


class CpfValidationTests(TestCase):
    def test_valida_e_normaliza(self):
        from accounts.utils import normalize_cpf, validate_cpf

        self.assertTrue(validate_cpf('529.982.247-25'))
        self.assertTrue(validate_cpf(CPF_OK))
        self.assertFalse(validate_cpf('111.111.111-11'))  # repetido
        self.assertFalse(validate_cpf('529.982.247-24'))  # dígito errado
        self.assertFalse(validate_cpf('123'))
        self.assertEqual(normalize_cpf('529.982.247-25'), CPF_OK)


class VerifyCertificateTests(TestCase):
    def setUp(self):
        U = get_user_model()
        u = U.objects.create_user(email='a@x.com', password='x', name='Aluno', cpf=CPF_OK)
        course = Course.objects.create(name='Curso X', category='sales')
        self.cert = Certificate.objects.create(
            user=u, course=course, student_name='Aluno', student_cpf=CPF_OK, hours=10, code='ABCD12345678'
        )

    def test_mask_cpf(self):
        self.assertEqual(_mask_cpf(CPF_OK), '529.***.***-25')

    def test_verify_out_mascara_cpf(self):
        out = CertificateVerifyOut.from_orm(self.cert)
        self.assertEqual(out.student_cpf, '529.***.***-25')
        self.assertNotIn('982', out.student_cpf)  # miolo do CPF não vaza

    def test_valido_e_case_insensitive(self):
        req = SimpleNamespace(auth=None)
        self.assertEqual(verify_certificate(req, 'ABCD12345678').status_code, 200)
        self.assertEqual(verify_certificate(req, 'abcd12345678').status_code, 200)  # upper

    def test_codigo_desconhecido_404(self):
        self.assertEqual(verify_certificate(SimpleNamespace(auth=None), 'ZZZZ00000000').status_code, 404)


class CertificateConfigTests(TestCase):
    def setUp(self):
        U = get_user_model()
        self.staff = U.objects.create_user(email='s@x.com', password='x', is_staff=True)

    def _req(self):
        return SimpleNamespace(auth=self.staff)

    def test_atualiza_nome_e_cargo(self):
        res = update_certificate_config(self._req(), CertificateConfigIn(signer_name='  Fulano  ', signer_role='Diretor'))
        self.assertEqual(res.status_code, 200)
        cfg = CertificateConfig.load()
        self.assertEqual((cfg.signer_name, cfg.signer_role), ('Fulano', 'Diretor'))

    def test_upload_png_valido(self):
        f = SimpleUploadedFile('sig.png', _png(), content_type='image/png')
        res = upload_certificate_signature(self._req(), f)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(bool(CertificateConfig.load().signature))

    def test_rejeita_jpg_por_content_type(self):
        f = SimpleUploadedFile('sig.jpg', _jpg(), content_type='image/jpeg')
        res = upload_certificate_signature(self._req(), f)
        self.assertEqual(res.status_code, 400)
        self.assertFalse(bool(CertificateConfig.load().signature))

    def test_rejeita_png_falso(self):
        # content_type diz PNG mas o conteúdo é JPEG → Pillow pega
        f = SimpleUploadedFile('fake.png', _jpg(), content_type='image/png')
        res = upload_certificate_signature(self._req(), f)
        self.assertEqual(res.status_code, 400)

    def test_rejeita_arquivo_grande(self):
        big = _png((3200, 200)) + b'\x00' * (1024 * 1024 + 10)  # > 1MB
        f = SimpleUploadedFile('big.png', big, content_type='image/png')
        res = upload_certificate_signature(self._req(), f)
        self.assertEqual(res.status_code, 400)

    def test_delete_assinatura(self):
        cfg = CertificateConfig.load()
        cfg.signature = _png()
        cfg.save()
        res = delete_certificate_signature(self._req())
        self.assertEqual(res.status_code, 200)
        self.assertFalse(bool(CertificateConfig.load().signature))

    def test_render_com_assinatura_e_assinante(self):
        cfg = CertificateConfig.load()
        cfg.signer_name = 'Fulano de Tal'
        cfg.signer_role = 'Diretor'
        cfg.signature = _png()
        cfg.save()
        cert = Certificate(
            course=Course.objects.create(name='C', category='sales'),
            student_name='Aluno', student_cpf=CPF_OK, hours=10, issued_at=timezone.now(),
        )
        cert.code = 'CODE12345678'
        self.assertTrue(render_certificate_pdf(cert).startswith(b'%PDF'))
