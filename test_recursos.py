import unittest
from unittest.mock import patch, MagicMock
from io import BytesIO
from app import app


class TestRecursos(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    # ----------- Test: Registrar recurso -----------
    @patch("app.execute_update")
    @patch("app.fetchone")
    @patch("app.os.path.exists")
    @patch("app.os.path.join", side_effect=lambda a, b: f"{a}/{b}")
    def test_registrar_recurso(self, mock_join, mock_exists, mock_fetchone, mock_update):
        mock_exists.return_value = False       # El archivo NO existe → no renombrar
        mock_update.return_value = True        # Inserciones correctas
        mock_fetchone.return_value = {"id": 10}  # Último ID insertado

        data = {
            "nombre": "Guía Matemáticas",
            "tipo_documento": "PDF",
            "docente": "Juan Pérez",
            "materia": "Matemáticas",
            "archivo": (BytesIO(b"fake file"), "guia.pdf")
        }

        response = self.client.post(
            "/recursos",
            data=data,
            content_type="multipart/form-data",
            follow_redirects=True
        )

        self.assertEqual(response.status_code, 200)
        mock_update.assert_called()
        self.assertIn(b"Recurso subido correctamente", response.data)

    # ----------- Test: Listar recursos (GET) -----------
    @patch("app.fetchall")
    def test_listar_recursos(self, mock_fetchall):
        mock_fetchall.return_value = []

        response = self.client.get("/recursos")

        self.assertEqual(response.status_code, 200)

    # ----------- Test: Eliminar recurso -----------
    @patch("app.execute_update")
    @patch("app.fetchone")
    @patch("app.os.remove")
    @patch("app.os.path.join", side_effect=lambda a, b: f"{a}/{b}")
    def test_eliminar_recurso(self, mock_join, mock_remove, mock_fetchone, mock_update):
        mock_fetchone.return_value = {"archivo": "guia.pdf"}
        mock_update.return_value = True

        response = self.client.get("/recursos/eliminar/5", follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        mock_update.assert_called()
        self.assertIn(b"Recurso eliminado correctamente", response.data)


if __name__ == "__main__":
    unittest.main()