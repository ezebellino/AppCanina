from io import BytesIO
from types import SimpleNamespace

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from django.utils import timezone
from PIL import Image

from .credential_pdf import build_credential_pdf
from .image_utils import safe_image_upload


class ImageDependencyCompatibilityTests(SimpleTestCase):
    def test_uploaded_jpeg_and_png_remain_readable_and_embedded_in_credentials(self):
        for format_name, suffix in (("JPEG", "jpg"), ("PNG", "png")):
            with self.subTest(format=format_name):
                source = BytesIO()
                photo = Image.new("RGB", (240, 180), "green")
                exif = Image.Exif()
                exif[0x010E] = "Private original metadata"
                photo.save(source, format=format_name, exif=exif)
                cleaned = safe_image_upload(SimpleUploadedFile(f"animal.{suffix}", source.getvalue()))
                with Image.open(BytesIO(cleaned.read())) as result:
                    result.load()
                    self.assertEqual(result.size, (240, 180))
                    self.assertFalse(result.getexif())
                cleaned.seek(0)
                patient = SimpleNamespace(photo=cleaned, name="Animal de prueba", breed="", birth_date=None,
                                          microchip="", get_species_display=lambda: "Perro")
                pdf = build_credential_pdf(patient, SimpleNamespace(full_name="Responsable de prueba"), "TEST-ONLY", timezone.now())
                self.assertTrue(pdf.startswith(b"%PDF-"))
                self.assertIn(b"/Subtype /Image", pdf)
